from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ingestion.runtime_bridge import run_ingestion_stage


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("factreview_stage_ingestion")
    p.add_argument("paper_pdf", type=str, help="Path to paper PDF")
    p.add_argument("--paper-key", type=str, default="")
    p.add_argument("--run-dir", type=str, required=True, help="Run directory to write stage outputs")
    p.add_argument("--reuse-job-id", type=str, default="", help="Reuse an existing runtime job snapshot")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    paper_pdf = Path(args.paper_pdf).resolve()
    if not paper_pdf.exists():
        raise FileNotFoundError(f"paper pdf not found: {paper_pdf}")
    run_dir = Path(args.run_dir).resolve()
    paper_key = (args.paper_key or "").strip() or paper_pdf.stem.strip() or "paper"
    payload = run_ingestion_stage(
        repo_root=ROOT,
        run_dir=run_dir,
        paper_pdf=paper_pdf,
        paper_key=paper_key,
        reuse_job_id=str(args.reuse_job_id or "").strip(),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
