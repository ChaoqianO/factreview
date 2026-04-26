from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from common.runtime_shared.config import get_settings
from common.runtime_shared.env import load_env_file
from execution.stage_runner import run_execution_stage
from fact_extraction.stage_runner import run_fact_extraction_stage
from ingestion.runtime_bridge import init_full_pipeline_context, run_ingestion_stage
from llm.provider_capabilities import is_codex_provider
from positioning.stage_runner import run_positioning_stage
from reference_check.stage_runner import run_reference_check_stage
from synthesis.stage_runner import run_synthesis_stage
from util.paper_input import infer_paper_key, materialize_paper_pdf
from util.run_layout import build_run_dir, ensure_run_subdirs, make_run_id


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _set_env_if_value(name: str, value: str | None) -> None:
    token = str(value or "").strip()
    if token:
        os.environ[name] = token


def _apply_cli_env_overrides(args: argparse.Namespace) -> None:
    llm_provider = str(getattr(args, "llm_provider", "") or "").strip()
    if llm_provider:
        os.environ["MODEL_PROVIDER"] = llm_provider
        os.environ["CODE_EVAL_MODEL_PROVIDER"] = llm_provider
    _set_env_if_value("MINERU_API_TOKEN", getattr(args, "mineru_api_token", ""))
    _set_env_if_value("GEMINI_API_KEY", getattr(args, "gemini_api_key", ""))

    llm_model = str(getattr(args, "llm_model", "") or "").strip()
    if llm_model:
        os.environ["AGENT_MODEL"] = llm_model
        os.environ["CODE_EVAL_OPENAI_MODEL"] = llm_model
        provider = str(getattr(args, "llm_provider", "") or os.getenv("MODEL_PROVIDER") or "").strip()
        if is_codex_provider(provider):
            os.environ["OPENAI_CODEX_MODEL"] = llm_model

    teaser_mode = str(getattr(args, "teaser_mode", "auto") or "auto").strip().lower()
    if teaser_mode == "prompt":
        os.environ["TEASER_USE_GEMINI"] = "false"
    elif teaser_mode == "api":
        os.environ["TEASER_USE_GEMINI"] = "true"

    get_settings.cache_clear()


