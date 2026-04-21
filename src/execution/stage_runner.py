from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ingestion.runtime_bridge import (
    ensure_full_pipeline_context,
    load_bridge_state,
    read_json_file,
    write_json_file,
)


def _load_execution_artifacts(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    run_info = state.get("run") if isinstance(state.get("run"), dict) else {}
    run_dir = Path(str(run_info.get("dir") or "")).resolve() if run_info.get("dir") else Path()
    summary = read_json_file(run_dir / "summary.json") if run_dir else {}
    alignment = read_json_file(run_dir / "artifacts" / "alignment" / "alignment.json") if run_dir else {}
    return summary, alignment, str(run_dir) if run_dir else ""


async def _run_orchestrator_async(
    *,
    run_root: Path,
    paper_pdf: Path,
    paper_key: str,
    max_attempts: int,
    no_pdf_extract: bool,
) -> dict[str, Any]:
    from execution.graph import CodeEvalOrchestrator

    orchestrator = CodeEvalOrchestrator(
        run_root=str(run_root),
        max_attempts=max_attempts,
    )
    return await orchestrator.run(
        paper_root="",
        paper_pdf=str(paper_pdf),
        paper_key=paper_key,
        tasks_path="",
        baseline_path="",
        local_source_path="",
        no_pdf_extract=no_pdf_extract,
    )


def run_execution_stage(
    *,
    run_dir: Path,
    paper_pdf: Path | None = None,
    paper_key: str | None = None,
    max_attempts: int = 5,
    no_pdf_extract: bool = False,
) -> dict[str, Any]:
    ensure_full_pipeline_context(run_dir=run_dir)
    bridge = load_bridge_state(run_dir)
    resolved_pdf = paper_pdf.resolve() if paper_pdf else (bridge.paper_pdf if bridge else None)
    resolved_key = (paper_key or "").strip() or (bridge.paper_key if bridge else "")

    if resolved_pdf is None or not resolved_pdf.exists():
        raise FileNotFoundError(
            "paper_pdf is required for execution stage when bridge state is missing or invalid."
        )
    if not resolved_key:
        resolved_key = resolved_pdf.parent.name or "paper"

    stage_root = run_dir / "stages" / "execution"
    stage_root.mkdir(parents=True, exist_ok=True)
    stage_run_root = stage_root / "run"

    run_result = asyncio.run(
        _run_orchestrator_async(
            run_root=stage_run_root,
            paper_pdf=resolved_pdf,
            paper_key=resolved_key,
            max_attempts=max_attempts,
            no_pdf_extract=no_pdf_extract,
        )
    )

    state = run_result.get("state") if isinstance(run_result.get("state"), dict) else {}
    summary, alignment, actual_run_dir = _load_execution_artifacts(state)
    exit_status = str(run_result.get("exit_status") or "failed")

    stage_status = "failed"
    if exit_status == "success":
        stage_status = "ok"
    elif exit_status == "inconclusive":
        stage_status = "inconclusive"

    payload = {
        "paper_key": resolved_key,
        "paper_pdf": str(resolved_pdf),
        "status": stage_status,
        "success": bool(run_result.get("success")),
        "exit_status": exit_status,
        "run_dir": actual_run_dir,
        "summary": summary,
        "alignment": alignment,
    }

    output_path = stage_root / "execution.json"
    write_json_file(output_path, payload)

    return {
        "status": stage_status,
        "output": str(output_path),
        "run_dir": actual_run_dir,
    }


if __name__ == "__main__":
    raise SystemExit("Internal stage module. Use scripts/execute_review_pipeline.py.")
