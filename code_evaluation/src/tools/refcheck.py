"""Reference-checking adapter – wraps src.refchecker into a simple API.

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
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _build_checker(
    *,
    api_key: Optional[str] = None,
    db_path: Optional[str] = None,
    output_file: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    debug: bool = False,
    enable_parallel: bool = True,
    max_workers: int = 4,
):
    """Construct a ReferenceChecker with the given options."""
    from src.refchecker import ReferenceChecker

    llm_config = None
    if llm_provider:
        llm_config = {
            "provider": llm_provider,
            "model": llm_model,
        }

    ss_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or os.environ.get("S2_API_KEY")

    return ReferenceChecker(
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
    api_key: Optional[str] = None,
    db_path: Optional[str] = None,
    output_file: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    debug: bool = False,
    enable_parallel: bool = True,
    max_workers: int = 4,
) -> Dict[str, Any]:
    """Run reference checking on *paper* and return a summary dict.

    Returns
    -------
    dict with keys: ok, total_refs, errors, warnings, unverified, error_message
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

    paper_path = Path(paper)
    is_local = paper_path.exists() and paper_path.is_file()

    try:
        if is_local:
            checker.run(debug_mode=debug, local_pdf_path=str(paper_path))
        else:
            checker.run(debug_mode=debug, specific_paper_id=paper)

        return {
            "ok": True,
            "total_refs": checker.total_references_processed,
            "errors": checker.total_errors_found,
            "warnings": checker.total_warnings_found,
            "unverified": checker.total_unverified_refs,
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
        description="Check references in an academic paper.",
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
        print(f"Errors: {result['errors']}, Warnings: {result['warnings']}, Unverified: {result['unverified']}")
        return 0
    else:
        print(f"ERROR: {result['error_message']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_cli_main())
