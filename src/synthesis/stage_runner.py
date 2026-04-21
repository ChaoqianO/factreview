from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ingestion.runtime_bridge import (
    ensure_full_pipeline_context,
    require_bridge_state,
    read_json_file,
    resolve_artifact_path,
    write_json_file,
)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _copy_if_exists(src: Path | None, dst: Path) -> bool:
    if src is None:
        return False
    if not src.exists() or not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def run_synthesis_stage(
    *,
    repo_root: Path,
    run_dir: Path,
) -> dict[str, Any]:
    ensure_full_pipeline_context(run_dir=run_dir)
    bridge = require_bridge_state(run_dir=run_dir)

    job_state = read_json_file(bridge.job_json_path)
    artifacts = job_state.get("artifacts") if isinstance(job_state.get("artifacts"), dict) else {}
    metadata = job_state.get("metadata") if isinstance(job_state.get("metadata"), dict) else {}
    final_md_raw = str(artifacts.get("final_markdown_path") or "").strip()
    final_pdf_raw = str(artifacts.get("report_pdf_path") or "").strip()

    final_md = resolve_artifact_path(repo_root, final_md_raw)
    final_pdf = resolve_artifact_path(repo_root, final_pdf_raw)

    synthesis_dir = run_dir / "stages" / "synthesis"
    synthesis_json = synthesis_dir / "final_review.json"
    synthesis_md = synthesis_dir / "final_review.md"

    md_ok = _copy_if_exists(final_md, synthesis_md)
    pdf_ok = _copy_if_exists(final_pdf, synthesis_dir / "final_review.pdf")

    execution_payload = read_json_file(run_dir / "stages" / "execution" / "execution.json")

    write_json_file(
        synthesis_json,
        {
            "paper_key": bridge.paper_key,
            "run_id": run_dir.name,
            "job_id": bridge.job_id,
            "status": bridge.own_payload.get("status"),
            "message": bridge.own_payload.get("message"),
            "error": bridge.own_payload.get("error"),
            "usage": bridge.own_payload.get("usage") or {},
            "metadata": metadata,
            "execution": execution_payload,
            "final_markdown": _read_text(synthesis_md) if md_ok else "",
            "final_markdown_path": final_md_raw if (final_md is not None and final_md.exists()) else "",
            "final_pdf_path": final_pdf_raw if (final_pdf is not None and final_pdf.exists()) else "",
        },
    )

    result: dict[str, Any] = {
        "status": "ok" if (final_md is not None and final_md.exists()) else "failed",
        "output_json": str(synthesis_json),
        "output_md": str(synthesis_md),
    }
    if pdf_ok:
        result["output_pdf"] = str(synthesis_dir / "final_review.pdf")

    latest_md = Path(str(bridge.own_payload.get("latest_output_md") or "")).resolve()
    latest_pdf = Path(str(bridge.own_payload.get("latest_output_pdf") or "")).resolve()
    if latest_md.exists():
        result["latest_extraction_md"] = str(latest_md)
    if latest_pdf.exists():
        result["latest_extraction_pdf"] = str(latest_pdf)

    return result


if __name__ == "__main__":
    raise SystemExit("Internal stage module. Use scripts/execute_review_pipeline.py.")
