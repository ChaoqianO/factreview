"""Review teaser sub-stage.

Reads the report sub-stage's clean markdown (without the refcheck section, so
teaser prompts stay on the actual review content) and produces a teaser figure
prompt + image under ``stages/review/teaser/``.

When ``GEMINI_API_KEY`` is set and ``TEASER_USE_GEMINI`` is not ``false`` the
teaser image is generated via Gemini; otherwise only the prompt is written.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.pipeline_context import (  # noqa: E402
    ensure_full_pipeline_context,
    read_json_file,
    write_json_file,
)
from review.teaser.teaser import _env_true, generate_teaser_figure  # noqa: E402


def teaser_stage_dir(run_dir: Path) -> Path:
    return run_dir / "stages" / "review" / "teaser"


def run_teaser_stage(
    *,
    run_dir: Path,
) -> dict[str, Any]:
    ensure_full_pipeline_context(run_dir=run_dir, allow_standalone=True, stage="teaser")

    report_dir = run_dir / "stages" / "review" / "report"
    clean_md = report_dir / "final_review_clean.md"
    final_md = report_dir / "final_review.md"
    source_md = clean_md if clean_md.exists() else final_md

    out_dir = teaser_stage_dir(run_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    teaser_json_path = out_dir / "teaser_figure.json"

    if not source_md.exists():
        payload = {
            "status": "skipped",
            "message": f"no review markdown found at {source_md}",
            "source_markdown_path": "",
            "prompt_path": "",
            "image_path": "",
        }
        write_json_file(teaser_json_path, payload)
        return {"status": "skipped", "output_json": str(teaser_json_path)}

    use_gemini = _env_true("TEASER_USE_GEMINI", default=True)
    teaser_result = generate_teaser_figure(
        source_md,
        output_dir=out_dir,
        generate_image=use_gemini,
    )
    payload = {
        "status": teaser_result.status,
        "message": teaser_result.message,
        "clipboard_copied": teaser_result.clipboard_copied,
        "used_gemini_api": teaser_result.used_gemini_api,
        "model": teaser_result.model,
        "source_markdown_path": teaser_result.source_markdown_path,
        "prompt_path": teaser_result.prompt_path,
        "prompt": teaser_result.prompt,
        "image_path": teaser_result.image_path,
        "response_path": teaser_result.response_path,
    }
    write_json_file(teaser_json_path, payload)

    # Also append the teaser payload to the review JSON so a single artifact
    # captures the final review (report + teaser) outcome.
    review_json_path = report_dir / "final_review.json"
    review_payload = read_json_file(review_json_path)
    if review_payload:
        review_payload["teaser_figure"] = payload
        write_json_file(review_json_path, review_payload)

    result: dict[str, Any] = {
        "status": teaser_result.status,
        "output_json": str(teaser_json_path),
        "teaser_figure": payload,
    }
    if teaser_result.prompt_path:
        result["teaser_figure_prompt"] = teaser_result.prompt_path
    if teaser_result.image_path:
        result["teaser_figure_image"] = teaser_result.image_path
    return result


if __name__ == "__main__":
    raise SystemExit("Internal stage module. Use scripts/execute_review_pipeline.py.")
