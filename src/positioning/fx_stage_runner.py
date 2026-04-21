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

from ingestion.fx_stage_runner import ensure_bridge_state, read_json_file, write_json_file


def run_positioning_stage(
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


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("run_positioning_fx_stage")
    p.add_argument("--run-dir", type=str, required=True)
    p.add_argument("--paper-pdf", type=str, default="")
    p.add_argument("--paper-key", type=str, default="")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = Path(args.run_dir).resolve()
    paper_pdf = Path(args.paper_pdf).resolve() if args.paper_pdf else None
    payload = run_positioning_stage(
        repo_root=repo_root,
        run_dir=run_dir,
        paper_pdf=paper_pdf,
        paper_key=(args.paper_key or "").strip() or None,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
