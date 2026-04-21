from __future__ import annotations

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


def run_fact_extraction_stage(
    *,
    repo_root: Path,
    run_dir: Path,
) -> dict[str, Any]:
    ensure_full_pipeline_context(run_dir=run_dir)
    bridge = require_bridge_state(run_dir=run_dir)

    job_state = read_json_file(bridge.job_json_path)
    artifacts = job_state.get("artifacts") if isinstance(job_state.get("artifacts"), dict) else {}
    metadata = job_state.get("metadata") if isinstance(job_state.get("metadata"), dict) else {}
    annotation_count = int(job_state.get("annotation_count") or 0)
    annotations_raw = str(artifacts.get("annotations_path") or "").strip()

    annotations = resolve_artifact_path(repo_root, annotations_raw)
    has_annotations_file = annotations is not None and annotations.exists()
    annotations_payload: dict[str, Any] | list[Any]
    if has_annotations_file:
        annotations_payload = read_json_file(annotations)
    else:
        # factreview-own completed jobs can legitimately have zero annotations and no annotations.json.
        annotations_payload = []

    facts_out = run_dir / "stages" / "fact_extraction" / "facts.json"
    write_json_file(
        facts_out,
        {
            "annotation_count": annotation_count,
            "annotations_path": annotations_raw if has_annotations_file else "",
            "annotations": annotations_payload,
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
        "status": "ok" if (has_annotations_file or annotation_count == 0) else "failed",
        "output": str(facts_out),
        "job_id": bridge.job_id,
    }


if __name__ == "__main__":
    raise SystemExit("Internal stage module. Use scripts/run_full_pipeline.py.")
