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
    write_json_file,
)


def run_positioning_stage(
    *,
    repo_root: Path,
    run_dir: Path,
) -> dict[str, Any]:
    _ = repo_root
    ensure_full_pipeline_context(run_dir=run_dir)
    bridge = require_bridge_state(run_dir=run_dir)

    job_state = read_json_file(bridge.job_json_path)
    metadata = job_state.get("metadata") if isinstance(job_state.get("metadata"), dict) else {}

    semantic_path = bridge.job_dir / "semantic_scholar_candidates.json"
    semantic_payload = read_json_file(semantic_path)
    if not semantic_payload:
        semantic_payload = {"success": False, "papers": []}

    paper_search_state = (
        metadata.get("paper_search_runtime_state")
        if isinstance(metadata.get("paper_search_runtime_state"), dict)
        else {}
    )
    search_started = bool(paper_search_state.get("started"))
    semantic_file_exists = semantic_path.exists()
    status = "ok" if (semantic_file_exists or (not search_started)) else "failed"

    positioning_out = run_dir / "stages" / "positioning" / "positioning.json"
    write_json_file(
        positioning_out,
        {
            "semantic_scholar": semantic_payload,
            "paper_search_runtime_state": paper_search_state,
            "job_id": bridge.job_id,
            "job_json_path": str(bridge.job_json_path),
        },
    )

    return {
        "status": status,
        "output": str(positioning_out),
        "job_id": bridge.job_id,
    }


if __name__ == "__main__":
    raise SystemExit("Internal stage module. Use scripts/execute_review_pipeline.py.")
