"""OpenAlex API checker."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from .base import BaseChecker, VerifyResult
from ..errors import error, unverified, validate_year
from ..utils.doi import extract_doi, normalize_doi, construct_doi_url
from ..utils.titles import compare_titles
from ..utils.authors import compare_authors

logger = logging.getLogger(__name__)

_API_BASE = "https://api.openalex.org"


class OpenAlexChecker(BaseChecker):
    """Verify references using the OpenAlex API."""

    def __init__(self, email: Optional[str] = None) -> None:
        self.email = email
        self._session = requests.Session()
        if email:
            self._session.params = {"mailto": email}  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def search_works(
        self, query: str, year: Optional[str] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search OpenAlex works by title."""
        params: Dict[str, Any] = {
            "search": query,
            "per_page": limit,
        }
        if year:
            params["filter"] = f"publication_year:{year}"
        try:
            resp = self._session.get(f"{_API_BASE}/works", params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("results", [])
        except requests.RequestException as exc:
            logger.warning("OpenAlex search error: %s", exc)
        return []

    def get_work_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetch a work by DOI."""
        doi = normalize_doi(doi)
        try:
            resp = self._session.get(
                f"{_API_BASE}/works/https://doi.org/{doi}", timeout=30
            )
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException as exc:
            logger.warning("OpenAlex DOI lookup error: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_metadata(work: Dict[str, Any]) -> Dict[str, Any]:
        """Build verified-data dict from an OpenAlex work record."""
        authors = []
        for authorship in work.get("authorships", []):
            author = authorship.get("author", {})
            name = author.get("display_name", "")
            if name:
                authors.append(name)

        doi = work.get("doi", "") or ""
        if doi.startswith("https://doi.org/"):
            doi = doi[len("https://doi.org/"):]

        return {
            "source": "openalex",
            "title": work.get("title", "") or work.get("display_name", ""),
            "authors": authors,
            "year": work.get("publication_year"),
            "doi": doi,
            "venue": (work.get("primary_location", {}) or {}).get("source", {}) or {},
            "url": work.get("id", ""),
        }

    def _best_match(
        self, works: List[Dict[str, Any]], cited_title: str
    ) -> Optional[Dict[str, Any]]:
        """Pick the best-matching work by title similarity."""
        best, best_sim = None, 0.0
        for w in works:
            w_title = w.get("title", "") or w.get("display_name", "")
            if not w_title:
                continue
            sim = compare_titles(cited_title, w_title)
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
            return None, [unverified("Not found in OpenAlex")], None

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
