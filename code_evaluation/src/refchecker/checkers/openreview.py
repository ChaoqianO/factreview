"""OpenReview checker for ML conference papers."""

from __future__ import annotations
import logging
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .base import BaseChecker, VerifyResult
from ..utils.titles import compare_titles
from ..utils.authors import compare_authors
from ..errors import validate_year, unverified

logger = logging.getLogger(__name__)

_OR_VENUES = {"iclr", "icml", "neurips", "nips", "aaai", "ijcai", "emnlp", "acl", "naacl"}


class OpenReviewChecker(BaseChecker):
    """Verify references via the OpenReview API."""

    def __init__(self, request_delay: float = 1.0):
        self.api_url = "https://api2.openreview.net"
        self.delay = request_delay
        self._last = 0.0

    def is_openreview_reference(self, ref: Dict[str, Any]) -> bool:
        url = ref.get("url", "")
        if "openreview.net" in url:
            return True
        venue = (ref.get("venue") or ref.get("journal") or "").lower()
        return any(v in venue for v in _OR_VENUES)

    def verify_reference(self, ref: Dict[str, Any]) -> VerifyResult:
        import requests

        url = ref.get("url", "")
        paper_id = self._extract_id(url) if "openreview.net" in url else None

        if paper_id:
            meta = self._fetch(requests, paper_id)
            if meta:
                return self._compare(meta, ref)

        # Search by title
        title = ref.get("title", "").strip()
        if not title:
            return None, [], None
        self._rate_limit()
        try:
            r = requests.get(f"{self.api_url}/notes/search",
                             params={"query": title, "limit": 5}, timeout=15)
            if r.status_code == 200:
                for note in r.json().get("notes", []):
                    content = note.get("content", {})
                    t = content.get("title", {})
                    t = t.get("value", t) if isinstance(t, dict) else t
                    if t and compare_titles(title, str(t)) > 0.85:
                        meta = self._parse(note)
                        return self._compare(meta, ref)
        except Exception as e:
            logger.debug("OpenReview search failed: %s", e)

        return None, [], None

    # ------------------------------------------------------------------
    def _extract_id(self, url: str) -> Optional[str]:
        m = re.search(r"id=([^&]+)", url)
        return m.group(1) if m else None

    def _fetch(self, requests, paper_id: str) -> Optional[Dict]:
        self._rate_limit()
        try:
            r = requests.get(f"{self.api_url}/notes", params={"id": paper_id}, timeout=15)
            if r.status_code == 200:
                notes = r.json().get("notes", [])
                if notes:
                    return self._parse(notes[0])
        except Exception as e:
            logger.debug("OpenReview fetch failed: %s", e)
        return None

    def _parse(self, note: Dict) -> Dict:
        content = note.get("content", {})
        def _val(v):
            return v.get("value", v) if isinstance(v, dict) else v
        authors = _val(content.get("authors", []))
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(",")]
        return {
            "title": str(_val(content.get("title", ""))),
            "authors": authors,
            "year": note.get("cdate", note.get("pdate")),
            "venue": str(_val(content.get("venue", ""))),
            "url": f"https://openreview.net/forum?id={note.get('id', '')}",
        }

    def _compare(self, meta: Dict, ref: Dict) -> VerifyResult:
        errors: List[Dict[str, Any]] = []
        cited_authors = ref.get("authors", [])
        if cited_authors and meta.get("authors"):
            ok, msg = compare_authors(cited_authors, meta["authors"])
            if not ok:
                errors.append({"error_type": "author", "error_details": msg})
        yw = validate_year(ref.get("year"), meta.get("year"))
        if yw:
            errors.append(yw)
        return meta, errors, meta.get("url")

    def _rate_limit(self):
        elapsed = time.time() - self._last
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last = time.time()
