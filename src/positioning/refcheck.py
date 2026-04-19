"""Reference-checking adapter for the refchecker package.

Wraps the refchecker.ArxivReferenceChecker into a simpler API that
code_evaluation nodes can call without knowing refchecker internals.

Usage (library)::

    from src.tools.refcheck import check_references

    result = check_references(
        paper="2401.12345",          # arXiv ID, URL, or local PDF/tex path
        output_file="refs_out.txt",  # optional
    )
    # result -> {"total_refs": 42, "errors": 3, "warnings": 1, ...}

Usage (CLI, from code_evaluation/)::

    python -m src.tools.refcheck --paper 2401.12345
    python -m src.tools.refcheck --paper ./paper.pdf --output-file results.txt
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Ensure the vendored refchecker package (under tools/) is importable.
# src/positioning/refcheck.py -> repo_root/tools/refchecker/src
_REPO_ROOT = Path(__file__).resolve().parents[2]
_REFCHECKER_SRC = _REPO_ROOT / "tools" / "refchecker" / "src"
if _REFCHECKER_SRC.exists() and str(_REFCHECKER_SRC) not in sys.path:
    sys.path.insert(0, str(_REFCHECKER_SRC))


def _build_checker(
    *,
    api_key: str | None = None,
    db_path: str | None = None,
    output_file: str | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    debug: bool = False,
    enable_parallel: bool = True,
    max_workers: int = 4,
):
    """Construct an ArxivReferenceChecker with the given options."""
    from refchecker import ArxivReferenceChecker

    llm_config = None
    if llm_provider:
        llm_config = {
            "provider": llm_provider,
            "model": llm_model,
        }

    ss_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or os.environ.get("S2_API_KEY")

    return ArxivReferenceChecker(
        semantic_scholar_api_key=ss_key,
        db_path=db_path,
        output_file=output_file,
        llm_config=llm_config,
        debug_mode=debug,
        enable_parallel=enable_parallel,
        max_workers=max_workers,
    )


def check_references(
    paper: str,
    *,
    api_key: str | None = None,
    db_path: str | None = None,
    output_file: str | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    debug: bool = False,
    enable_parallel: bool = True,
    max_workers: int = 4,
) -> dict[str, Any]:
    """Run reference checking on *paper* and return a summary dict.

    Parameters
    ----------
    paper : str
        ArXiv ID (e.g. ``"2401.12345"``), arXiv URL, or local file path
        (``.pdf`` / ``.tex`` / ``.bib``).
    api_key : str, optional
        Semantic Scholar API key. Falls back to env vars.
    db_path : str, optional
        Path to a local Semantic Scholar SQLite database.
    output_file : str, optional
        If given, write the error report to this path.
    debug : bool
        Enable verbose logging.

    Returns
    -------
    dict with keys:
        ok              – True if the run completed (even if errors found)
        total_refs      – number of references processed
        errors          – number of errors found
        warnings        – number of warnings found
        unverified      – number of unverifiable references
        error_message   – non-empty string if the run itself failed
    """
    checker = _build_checker(
        api_key=api_key,
        db_path=db_path,
        output_file=output_file,
        llm_provider=llm_provider,
        llm_model=llm_model,
        debug=debug,
        enable_parallel=enable_parallel,
        max_workers=max_workers,
    )

    # Determine whether paper is a local file or an arXiv specifier.
    paper_path = Path(paper)
    is_local = paper_path.exists() and paper_path.is_file()

    try:
        if is_local:
            checker.run(debug_mode=debug, local_pdf_path=str(paper_path))
        else:
            checker.run(debug_mode=debug, specific_paper_id=paper)

        return {
            "ok": True,
            "total_refs": getattr(checker, "total_references_processed", 0),
            "errors": getattr(checker, "total_errors_found", 0),
            "warnings": getattr(checker, "total_warnings_found", 0),
            "unverified": getattr(checker, "total_unverified_refs", 0),
            "error_message": "",
        }
    except Exception as exc:
        logger.exception("refchecker run failed")
        return {
            "ok": False,
            "total_refs": 0,
            "errors": 0,
            "warnings": 0,
            "unverified": 0,
            "error_message": str(exc),
        }


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def _cli_main() -> int:
    p = argparse.ArgumentParser(
        prog="refcheck",
        description="Check references in an academic paper (adapter for refchecker).",
    )
    p.add_argument("--paper", required=True, help="ArXiv ID, URL, or local PDF/TeX path")
    p.add_argument("--db-path", default=None, help="Local Semantic Scholar DB path")
    p.add_argument("--output-file", default=None, help="Write error report to this path")
    p.add_argument("--llm-provider", default=None, help="LLM provider (openai, anthropic, ...)")
    p.add_argument("--llm-model", default=None, help="LLM model name")
    p.add_argument("--debug", action="store_true", help="Verbose logging")
    p.add_argument("--max-workers", type=int, default=4)
    args = p.parse_args()

    result = check_references(
        paper=args.paper,
        db_path=args.db_path,
        output_file=args.output_file,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        debug=args.debug,
        max_workers=args.max_workers,
    )

    if result["ok"]:
        print(f"References processed: {result['total_refs']}")
        print(
            f"Errors: {result['errors']}, Warnings: {result['warnings']}, Unverified: {result['unverified']}"
        )
        return 0
    else:
        print(f"ERROR: {result['error_message']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_cli_main())
