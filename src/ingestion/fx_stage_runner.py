from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_BRIDGE_FILE = "_fx_bridge.json"


@dataclass(frozen=True)
class FXBridgeState:
    paper_pdf: Path
    paper_key: str
    job_id: str
    job_dir: Path
    job_json_path: Path
    own_payload: dict[str, Any]


def read_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_artifact_path(repo_root: Path, raw: Any) -> Path | None:
    token = str(raw or "").strip()
    if not token:
        return None
    p = Path(token)
    if not p.is_absolute():
        p = (repo_root / p).resolve()
    return p


def _pick_python_executable(repo_root: Path) -> Path:
    candidates = [
        repo_root / ".venv" / "bin" / "python",
        repo_root / "factreview-own" / ".venv" / "bin" / "python",
    ]
    for cand in candidates:
        if cand.exists():
            try:
                chk = subprocess.run(
                    [str(cand), "-c", "import agents"],
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                )
                if chk.returncode == 0:
                    return cand
            except Exception:
                continue
    for cand in candidates:
        if cand.exists():
            return cand
    return Path("python3")


def _run_fx_runtime(*, repo_root: Path, paper_pdf: Path, title: str) -> dict[str, Any]:
    py_exec = _pick_python_executable(repo_root)
    script = repo_root / "scripts" / "run_fx_runtime_job.py"

    env = os.environ.copy()
    # Keep parity with legacy integration behavior: execution is handled as external stage.
    env.setdefault("ENABLE_CODE_EVALUATION", "false")

    proc = subprocess.run(
        [str(py_exec), str(script), "--paper-pdf", str(paper_pdf), "--title", title],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "factreview-own runtime pipeline failed\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )

    text = (proc.stdout or "").strip()
    payload: dict[str, Any] | None = None
    if text:
        try:
            parsed = json.loads(text)
            payload = parsed if isinstance(parsed, dict) else None
        except Exception:
            start = text.rfind("{")
            if start >= 0:
                try:
                    parsed = json.loads(text[start:])
                    payload = parsed if isinstance(parsed, dict) else None
                except Exception:
                    payload = None
    if payload is None:
        raise RuntimeError(f"cannot parse factreview-own runtime output: {text}")
    return payload


def _bridge_path(run_dir: Path) -> Path:
    return run_dir / "stages" / "ingestion" / _BRIDGE_FILE


def load_bridge_state(run_dir: Path) -> FXBridgeState | None:
    payload = read_json_file(_bridge_path(run_dir))
    if not payload:
        return None

    paper_pdf = Path(str(payload.get("paper_pdf") or "")).resolve()
    paper_key = str(payload.get("paper_key") or "").strip() or "paper"
    job_id = str(payload.get("job_id") or "").strip()
    job_dir = Path(str(payload.get("job_dir") or "")).resolve()
    job_json_path = Path(str(payload.get("job_json_path") or "")).resolve()
    own_payload = payload.get("own_payload") if isinstance(payload.get("own_payload"), dict) else {}
    if not job_json_path.exists() and job_dir.exists():
        job_json_path = job_dir / "job.json"
    if not (paper_pdf.exists() and job_id and job_json_path.exists()):
        return None

    return FXBridgeState(
        paper_pdf=paper_pdf,
        paper_key=paper_key,
        job_id=job_id,
        job_dir=job_dir,
        job_json_path=job_json_path,
        own_payload=own_payload,
    )


def save_bridge_state(
    *,
    run_dir: Path,
    paper_pdf: Path,
    paper_key: str,
    own_payload: dict[str, Any],
) -> FXBridgeState:
    job_id = str(own_payload.get("job_id") or "").strip()
    job_dir = Path(str(own_payload.get("job_dir") or "")).resolve()
    job_json_path = Path(str(own_payload.get("job_json_path") or "")).resolve()
    if not job_json_path.exists() and job_dir.exists():
        job_json_path = job_dir / "job.json"

    bridge_payload = {
        "paper_pdf": str(paper_pdf.resolve()),
        "paper_key": paper_key,
        "job_id": job_id,
        "job_dir": str(job_dir),
        "job_json_path": str(job_json_path),
        "own_payload": own_payload,
    }
    write_json_file(_bridge_path(run_dir), bridge_payload)

    return FXBridgeState(
        paper_pdf=paper_pdf.resolve(),
        paper_key=paper_key,
        job_id=job_id,
        job_dir=job_dir,
        job_json_path=job_json_path,
        own_payload=own_payload,
    )


def ensure_bridge_state(
    *,
    repo_root: Path,
    run_dir: Path,
    paper_pdf: Path | None,
    paper_key: str | None,
) -> FXBridgeState:
    existing = load_bridge_state(run_dir)
    if existing is not None:
        return existing

    if paper_pdf is None:
        raise FileNotFoundError(
            f"Bridge state missing at {_bridge_path(run_dir)} and no paper_pdf was provided to bootstrap ingestion."
        )

    resolved_pdf = paper_pdf.resolve()
    if not resolved_pdf.exists():
        raise FileNotFoundError(f"paper pdf not found: {resolved_pdf}")

    key = str(paper_key or "").strip() or resolved_pdf.parent.name or "paper"
    own_payload = _run_fx_runtime(repo_root=repo_root, paper_pdf=resolved_pdf, title=key)
    return save_bridge_state(
        run_dir=run_dir,
        paper_pdf=resolved_pdf,
        paper_key=key,
        own_payload=own_payload,
    )


def run_ingestion_stage(
    *,
    repo_root: Path,
    run_dir: Path,
    paper_pdf: Path,
    paper_key: str,
) -> dict[str, Any]:
    state = ensure_bridge_state(
        repo_root=repo_root,
        run_dir=run_dir,
        paper_pdf=paper_pdf,
        paper_key=paper_key,
    )
    job_state = read_json_file(state.job_json_path)
    artifacts = job_state.get("artifacts") if isinstance(job_state.get("artifacts"), dict) else {}
    metadata = job_state.get("metadata") if isinstance(job_state.get("metadata"), dict) else {}

    mineru_md = resolve_artifact_path(repo_root, artifacts.get("mineru_markdown_path"))
    mineru_content = resolve_artifact_path(repo_root, artifacts.get("mineru_content_list_path"))

    ingestion_out = run_dir / "stages" / "ingestion" / "paper.json"
    write_json_file(
        ingestion_out,
        {
            "source_pdf": str(state.paper_pdf),
            "mineru_markdown_path": str(mineru_md) if (mineru_md is not None and mineru_md.exists()) else "",
            "mineru_content_list_path": str(mineru_content)
            if (mineru_content is not None and mineru_content.exists())
            else "",
            "markdown_provider": metadata.get("markdown_provider"),
            "mineru_batch_id": metadata.get("mineru_batch_id"),
            "parse_warning": metadata.get("parse_warning"),
            "job_id": state.job_id,
            "job_json_path": str(state.job_json_path),
        },
    )

    return {
        "status": "ok" if (mineru_md is not None and mineru_md.exists()) else "failed",
        "output": str(ingestion_out),
        "bridge": str(_bridge_path(run_dir)),
        "job_id": state.job_id,
        "job_dir": str(state.job_dir),
    }


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("run_ingestion_fx_stage")
    p.add_argument("paper_pdf", type=str)
    p.add_argument("--paper-key", type=str, default="")
    p.add_argument("--run-dir", type=str, required=True)
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    paper_pdf = Path(args.paper_pdf).resolve()
    paper_key = (args.paper_key or "").strip() or paper_pdf.parent.name or "paper"
    run_dir = Path(args.run_dir).resolve()
    payload = run_ingestion_stage(
        repo_root=repo_root,
        run_dir=run_dir,
        paper_pdf=paper_pdf,
        paper_key=paper_key,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
