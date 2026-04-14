"""Generic web-page checker for non-academic references."""

from __future__ import annotations
import logging
import time
from typing import Any, Dict, List, Optional

from .base import BaseChecker, VerifyResult

logger = logging.getLogger(__name__)


class WebPageChecker(BaseChecker):
    """Verify references by fetching web pages and checking titles."""

    def __init__(self, request_delay: float = 1.0):
        self.delay = request_delay
        self._last = 0.0

    def verify_reference(self, ref: Dict[str, Any]) -> VerifyResult:
        import requests

        url = ref.get("url", "").strip()
        if not url or not url.startswith("http"):
            return None, [], None

        self._rate_limit()
        try:
            r = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (compatible; RefChecker/3.0)"
            })
            if r.status_code != 200:
                return None, [], url

            title = self._extract_title(r.text)
            verified = {
                "title": title or "",
                "url": url,
            }
            return verified, [], url

        except Exception as e:
            logger.debug("Web page fetch failed for %s: %s", url, e)
            return None, [], url

    @staticmethod
    def _extract_title(html: str) -> Optional[str]:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            tag = soup.find("title")
            return tag.get_text(strip=True) if tag else None
        except ImportError:
            import re
            m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            return m.group(1).strip() if m else None

    def _rate_limit(self):
        elapsed = time.time() - self._last
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last = time.time()
