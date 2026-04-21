from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ingestion.fx_stage_runner import (
    ensure_bridge_state,
    read_json_file,
    resolve_artifact_path,
    write_json_file,
)


def run_fact_extraction_stage(
    *,
    repo_root: Path,
    run_dir: Path,
    paper_pdf: Path | None = None,
    paper_key: str | None = None,
) -> dict[str, Any]:
    bridge = ensure_bridge_state(
        repo_root=repo_root,
        run_dir=run_dir,
        paper_pdf=paper_pdf,
        paper_key=paper_key,
    )

    job_state = read_json_file(bridge.job_json_path)
    artifacts = job_state.get("artifacts") if isinstance(job_state.get("artifacts"), dict) else {}
    metadata = job_state.get("metadata") if isinstance(job_state.get("metadata"), dict) else {}

    annotations = resolve_artifact_path(repo_root, artifacts.get("annotations_path"))

    facts_out = run_dir / "stages" / "fact_extraction" / "facts.json"
    write_json_file(
        facts_out,
        {
            "annotation_count": int(job_state.get("annotation_count") or 0),
            "annotations_path": str(annotations) if (annotations is not None and annotations.exists()) else "",
            "annotations": read_json_file(annotations)
            if (annotations is not None and annotations.exists())
            else {},
            "usage": job_state.get("usage") or {},
            "metadata": {
                "final_report_sections_completed": metadata.get("final_report_sections_completed") or [],
                "final_report_source": metadata.get("final_report_source"),
            },
            "job_id": bridge.job_id,
            "job_json_path": str(bridge.job_json_path),
        },
    )

    return {
        "status": "ok" if (annotations is not None and annotations.exists()) else "failed",
        "output": str(facts_out),
        "job_id": bridge.job_id,
    }


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("run_fact_extraction_fx_stage")
    p.add_argument("--run-dir", type=str, required=True)
    p.add_argument("--paper-pdf", type=str, default="")
    p.add_argument("--paper-key", type=str, default="")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = Path(args.run_dir).resolve()
    paper_pdf = Path(args.paper_pdf).resolve() if args.paper_pdf else None
    payload = run_fact_extraction_stage(
        repo_root=repo_root,
        run_dir=run_dir,
        paper_pdf=paper_pdf,
        paper_key=(args.paper_key or "").strip() or None,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
