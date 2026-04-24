from __future__ import annotations

import json
import os
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_BRIDGE_FILE = "_runtime_bridge.json"
_PIPELINE_CONTEXT_FILE = "_full_pipeline_context.json"
_JOB_STATE_SNAPSHOT_FILE = "_job_state_snapshot.json"
_STAGE_ASSETS_SNAPSHOT_FILE = "_stage_assets_snapshot.json"


@dataclass(frozen=True)
class RuntimeBridgeState:
    paper_pdf: Path
    paper_key: str
    job_id: str
    job_dir: Path
    job_json_path: Path
    own_payload: dict[str, Any]


def _ingestion_stage_dir(run_dir: Path) -> Path:
    return run_dir / "stages" / "ingestion"


def _job_state_snapshot_path(run_dir: Path) -> Path:
    return _ingestion_stage_dir(run_dir) / _JOB_STATE_SNAPSHOT_FILE


def _stage_assets_snapshot_path(run_dir: Path) -> Path:
    return _ingestion_stage_dir(run_dir) / _STAGE_ASSETS_SNAPSHOT_FILE


def _init_pipeline_context(*, run_dir: Path, runner: str, stage: str = "") -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {"runner": runner, "stage": stage, "version": 1}
    path = run_dir / _PIPELINE_CONTEXT_FILE
    write_json_file(path, payload)
    return path


def init_full_pipeline_context(*, run_dir: Path) -> Path:
    """Mark a run directory as managed by src.pipeline_full."""
    return _init_pipeline_context(run_dir=run_dir, runner="full_pipeline")


def init_standalone_stage_context(*, run_dir: Path, stage: str = "") -> Path:
    """Mark a run directory as managed by a standalone stage command."""
    return _init_pipeline_context(run_dir=run_dir, runner="standalone_stage", stage=stage)


def ensure_full_pipeline_context(*, run_dir: Path, allow_standalone: bool = False, stage: str = "") -> None:
    """Validate stage context; optionally bootstrap standalone mode."""
    marker = run_dir / _PIPELINE_CONTEXT_FILE
    payload = read_json_file(marker)
    if not payload:
        if allow_standalone:
            init_standalone_stage_context(run_dir=run_dir, stage=stage)
            return
        raise RuntimeError(
            "Stage modules are internal-only and must be run via full_pipeline. "
            f"Missing pipeline context marker: {marker}"
        )
    runner = str(payload.get("runner") or "").strip()
    if runner == "full_pipeline":
        return
    if allow_standalone and runner == "standalone_stage":
        return
    if allow_standalone:
        raise RuntimeError(
            "Invalid pipeline context marker. Expected full_pipeline or standalone_stage, "
            f"got runner={runner!r}. Marker: {marker}"
        )
    if runner != "full_pipeline":
        raise RuntimeError(
            "Invalid pipeline context marker. "
            "Please run through scripts/execute_review_pipeline.py."
        )


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


def _copy_file_if_exists(src: Path | None, dst: Path) -> bool:
    if src is None or (not src.exists()) or (not src.is_file()):
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _copy_dir_if_exists(src: Path | None, dst: Path) -> bool:
    if src is None or (not src.exists()) or (not src.is_dir()):
        return False
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    return True


def _snapshot_file(
    *,
    source: Path | None,
    destination: Path,
) -> str:
    if source is None or (not source.exists()) or (not source.is_file()):
        return ""
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return str(destination.resolve())


def load_job_state_snapshot(run_dir: Path) -> dict[str, Any]:
    return read_json_file(_job_state_snapshot_path(run_dir))


def load_stage_assets_snapshot(run_dir: Path) -> dict[str, Any]:
    return read_json_file(_stage_assets_snapshot_path(run_dir))


