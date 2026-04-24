from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("execute_review_runtime_job")
    p.add_argument("--paper-pdf", required=True)
    p.add_argument("--title", default="factreview-job")
    return p.parse_args()


def main() -> None:
    from common.runtime_shared.runner import run_job
    from common.runtime_shared.state import ensure_artifact_paths, load_job_state, mutate_job_state, save_job_state
    from common.runtime_shared.types import JobState

    args = parse_args()
    source_pdf = Path(args.paper_pdf).resolve()
    if not source_pdf.exists():
        raise FileNotFoundError(f"paper pdf not found: {source_pdf}")

    job = JobState(title=str(args.title), source_pdf_name=source_pdf.name)
    save_job_state(job)
    artifacts = ensure_artifact_paths(str(job.id))

    shutil.copy2(source_pdf, artifacts["source_pdf"])

    def _apply(state: JobState) -> None:
        state.artifacts.source_pdf_path = str(artifacts["source_pdf"])

    mutate_job_state(str(job.id), _apply)

    run_job(str(job.id))
    final_state = load_job_state(str(job.id))
    if final_state is None:
        raise RuntimeError("failed to load final job state")

    payload = {
        "job_id": str(job.id),
        "status": final_state.status.value,
        "message": final_state.message,
        "error": final_state.error,
        "artifacts": final_state.artifacts.model_dump(mode="json"),
        "usage": final_state.usage.model_dump(mode="json"),
        "metadata": final_state.metadata,
        "annotation_count": int(final_state.annotation_count),
        "final_report_ready": bool(final_state.final_report_ready),
        "pdf_ready": bool(final_state.pdf_ready),
        "job_json_path": str((Path("data") / "jobs" / str(job.id) / "job.json").resolve()),
        "job_dir": str((Path("data") / "jobs" / str(job.id)).resolve()),
        "latest_output_md": str(Path(artifacts["latest_output_md"]).resolve()),
        "latest_output_pdf": str(Path(artifacts["latest_output_pdf"]).resolve()),
        "final_report_audit_json": str(Path(artifacts["final_report_audit"]).resolve()),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
