"""Semantic Scholar API checker."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from .base import BaseChecker, VerifyResult
from ..errors import error, warning, unverified, api_failure, validate_year
from ..utils.doi import extract_doi, normalize_doi
from ..utils.titles import compare_titles
from ..utils.authors import compare_authors

logger = logging.getLogger(__name__)

_API_BASE = "https://api.semanticscholar.org/graph/v1"
_FIELDS = "title,authors,year,externalIds,venue,url"
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0


class SemanticScholarChecker(BaseChecker):
    """Verify references using the Semantic Scholar API."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key
        self._session = requests.Session()
        if api_key:
            self._session.headers["x-api-key"] = api_key

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """GET with retry and rate-limit handling."""
        for attempt in range(_MAX_RETRIES):
            try:
                resp = self._session.get(url, params=params, timeout=30)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 429:
                    wait = _BACKOFF_BASE ** (attempt + 1)
                    logger.info("S2 rate-limited, waiting %.1fs", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code == 404:
                    return None
                logger.debug("S2 returned %s for %s", resp.status_code, url)
            except requests.RequestException as exc:
                logger.warning("S2 request error: %s", exc)
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_BACKOFF_BASE ** attempt)
        return None

    def search_paper(
        self, query: str, year: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Search Semantic Scholar by title query."""
        params: Dict[str, Any] = {"query": query, "fields": _FIELDS, "limit": 5}
        if year:
            params["year"] = year
        data = self._get(f"{_API_BASE}/paper/search", params)
        if data and data.get("data"):
            return data["data"][0]
        return None

    def get_paper_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Lookup a paper by DOI."""
        doi = normalize_doi(doi)
        return self._get(f"{_API_BASE}/paper/DOI:{doi}", {"fields": _FIELDS})

    # ------------------------------------------------------------------
    # Main interface
    # ------------------------------------------------------------------

    def _extract_metadata(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """Build a verified-data dict from an S2 paper record."""
        authors = [a.get("name", "") for a in paper.get("authors", [])]
        ext_ids = paper.get("externalIds", {}) or {}
        return {
            "source": "semantic_scholar",
            "title": paper.get("title", ""),
            "authors": authors,
            "year": paper.get("year"),
            "doi": ext_ids.get("DOI", ""),
            "venue": paper.get("venue", ""),
            "url": paper.get("url", ""),
        }

    def verify_reference(self, reference: Dict[str, Any]) -> VerifyResult:
        paper: Optional[Dict[str, Any]] = None

        # Try DOI first
        doi = extract_doi(reference.get("doi", "") or reference.get("url", ""))
        if doi:
            paper = self.get_paper_by_doi(doi)

        # Fall back to title search
        if not paper:
            title = reference.get("title", "")
            if not title:
                return None, [], None
            paper = self.search_paper(title, reference.get("year"))

        if not paper:
            return None, [unverified("Not found in Semantic Scholar")], None

        verified = self._extract_metadata(paper)
        errors: List[Dict[str, Any]] = []
        url = verified.get("url")

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
                verified["authors"],
            )
            if not match:
                errors.append(error("author", detail, ref_authors_correct=", ".join(verified["authors"])))

        # Compare year
        yr_err = validate_year(reference.get("year"), verified.get("year"))
        if yr_err:
            errors.append(yr_err)

        return verified, errors, url
