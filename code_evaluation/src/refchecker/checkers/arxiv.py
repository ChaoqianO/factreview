"""ArXiv BibTeX checker -- authoritative source for ArXiv papers."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import requests

from .base import BaseChecker, VerifyResult
from ..errors import error, warning, unverified, api_failure, validate_year
from ..utils.arxiv import extract_arxiv_id, ArxivRateLimiter
from ..utils.text import strip_latex_commands
from ..utils.titles import compare_titles
from ..utils.authors import compare_authors

try:
    import bibtexparser
except ImportError:
    bibtexparser = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_BIBTEX_FIELD = re.compile(r"(\w+)\s*=\s*\{([^}]*)\}", re.DOTALL)
_RATE_LIMITER = ArxivRateLimiter(min_interval=3.0)


class ArxivChecker(BaseChecker):
    """Verify references against ArXiv BibTeX records."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def extract_arxiv_id(reference: Dict[str, Any]) -> Optional[str]:
        """Extract an ArXiv ID from a reference dict."""
        for field in ("url", "arxiv_id", "raw_text", "note"):
            value = reference.get(field, "")
            if value:
                aid = extract_arxiv_id(str(value))
                if aid:
                    return aid
        return None

    def fetch_bibtex(self, arxiv_id: str) -> Optional[str]:
        """Fetch the official BibTeX entry from ArXiv."""
        url = f"https://arxiv.org/bibtex/{arxiv_id}"
        _RATE_LIMITER.wait()
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200 and "@" in resp.text:
                return resp.text
            logger.debug("ArXiv BibTeX fetch returned %s for %s", resp.status_code, arxiv_id)
        except requests.RequestException as exc:
            logger.warning("ArXiv BibTeX request failed for %s: %s", arxiv_id, exc)
        return None

    @staticmethod
    def parse_bibtex(bibtex_str: str) -> Dict[str, str]:
        """Parse a BibTeX string into a field dict."""
        if bibtexparser is not None:
            try:
                lib = bibtexparser.parse(bibtex_str)
                if lib.entries:
                    entry = lib.entries[0]
                    return {k: str(v) for k, v in entry.fields_dict.items()}
            except Exception:
                pass
        # Fallback regex parser
        fields: Dict[str, str] = {}
        for m in _BIBTEX_FIELD.finditer(bibtex_str):
            fields[m.group(1).lower()] = m.group(2).strip()
        return fields

    # ------------------------------------------------------------------
    # Main interface
    # ------------------------------------------------------------------

    def verify_reference(self, reference: Dict[str, Any]) -> VerifyResult:
        arxiv_id = self.extract_arxiv_id(reference)
        if not arxiv_id:
            return None, [], None

        url = f"https://arxiv.org/abs/{arxiv_id}"
        bibtex_str = self.fetch_bibtex(arxiv_id)
        if not bibtex_str:
            return None, [api_failure("arxiv", f"Could not fetch BibTeX for {arxiv_id}")], url

        fields = self.parse_bibtex(bibtex_str)
        if not fields:
            return None, [api_failure("arxiv", f"Could not parse BibTeX for {arxiv_id}")], url

        verified: Dict[str, Any] = {
            "source": "arxiv",
            "arxiv_id": arxiv_id,
            "title": strip_latex_commands(fields.get("title", "")),
            "authors": strip_latex_commands(fields.get("author", "")),
            "year": fields.get("year", ""),
        }

        errors: List[Dict[str, Any]] = []

        # Compare title
        cited_title = reference.get("title", "")
        if cited_title and verified["title"]:
            sim = compare_titles(cited_title, verified["title"])
            if sim < 0.85:
                errors.append(error(
                    "title",
                    f"Title mismatch (similarity {sim:.2f}):\n"
                    f"  Cited:   {cited_title}\n"
                    f"  Correct: {verified['title']}",
                    ref_title_correct=verified["title"],
                ))

        # Compare authors
        cited_authors = reference.get("authors", [])
        if cited_authors and verified["authors"]:
            match, detail = compare_authors(
                cited_authors if isinstance(cited_authors, list) else [cited_authors],
                [verified["authors"]],
            )
            if not match:
                errors.append(error("author", detail, ref_authors_correct=verified["authors"]))

        # Compare year
        yr_err = validate_year(reference.get("year"), verified["year"])
        if yr_err:
            errors.append(yr_err)

        return verified, errors, url
