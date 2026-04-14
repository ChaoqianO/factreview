"""CrossRef API checker."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from .base import BaseChecker, VerifyResult
from ..errors import error, unverified, api_failure, validate_year
from ..utils.doi import extract_doi, normalize_doi, construct_doi_url
from ..utils.titles import compare_titles
from ..utils.authors import compare_authors

logger = logging.getLogger(__name__)

_API_BASE = "https://api.crossref.org"


class CrossRefChecker(BaseChecker):
    """Verify references using the CrossRef API."""

    def __init__(self, email: Optional[str] = None) -> None:
        self.email = email
        self._session = requests.Session()
        ua = "RefChecker/1.0 (https://github.com/refchecker; mailto:refchecker@example.com)"
        if email:
            ua = f"RefChecker/1.0 (https://github.com/refchecker; mailto:{email})"
        self._session.headers["User-Agent"] = ua

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def search_works(
        self, query: str, year: Optional[str] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search CrossRef works by title query."""
        params: Dict[str, Any] = {"query.bibliographic": query, "rows": limit}
        if year:
            params["filter"] = f"from-pub-date:{year},until-pub-date:{year}"
        try:
            resp = self._session.get(f"{_API_BASE}/works", params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("items", [])
        except requests.RequestException as exc:
            logger.warning("CrossRef search error: %s", exc)
        return []

    def get_work_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetch a work by DOI."""
        doi = normalize_doi(doi)
        try:
            resp = self._session.get(f"{_API_BASE}/works/{doi}", timeout=30)
            if resp.status_code == 200:
                return resp.json().get("message")
        except requests.RequestException as exc:
            logger.warning("CrossRef DOI lookup error: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_metadata(work: Dict[str, Any]) -> Dict[str, Any]:
        """Build verified-data dict from a CrossRef work record."""
        title_list = work.get("title", [])
        title = title_list[0] if title_list else ""

        authors = []
        for a in work.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)

        date_parts = work.get("published-print", work.get("published-online", {}))
        year = ""
        if isinstance(date_parts, dict):
            parts = date_parts.get("date-parts", [[]])
            if parts and parts[0]:
                year = str(parts[0][0])

        return {
            "source": "crossref",
            "title": title,
            "authors": authors,
            "year": year,
            "doi": work.get("DOI", ""),
            "venue": work.get("container-title", [""])[0] if work.get("container-title") else "",
            "url": construct_doi_url(work.get("DOI", "")) if work.get("DOI") else "",
        }

    def _best_match(
        self, works: List[Dict[str, Any]], cited_title: str
    ) -> Optional[Dict[str, Any]]:
        """Pick the best-matching work from a list by title similarity."""
        best, best_sim = None, 0.0
        for w in works:
            titles = w.get("title", [])
            if not titles:
                continue
            sim = compare_titles(cited_title, titles[0])
            if sim > best_sim:
                best_sim = sim
                best = w
        if best_sim >= 0.80:
            return best
        return None

    # ------------------------------------------------------------------
    # Main interface
    # ------------------------------------------------------------------

    def verify_reference(self, reference: Dict[str, Any]) -> VerifyResult:
        work: Optional[Dict[str, Any]] = None

        # Try DOI first
        doi = extract_doi(reference.get("doi", "") or reference.get("url", ""))
        if doi:
            work = self.get_work_by_doi(doi)

        # Fall back to title search
        if not work:
            title = reference.get("title", "")
            if not title:
                return None, [], None
            works = self.search_works(title, reference.get("year"))
            work = self._best_match(works, title)

        if not work:
            return None, [unverified("Not found in CrossRef")], None

        verified = self._extract_metadata(work)
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
