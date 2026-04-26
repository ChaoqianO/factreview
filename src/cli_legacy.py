import argparse
import asyncio
import os
from pathlib import Path

from common.runtime_shared.env import load_env_file
from execution.graph import CodeEvalOrchestrator


def _load_env_file(env_path: Path) -> None:
    load_env_file(env_path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        "code_evaluation", description="Paper code evaluation runner (LangGraph-based)"
    )
    p.add_argument(
        "paper_pdf_pos",
        nargs="?",
        default="",
        help="Optional positional paper PDF path or URL. Equivalent to --paper-pdf.",
    )
    p.add_argument(
        "local_repo_pos",
        nargs="?",
        default="",
        help="Optional positional local repository folder path. If provided, it will be copied into this run's workspace/source and cloning will be skipped.",
    )
    p.add_argument(
        "--paper-pdf",
        type=str,
        default="",
        help="Path or URL to the paper PDF. If provided, the system will try to extract repo URL(s) and prepare a run-local source checkout automatically.",
    )
    p.add_argument(
        "--paper-key",
        type=str,
        default="",
        help="Folder name under papers/ to store this paper (optional; auto-derived from pdf name if omitted).",
    )
    p.add_argument(
        "--paper-root", type=str, default="", help="Path to the paper/code repository root (optional)"
    )
    p.add_argument(
        "--tasks",
        type=str,
        default="",
        help="Path to tasks file (yaml/json). Describes how to run experiments.",
    )
    p.add_argument(
        "--baseline",
        type=str,
        default="",
        help="Path to baseline json file for deterministic comparisons.",
    )
    p.add_argument(
        "--no-pdf-extract",
        action="store_true",
        help="Disable PDF structure extraction (MinerU/magic-pdf). By default, extraction is REQUIRED when --paper-pdf is provided.",
    )
    p.add_argument(
        "--run-dir",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "runs" / "execution"),
        help="Run root for execution artifacts; actual runs use <paper_key>_<timestamp>",
    )
    p.add_argument("--max-attempts", type=int, default=5, help="Max fix loop attempts per run")
    p.add_argument(
        "--no-llm", action="store_true", help="Disable all LLM usage (triage only deterministic fixes)"
    )
    p.add_argument("--llm-model", type=str, default="", help="LLM model id (optional, depends on provider)")
    p.add_argument(
        "--llm-provider",
        type=str,
        default="",
        help="LLM provider: openai/openai-codex/deepseek/qwen/claude/ollama (optional)",
    )
    p.add_argument("--llm-base-url", type=str, default="", help="LLM base url (optional)")
    p.add_argument(
        "--dry-run", action="store_true", help="Do not execute commands; just plan and write run skeleton"
    )
    p.add_argument(
        "--auto-tasks",
        action="store_true",
        help="Auto-generate tasks.yaml from the cloned repo (README/entrypoints). Uses LLM if available; otherwise heuristics.",
    )
    p.add_argument(
        "--auto-tasks-mode",
        type=str,
        default="smoke",
        choices=["smoke", "full"],
        help="Task inference mode: smoke (safe, fast) or full (may propose heavier tasks; disabled by default).",
    )
    p.add_argument(
        "--auto-tasks-force",
        action="store_true",
        help="Overwrite existing tasks.yaml when using --auto-tasks.",
    )
    # Integrated capabilities (optional, off by default)
    p.add_argument(
        "--enable-refcheck",
        action="store_true",
        help="Run reference-accuracy checking on the paper PDF (requires refchecker deps).",
    )
    p.add_argument(
        "--enable-bibtex",
        action="store_true",
        help="Enrich facts.json with BibTeX for paper claims via Semantic Scholar.",
    )
    # Default: verbose console logs ON (users asked for flow-level tracing).
    # Use --quiet to disable. --verbose kept for backwards compatibility.
    p.add_argument(
        "--quiet", action="store_true", help="Disable verbose console logs (still writes run/* logs)"
    )
    p.add_argument(
        "--verbose", action="store_true", help="(Deprecated) Print step-by-step workflow logs to console"
    )
    return p.parse_args()


async def _amain() -> int:
    args = parse_args()
    root = Path(__file__).parent
    _load_env_file(root / ".env")
    # Verbose console logs are ON by default.
    # - If user explicitly sets CODE_EVAL_VERBOSE in env/.env, honor it.
    # - --quiet forces it off.
    # - --verbose forces it on (for backwards compatibility).
    if args.quiet:
        os.environ["CODE_EVAL_VERBOSE"] = "0"
    else:
        if args.verbose or ("CODE_EVAL_VERBOSE" not in os.environ):
            os.environ["CODE_EVAL_VERBOSE"] = "1"

    # Allow simple usage: `python main.py <paper.pdf>`
    if not args.paper_pdf and args.paper_pdf_pos:
        args.paper_pdf = args.paper_pdf_pos

    orchestrator = CodeEvalOrchestrator(
        run_root=args.run_dir,
        max_attempts=args.max_attempts,
        no_llm=args.no_llm,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_base_url=args.llm_base_url,
        dry_run=args.dry_run,
        auto_tasks=args.auto_tasks,
        auto_tasks_mode=args.auto_tasks_mode,
        auto_tasks_force=args.auto_tasks_force,
        enable_refcheck=args.enable_refcheck,
        enable_bibtex=args.enable_bibtex,
    )
    result = await orchestrator.run(
        paper_root=args.paper_root,
        paper_pdf=args.paper_pdf,
        paper_key=args.paper_key,
        tasks_path=args.tasks,
        baseline_path=args.baseline,
        local_source_path=args.local_repo_pos,
        no_pdf_extract=args.no_pdf_extract,
    )
    # Three-value exit semantics:
    #   0 = verified success (baseline checks passed)
    #   1 = failed (execution error or check failure)
    #   2 = inconclusive (ran OK but insufficient baseline to verify)
    exit_status = str(result.get("exit_status") or "failed")
    exit_code_map = {"success": 0, "failed": 1, "inconclusive": 2}
    exit_code = exit_code_map.get(exit_status, 1)

    try:
        st = result.get("state") or {}
        run_id = (st.get("run") or {}).get("id")
        paper_key = (st.get("config") or {}).get("paper_key")
        paper_root = (st.get("config") or {}).get("paper_root")
        repo_url = (st.get("config") or {}).get("paper_repo_url")
        report = None
        run_dir = (st.get("run") or {}).get("dir")
        if run_id and run_dir:
            report = Path(run_dir) / "reports" / f"{run_id}.md"
        if not paper_key and run_dir:
            try:
                name = Path(run_dir).name
                marker = f"_{run_id}"
                paper_key = name[: -len(marker)] if name.endswith(marker) else name
            except Exception:
                pass
        print("")
        print("=== Code Evaluation Summary ===")
        print(f"status   : {exit_status}")
        print(f"exit code: {exit_code}  (0=verified, 1=failed, 2=inconclusive)")
        print(f"paper    : {paper_key}")
        print(f"run id   : {run_id}")
        if repo_url:
            print(f"repo url : {repo_url}")
        if paper_root:
            print(f"source   : {paper_root}")
        if report and report.exists():
            print(f"report   : {report}")
        if run_dir:
            print(f"run dir  : {run_dir}")
            if exit_code != 0:
                print(f"see      : {Path(run_dir) / 'issues.md'}")
    except Exception:
        pass
    return exit_code


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