def _materialize_stage_inputs_snapshot(
    *,
    repo_root: Path,
    run_dir: Path,
    state: RuntimeBridgeState,
    own_payload: dict[str, Any],
) -> None:
    """
    Persist run-local snapshots so downstream stages can run independently
    of data/jobs/<job_id>/job.json and sibling runtime directories.
    """
    stage_dir = _ingestion_stage_dir(run_dir)
    snapshot_root = stage_dir / "snapshot_artifacts"
    snapshot_root.mkdir(parents=True, exist_ok=True)

    job_state = read_json_file(state.job_json_path)
    if not job_state:
        artifacts = own_payload.get("artifacts") if isinstance(own_payload.get("artifacts"), dict) else {}
        job_state = {
            "status": own_payload.get("status"),
            "message": own_payload.get("message"),
            "error": own_payload.get("error"),
            "artifacts": artifacts,
            "usage": own_payload.get("usage") or {},
            "metadata": own_payload.get("metadata") or {},
            "annotation_count": int(own_payload.get("annotation_count") or 0),
            "final_report_ready": bool(own_payload.get("final_report_ready")),
            "pdf_ready": bool(own_payload.get("pdf_ready")),
        }
    write_json_file(_job_state_snapshot_path(run_dir), job_state)

    artifacts = job_state.get("artifacts") if isinstance(job_state.get("artifacts"), dict) else {}
    annotations_src = resolve_artifact_path(repo_root, artifacts.get("annotations_path"))
    final_md_src = resolve_artifact_path(repo_root, artifacts.get("final_markdown_path"))
    final_pdf_src = resolve_artifact_path(repo_root, artifacts.get("report_pdf_path"))
    semantic_src = (state.job_dir / "semantic_scholar_candidates.json").resolve()

    snapshot_payload = {
        "job_json_path": str(state.job_json_path),
        "job_dir": str(state.job_dir),
        "job_state_snapshot_path": str(_job_state_snapshot_path(run_dir)),
        "annotations_snapshot_path": _snapshot_file(
            source=annotations_src,
            destination=snapshot_root / "annotations.json",
        ),
        "final_markdown_snapshot_path": _snapshot_file(
            source=final_md_src,
            destination=snapshot_root / "final_review.md",
        ),
        "report_pdf_snapshot_path": _snapshot_file(
            source=final_pdf_src,
            destination=snapshot_root / "final_review.pdf",
        ),
        "semantic_scholar_candidates_snapshot_path": _snapshot_file(
            source=semantic_src if semantic_src.exists() else None,
            destination=snapshot_root / "semantic_scholar_candidates.json",
        ),
    }
    write_json_file(_stage_assets_snapshot_path(run_dir), snapshot_payload)


def _materialize_execution_paper_extract(
    *,
    repo_root: Path,
    paper_key: str,
    job_dir: Path,
    mineru_md: Path | None,
    mineru_content: Path | None,
) -> dict[str, str]:
    """
    Bridge the runtime MinerU output into the execution stage's shared baseline folder.

    This lets execution reuse the first PDF parse instead of requiring a second,
    local MinerU CLI invocation under src/baseline/<paper_key>/paper_extracted/.
    """
    baseline_dir = repo_root / "src" / "baseline" / str(paper_key or "paper").strip()
    extracted_dir = baseline_dir / "paper_extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    md_dst = extracted_dir / "paper.mineru.md"
    content_dst = extracted_dir / "paper.mineru.content_list.json"
    assets_src = job_dir / "mineru_assets"
    assets_dst = extracted_dir / "mineru_assets"

    copied_md = _copy_file_if_exists(mineru_md, md_dst)
    copied_content = _copy_file_if_exists(mineru_content, content_dst)
    copied_assets = _copy_dir_if_exists(assets_src, assets_dst)

    tables_dir = extracted_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    return {
        "paper_extracted_dir": str(extracted_dir.resolve()),
        "paper_extracted_md_path": str(md_dst.resolve()) if copied_md else "",
        "paper_extracted_content_list_path": str(content_dst.resolve()) if copied_content else "",
        "paper_extracted_assets_dir": str(assets_dst.resolve()) if copied_assets else "",
        "paper_extracted_tables_dir": str(tables_dir.resolve()),
    }


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


