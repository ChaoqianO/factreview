"""
ReferenceChecker – main orchestrator for reference validation.

Replaces the original 5838-line ArxivReferenceChecker with a clean,
modular design that delegates to focused sub-modules.
"""

from __future__ import annotations

import datetime
import io
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .config import get_config
from .errors import unverified

logger = logging.getLogger(__name__)


class ReferenceChecker:
    """Validate references in academic papers.

    Parameters
    ----------
    semantic_scholar_api_key : str, optional
        API key for Semantic Scholar (higher rate limits).
    db_path : str, optional
        Path to local Semantic Scholar SQLite database for offline mode.
    output_file : str, optional
        Write error report to this file.
    llm_config : dict, optional
        LLM provider configuration for bibliography extraction.
    debug_mode : bool
        Enable verbose logging.
    enable_parallel : bool
        Use parallel reference verification.
    max_workers : int
        Number of parallel worker threads.
    """

    def __init__(
        self,
        semantic_scholar_api_key: Optional[str] = None,
        db_path: Optional[str] = None,
        output_file: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        debug_mode: bool = False,
        enable_parallel: bool = True,
        max_workers: int = 4,
    ):
        self.db_path = db_path
        self.output_file = output_file
        self.debug_mode = debug_mode
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self.config = get_config()

        # Statistics
        self.total_references_processed = 0
        self.total_errors_found = 0
        self.total_warnings_found = 0
        self.total_unverified_refs = 0
        self.errors: List[Dict[str, Any]] = []

        # ArXiv client
        try:
            import arxiv
            self.arxiv_client = arxiv.Client(
                page_size=100, delay_seconds=3, num_retries=5,
            )
        except ImportError:
            self.arxiv_client = None

        # Main checker
        if db_path:
            from .db import ThreadSafeDBChecker
            self.checker = ThreadSafeDBChecker(db_path) if enable_parallel else None
            if not enable_parallel:
                from .checkers.local_db import LocalDBChecker
                self.checker = LocalDBChecker(db_path)
        else:
            from .checkers.hybrid import HybridChecker
            self.checker = HybridChecker(
                semantic_scholar_api_key=semantic_scholar_api_key,
                db_path=None,
                enable_openalex=True,
                enable_crossref=True,
                enable_arxiv_citation=True,
                debug_mode=debug_mode,
            )

        # LLM extractor
        self.llm_extractor = self._init_llm(llm_config)
        self.llm_enabled = self.llm_extractor is not None

        # Metadata cache
        self._cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        *,
        specific_paper_id: Optional[str] = None,
        local_pdf_path: Optional[str] = None,
        debug_mode: bool = False,
    ):
        """Run the full validation pipeline on a paper."""
        paper = self._resolve_paper(specific_paper_id, local_pdf_path)
        if paper is None:
            logger.error("Could not resolve paper")
            return

        # Extract bibliography text
        bib_text = self._extract_bibliography(paper)
        if not bib_text:
            logger.error("Could not extract bibliography")
            return

        # Parse references
        from .extraction.parsers import parse_references
        bibliography = parse_references(bib_text, llm_extractor=self.llm_extractor)
        if not bibliography:
            logger.error("No references parsed from bibliography")
            return

        logger.info("Parsed %d references", len(bibliography))
        self.total_references_processed = len(bibliography)

        # Verify references
        if self.enable_parallel and len(bibliography) > 1:
            self._verify_parallel(paper, bibliography)
        else:
            self._verify_sequential(paper, bibliography)

        # Write output
        if self.output_file:
            self._write_report()

        logger.info(
            "Done: %d refs, %d errors, %d warnings, %d unverified",
            self.total_references_processed,
            self.total_errors_found,
            self.total_warnings_found,
            self.total_unverified_refs,
        )

    # ------------------------------------------------------------------
    # Paper resolution
    # ------------------------------------------------------------------

    def _resolve_paper(self, paper_id: Optional[str], local_path: Optional[str]):
        if local_path:
            return _LocalPaper(local_path)

        if paper_id and paper_id.startswith("http"):
            return _LocalPaper(paper_id, is_url=True)

        if paper_id and self.arxiv_client:
            import arxiv
            try:
                search = arxiv.Search(id_list=[paper_id])
                results = list(self.arxiv_client.results(search))
                return results[0] if results else None
            except Exception as e:
                logger.error("ArXiv fetch failed for %s: %s", paper_id, e)
        return None

    # ------------------------------------------------------------------
    # Bibliography extraction
    # ------------------------------------------------------------------

    def _extract_bibliography(self, paper) -> Optional[str]:
        text = self._get_paper_text(paper)
        if not text:
            return None

        from .extraction.bibliography import find_bibliography
        return find_bibliography(text)

    def _get_paper_text(self, paper) -> Optional[str]:
        # Local file
        if hasattr(paper, "file_path") and paper.file_path:
            path = paper.file_path
            if hasattr(paper, "is_url") and paper.is_url:
                from .pdf_service import download_pdf, extract_text
                buf = download_pdf(path)
                return extract_text(buf) if buf else None
            if path.lower().endswith((".tex", ".bbl")):
                return Path(path).read_text(encoding="utf-8", errors="replace")
            if path.lower().endswith(".txt"):
                return Path(path).read_text(encoding="utf-8", errors="replace")
            # PDF
            from .pdf_service import extract_text
            with open(path, "rb") as f:
                return extract_text(io.BytesIO(f.read()))

        # ArXiv paper
        pdf_url = getattr(paper, "pdf_url", None)
        if not pdf_url:
            aid = getattr(paper, "get_short_id", lambda: None)()
            if aid:
                pdf_url = f"https://arxiv.org/pdf/{aid}.pdf"
        if pdf_url:
            from .pdf_service import download_pdf, extract_text
            buf = download_pdf(pdf_url)
            return extract_text(buf) if buf else None
        return None

    # ------------------------------------------------------------------
    # Reference verification
    # ------------------------------------------------------------------

    def verify_reference(self, source_paper, reference: Dict) -> tuple:
        """Verify a single reference. Returns (errors, url, verified_data)."""
        # Skip URL-only references
        authors = reference.get("authors", [])
        if isinstance(authors, list) and authors and isinstance(authors[0], dict):
            if authors[0].get("is_url_reference"):
                return [], reference.get("url"), None

        verified_data, errors, url = self.checker.verify_reference(reference)

        # Count errors
        for e in errors:
            if e.get("error_type") == "unverified":
                self.total_unverified_refs += 1
            elif "error_type" in e:
                self.total_errors_found += 1
            elif "warning_type" in e:
                self.total_warnings_found += 1

        self.errors.extend(errors)
        return errors, url, verified_data

    def _verify_sequential(self, paper, bibliography: List[Dict]):
        for i, ref in enumerate(bibliography):
            title = ref.get("title", "Unknown")
            logger.info("[%d/%d] %s", i + 1, len(bibliography), title[:80])
            self.verify_reference(paper, ref)

    def _verify_parallel(self, paper, bibliography: List[Dict]):
        from .parallel import ParallelProcessor

        def _callback(result):
            for e in (result.errors or []):
                if e.get("error_type") == "unverified":
                    self.total_unverified_refs += 1
                elif "error_type" in e:
                    self.total_errors_found += 1
                elif "warning_type" in e:
                    self.total_warnings_found += 1
                self.errors.append(e)

        proc = ParallelProcessor(self.verify_reference, self.max_workers)
        proc.run(paper, bibliography, callback=_callback)

    # ------------------------------------------------------------------
    # LLM initialisation
    # ------------------------------------------------------------------

    def _init_llm(self, llm_config: Optional[Dict]) -> Optional[Any]:
        if not llm_config or llm_config.get("disabled"):
            return None

        provider_name = llm_config.get("provider")
        if not provider_name:
            return None

        provider_cfg = self.config.get("llm", {}).get(provider_name, {}).copy()
        for k in ("model", "api_key", "endpoint"):
            if llm_config.get(k):
                provider_cfg[k] = llm_config[k]

        from .llm.providers import create_provider
        provider = create_provider(provider_name, provider_cfg)
        if not provider:
            return None

        from .extraction.llm_extractor import LLMExtractor
        return LLMExtractor(provider, fallback_enabled=False)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _write_report(self):
        if not self.errors or not self.output_file:
            return
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(f"Reference Validation Report\n")
                f.write(f"Generated: {datetime.datetime.now()}\n")
                f.write(f"Total references: {self.total_references_processed}\n")
                f.write(f"Errors: {self.total_errors_found}\n")
                f.write(f"Warnings: {self.total_warnings_found}\n")
                f.write(f"Unverified: {self.total_unverified_refs}\n\n")
                for i, e in enumerate(self.errors, 1):
                    kind = e.get("error_type") or e.get("warning_type") or e.get("info_type", "unknown")
                    detail = e.get("error_details") or e.get("warning_details") or e.get("info_details", "")
                    f.write(f"[{i}] {kind}: {detail}\n")
        except Exception as exc:
            logger.error("Failed to write report: %s", exc)


# ------------------------------------------------------------------
# Internal paper object for local files / URLs
# ------------------------------------------------------------------

class _LocalPaper:
    def __init__(self, path: str, is_url: bool = False):
        self.file_path = path
        self.is_url = is_url
        self.is_latex = path.lower().endswith(".tex")
        self.authors: List = []
        name = os.path.splitext(os.path.basename(urlparse(path).path if is_url else path))[0]
        self.title = name.replace("_", " ").title() if name else "Unknown"

        class _Pub:
            year = datetime.datetime.now().year
        self.published = _Pub()
        self.pdf_url = path if is_url else None

    def get_short_id(self):
        name = os.path.splitext(os.path.basename(self.file_path))[0]
        prefix = "url_" if self.is_url else "local_"
        return f"{prefix}{name}"