def run_full_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    settings = get_settings()
    paper_source = str(args.paper_pdf or "").strip()
    paper_key = (args.paper_key or "").strip() or infer_paper_key(paper_source)
    run_id = make_run_id()
    run_dir = build_run_dir(args.run_root, paper_key, run_id)
    layout = ensure_run_subdirs(run_dir)
    paper_input = materialize_paper_pdf(
        paper_source,
        layout["inputs"] / "source_pdf",
        paper_key=paper_key,
    )
    paper_pdf = paper_input.path
    init_full_pipeline_context(run_dir=run_dir)
    run_execution = bool(getattr(args, "run_execution", False)) and not bool(args.skip_execution)

    ingestion_result = run_ingestion_stage(
        repo_root=repo_root,
        run_dir=run_dir,
        paper_pdf=paper_pdf,
        paper_key=paper_key,
        reuse_job_id=str(args.reuse_job_id or "").strip(),
        materialize_execution_extract=run_execution,
    )
    fact_result = run_fact_extraction_stage(
        repo_root=repo_root,
        run_dir=run_dir,
    )
    enable_refcheck = bool(getattr(args, "enable_refcheck", False) or settings.reference_check_enabled)
    reference_check_result = run_reference_check_stage(
        repo_root=repo_root,
        run_dir=run_dir,
        paper_pdf=paper_pdf,
        paper_key=paper_key,
        enable_refcheck=enable_refcheck,
    )
    positioning_result = run_positioning_stage(
        repo_root=repo_root,
        run_dir=run_dir,
    )
    if not run_execution:
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
            paper_extracted_dir=str(
                (ingestion_result.get("shared_execution_extract") or {}).get("paper_extracted_dir") or ""
            ),
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
        "reference_check": str(reference_check_result.get("status") or "failed"),
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
    if reference_check_result.get("output"):
        outputs["reference_check"] = str(reference_check_result.get("output"))
    if reference_check_result.get("output_md"):
        outputs["reference_check_md"] = str(reference_check_result.get("output_md"))
    if execution_result.get("output"):
        outputs["execution"] = str(execution_result.get("output"))
    if synthesis_result.get("output_json"):
        outputs["synthesis_json"] = str(synthesis_result.get("output_json"))
    if synthesis_result.get("output_md"):
        outputs["synthesis_md"] = str(synthesis_result.get("output_md"))
    if synthesis_result.get("output_audit_json"):
        outputs["synthesis_audit_json"] = str(synthesis_result.get("output_audit_json"))
    if synthesis_result.get("output_pdf"):
        outputs["synthesis_pdf"] = str(synthesis_result.get("output_pdf"))
    if synthesis_result.get("teaser_figure_prompt"):
        outputs["teaser_figure_prompt"] = str(synthesis_result.get("teaser_figure_prompt"))
    if synthesis_result.get("teaser_figure_image"):
        outputs["teaser_figure_image"] = str(synthesis_result.get("teaser_figure_image"))

    summary = {
        "paper_key": paper_key,
        "paper_source": paper_input.source,
        "paper_source_type": paper_input.source_type,
        "paper_pdf": str(paper_pdf),
        "run_id": run_id,
        "run_dir": str(run_dir),
        "job_id": ingestion_result.get("job_id"),
        "job_dir": ingestion_result.get("job_dir"),
        "stages": statuses,
        "outputs": outputs,
        "reference_check": reference_check_result.get("reference_check") or {"enabled": enable_refcheck},
        "teaser_figure": synthesis_result.get("teaser_figure") or {},
    }

    summary_path = run_dir / "full_pipeline_summary.json"
    _write_json(summary_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("factreview_full_pipeline")
    p.add_argument("paper_pdf", type=str, help="Path or URL to a paper PDF")
    p.add_argument("--paper-key", type=str, default="")
    p.add_argument("--run-root", type=str, default="runs")
    p.add_argument("--reuse-job-id", type=str, default="", help="Reuse an existing runtime job snapshot")
    p.add_argument(
        "--llm-provider",
        type=str,
        default="",
        help="LLM provider override. Default is openai-codex after `codex login`.",
    )
    p.add_argument(
        "--llm-model",
        type=str,
        default="",
        help="LLM model override for the selected provider.",
    )
    p.add_argument(
        "--mineru-api-token",
        type=str,
        default="",
        help="MinerU API token override. Prefer MINERU_API_TOKEN in .env for routine use.",
    )
    p.add_argument(
        "--gemini-api-key",
        type=str,
        default="",
        help="Optional Gemini API key override for teaser image generation.",
    )
    p.add_argument(
        "--teaser-mode",
        choices=("auto", "prompt", "api"),
        default="auto",
        help="Teaser figure mode: auto attempts Gemini when a key exists, prompt saves/copies the prompt, api attempts the configured image API.",
    )
    p.add_argument(
        "--enable-refcheck",
        action="store_true",
        help="Run RefChecker reference-accuracy validation and append warning/error results to the final report.",
    )
    p.add_argument(
        "--run-execution",
        action="store_true",
        help="Run the repository execution/code-evaluation stage. Disabled by default.",
    )
    p.add_argument(
        "--skip-execution",
        action="store_true",
        help="Compatibility flag; execution is already skipped unless --run-execution is set.",
    )
    p.add_argument("--max-attempts", type=int, default=5, help="Execution-stage max fix loop attempts")
    p.add_argument(
        "--no-pdf-extract",
        action="store_true",
        help="Pass through to external execution stage (skip MinerU in execution prepare).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    load_env_file(Path(__file__).resolve().parents[1] / ".env")
    _apply_cli_env_overrides(args)
    summary = run_full_pipeline(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