def _run_review_runtime(*, repo_root: Path, paper_pdf: Path, title: str) -> dict[str, Any]:
    py_exec = _pick_python_executable(repo_root)
    script = repo_root / "scripts" / "execute_review_runtime_job.py"

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


def load_bridge_state(run_dir: Path) -> RuntimeBridgeState | None:
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
    if not (paper_pdf.exists() and job_id):
        return None

    return RuntimeBridgeState(
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
) -> RuntimeBridgeState:
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

    return RuntimeBridgeState(
        paper_pdf=paper_pdf.resolve(),
        paper_key=paper_key,
        job_id=job_id,
        job_dir=job_dir,
        job_json_path=job_json_path,
        own_payload=own_payload,
    )


def require_bridge_state(
    *,
    run_dir: Path,
) -> RuntimeBridgeState:
    existing = load_bridge_state(run_dir)
    if existing is not None:
        return existing
    raise FileNotFoundError(
        f"Bridge state missing at {_bridge_path(run_dir)}. "
        "Ensure ingestion stage has been completed by full_pipeline."
    )


def bootstrap_bridge_state(
    *,
    repo_root: Path,
    run_dir: Path,
    paper_pdf: Path | None = None,
    paper_key: str,
    reuse_job_id: str = "",
) -> RuntimeBridgeState:
    run_dir.mkdir(parents=True, exist_ok=True)
    existing = load_bridge_state(run_dir)
    if existing is not None:
        return existing

    job_id = str(reuse_job_id or "").strip()
    if job_id:
        job_dir = (repo_root / "data" / "jobs" / job_id).resolve()
        job_json_path = job_dir / "job.json"
        if not job_json_path.exists():
            raise FileNotFoundError(f"reused job.json not found: {job_json_path}")
        job_state = read_json_file(job_json_path)
        if not job_state:
            raise RuntimeError(f"reused job state is empty/invalid: {job_json_path}")

        artifacts = job_state.get("artifacts") if isinstance(job_state.get("artifacts"), dict) else {}
        source_pdf = resolve_artifact_path(repo_root, artifacts.get("source_pdf_path"))
        fallback_pdf = paper_pdf.resolve() if paper_pdf is not None else None
        resolved_pdf = source_pdf if (source_pdf is not None and source_pdf.exists()) else fallback_pdf
        if resolved_pdf is None or (not resolved_pdf.exists()):
            raise FileNotFoundError(
                "cannot resolve source_pdf_path from reused job state; "
                "please provide --paper-pdf when using --reuse-job-id."
            )
        key = str(paper_key or "").strip() or resolved_pdf.parent.name or "paper"

        own_payload = {
            "job_id": job_id,
            "status": job_state.get("status"),
            "message": job_state.get("message"),
            "error": job_state.get("error"),
            "artifacts": artifacts,
            "usage": job_state.get("usage") or {},
            "metadata": job_state.get("metadata") or {},
            "annotation_count": int(job_state.get("annotation_count") or 0),
            "final_report_ready": bool(job_state.get("final_report_ready")),
            "pdf_ready": bool(job_state.get("pdf_ready")),
            "job_json_path": str(job_json_path),
            "job_dir": str(job_dir),
            "latest_output_md": str(
                resolve_artifact_path(repo_root, artifacts.get("latest_output_md_path"))
                or (job_dir / "latest_extraction.md").resolve()
            ),
            "latest_output_pdf": str(
                resolve_artifact_path(repo_root, artifacts.get("latest_output_pdf_path"))
                or (job_dir / "latest_extraction.pdf").resolve()
            ),
        }
        return save_bridge_state(
            run_dir=run_dir,
            paper_pdf=resolved_pdf,
            paper_key=key,
            own_payload=own_payload,
        )

    if paper_pdf is None:
        raise FileNotFoundError(
            f"Bridge state missing at {_bridge_path(run_dir)}. "
            "Provide paper_pdf to bootstrap a standalone stage or run ingestion first."
        )
    resolved_pdf = paper_pdf.resolve()
    if not resolved_pdf.exists():
        raise FileNotFoundError(f"paper pdf not found: {resolved_pdf}")

    key = str(paper_key or "").strip() or resolved_pdf.parent.name or "paper"
    own_payload = _run_review_runtime(repo_root=repo_root, paper_pdf=resolved_pdf, title=key)
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
    reuse_job_id: str = "",
) -> dict[str, Any]:
    ensure_full_pipeline_context(run_dir=run_dir, allow_standalone=True, stage="ingestion")
    state = bootstrap_bridge_state(
        repo_root=repo_root,
        run_dir=run_dir,
        paper_pdf=paper_pdf,
        paper_key=paper_key,
        reuse_job_id=reuse_job_id,
    )
    own_payload = state.own_payload if isinstance(state.own_payload, dict) else {}
    _materialize_stage_inputs_snapshot(
        repo_root=repo_root,
        run_dir=run_dir,
        state=state,
        own_payload=own_payload,
    )
    artifacts = own_payload.get("artifacts") if isinstance(own_payload.get("artifacts"), dict) else {}
    metadata = own_payload.get("metadata") if isinstance(own_payload.get("metadata"), dict) else {}
    usage = own_payload.get("usage") if isinstance(own_payload.get("usage"), dict) else {}
    annotation_count = int(own_payload.get("annotation_count") or 0)
    mineru_md_raw = str(artifacts.get("mineru_markdown_path") or "").strip()
    mineru_content_raw = str(artifacts.get("mineru_content_list_path") or "").strip()

    mineru_md = resolve_artifact_path(repo_root, mineru_md_raw)
    mineru_content = resolve_artifact_path(repo_root, mineru_content_raw)
    shared_extract = _materialize_execution_paper_extract(
        repo_root=repo_root,
        paper_key=state.paper_key,
        job_dir=state.job_dir,
        mineru_md=mineru_md,
        mineru_content=mineru_content,
    )

    ingestion_out = run_dir / "stages" / "ingestion" / "paper.json"
    write_json_file(
        ingestion_out,
        {
            "source_pdf": str(state.paper_pdf),
            "mineru_markdown_path": mineru_md_raw if (mineru_md is not None and mineru_md.exists()) else "",
            "mineru_content_list_path": mineru_content_raw
            if (mineru_content is not None and mineru_content.exists())
            else "",
            "markdown_provider": metadata.get("markdown_provider"),
            "mineru_batch_id": metadata.get("mineru_batch_id"),
            "parse_warning": metadata.get("parse_warning"),
            "job_id": state.job_id,
            "job_json_path": str(state.job_json_path),
            "shared_execution_extract": shared_extract,
            "annotation_count": annotation_count,
            "annotations_path": str(artifacts.get("annotations_path") or ""),
            "semantic_scholar_candidates_path": str((state.job_dir / "semantic_scholar_candidates.json").resolve()),
            "final_markdown_path": str(artifacts.get("final_markdown_path") or ""),
            "report_pdf_path": str(artifacts.get("report_pdf_path") or ""),
            "latest_output_md": str(own_payload.get("latest_output_md") or ""),
            "latest_output_pdf": str(own_payload.get("latest_output_pdf") or ""),
            "runtime_status": own_payload.get("status"),
            "runtime_message": own_payload.get("message"),
            "runtime_error": own_payload.get("error"),
            "usage": usage,
            "paper_search_runtime_state": metadata.get("paper_search_runtime_state")
            if isinstance(metadata.get("paper_search_runtime_state"), dict)
            else {},
        },
    )

    return {
        "status": "ok" if (mineru_md is not None and mineru_md.exists()) else "failed",
        "output": str(ingestion_out),
        "bridge": str(_bridge_path(run_dir)),
        "job_id": state.job_id,
        "job_dir": str(state.job_dir),
    }


if __name__ == "__main__":
    raise SystemExit("Internal stage module. Use scripts/execute_review_pipeline.py.")
