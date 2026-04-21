from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from execution.stage_runner import run_execution_stage
from fact_extraction.stage_runner import run_fact_extraction_stage
from ingestion.runtime_bridge import init_full_pipeline_context, run_ingestion_stage
from positioning.stage_runner import run_positioning_stage
from synthesis.stage_runner import run_synthesis_stage


def _now_run_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_full_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    paper_pdf = Path(args.paper_pdf).resolve()
    if not paper_pdf.exists():
        raise FileNotFoundError(f"paper pdf not found: {paper_pdf}")

    paper_key = (args.paper_key or "").strip() or paper_pdf.parent.name or "paper"
    run_id = _now_run_id()
    run_dir = Path(args.run_root).resolve() / paper_key / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    init_full_pipeline_context(run_dir=run_dir)

    ingestion_result = run_ingestion_stage(
        repo_root=repo_root,
        run_dir=run_dir,
        paper_pdf=paper_pdf,
        paper_key=paper_key,
        reuse_job_id=str(args.reuse_job_id or "").strip(),
    )
    fact_result = run_fact_extraction_stage(
        repo_root=repo_root,
        run_dir=run_dir,
    )
    positioning_result = run_positioning_stage(
        repo_root=repo_root,
        run_dir=run_dir,
    )
    if bool(args.skip_execution):
        execution_payload = {
            "paper_key": paper_key,
            "paper_pdf": str(paper_pdf),
            "status": "skipped",
            "success": False,
            "exit_status": "skipped",
            "run_dir": "",
            "summary": {},
            "alignment": {},
        }
        execution_out = run_dir / "stages" / "execution" / "execution.json"
        _write_json(execution_out, execution_payload)
        execution_result = {
            "status": "skipped",
            "output": str(execution_out),
            "run_dir": "",
        }
    else:
        execution_result = run_execution_stage(
            run_dir=run_dir,
            paper_pdf=paper_pdf,
            paper_key=paper_key,
            max_attempts=int(args.max_attempts),
            no_pdf_extract=bool(args.no_pdf_extract),
        )
    synthesis_result = run_synthesis_stage(
        repo_root=repo_root,
        run_dir=run_dir,
    )

    statuses = {
        "ingestion": str(ingestion_result.get("status") or "failed"),
        "fact_extraction": str(fact_result.get("status") or "failed"),
        "positioning": str(positioning_result.get("status") or "failed"),
        "execution": str(execution_result.get("status") or "failed"),
        "synthesis": str(synthesis_result.get("status") or "failed"),
    }

    outputs: dict[str, str] = {}
    if ingestion_result.get("output"):
        outputs["ingestion"] = str(ingestion_result.get("output"))
    if fact_result.get("output"):
        outputs["fact_extraction"] = str(fact_result.get("output"))
    if positioning_result.get("output"):
        outputs["positioning"] = str(positioning_result.get("output"))
    if execution_result.get("output"):
        outputs["execution"] = str(execution_result.get("output"))
    if synthesis_result.get("output_json"):
        outputs["synthesis_json"] = str(synthesis_result.get("output_json"))
    if synthesis_result.get("output_md"):
        outputs["synthesis_md"] = str(synthesis_result.get("output_md"))
    if synthesis_result.get("output_pdf"):
        outputs["synthesis_pdf"] = str(synthesis_result.get("output_pdf"))
    if synthesis_result.get("latest_extraction_md"):
        outputs["latest_extraction_md"] = str(synthesis_result.get("latest_extraction_md"))
    if synthesis_result.get("latest_extraction_pdf"):
        outputs["latest_extraction_pdf"] = str(synthesis_result.get("latest_extraction_pdf"))

    summary = {
        "paper_key": paper_key,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "job_id": ingestion_result.get("job_id"),
        "job_dir": ingestion_result.get("job_dir"),
        "stages": statuses,
        "outputs": outputs,
    }

    summary_path = run_dir / "full_pipeline_summary.json"
    _write_json(summary_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("factreview_full_pipeline")
    p.add_argument("paper_pdf", type=str, help="Path to paper PDF")
    p.add_argument("--paper-key", type=str, default="")
    p.add_argument("--run-root", type=str, default="runs")
    p.add_argument("--reuse-job-id", type=str, default="", help="Reuse existing data/jobs/<job_id>/job.json")
    p.add_argument("--skip-execution", action="store_true", help="Skip execution stage and continue to synthesis")
    p.add_argument("--max-attempts", type=int, default=5, help="Execution-stage max fix loop attempts")
    p.add_argument(
        "--no-pdf-extract",
        action="store_true",
        help="Pass through to external execution stage (skip MinerU in execution prepare).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_full_pipeline(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
