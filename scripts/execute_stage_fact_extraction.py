from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fact_extraction.stage_runner import run_fact_extraction_stage


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("factreview_stage_fact_extraction")
    p.add_argument("--run-dir", type=str, required=True, help="Run directory to write stage outputs")
    p.add_argument("--paper-pdf", type=str, default="", help="Optional bootstrap PDF when bridge is missing")
    p.add_argument("--paper-key", type=str, default="")
    p.add_argument("--reuse-job-id", type=str, default="", help="Optional bootstrap with existing job id")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()
    paper_pdf = Path(args.paper_pdf).resolve() if str(args.paper_pdf or "").strip() else None
    payload = run_fact_extraction_stage(
        repo_root=ROOT,
        run_dir=run_dir,
        paper_pdf=paper_pdf,
        paper_key=str(args.paper_key or "").strip(),
        reuse_job_id=str(args.reuse_job_id or "").strip(),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
