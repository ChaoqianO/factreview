"""ArXiv ID extraction, URL construction, and rate limiting."""

from __future__ import annotations

import re
import threading
import time

# Matches arXiv IDs: 1234.5678, 1234.5678v2, arXiv:1234.5678, etc.
_ARXIV_ID_PATTERN = re.compile(
    r"(?:arxiv(?:\.org/(?:abs|pdf|e-print)/)?[:\s]*)"
    r"(\d{4}\.\d{4,5}(?:v\d+)?)"
    r"|"
    r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b",
    re.IGNORECASE,
)

# Strip version suffix
_VERSION_SUFFIX = re.compile(r"v\d+$")


def extract_arxiv_id(text: str) -> str | None:
    """Extract an arXiv ID from text or URL.

    Handles: 1234.5678, 1234.5678v2, arxiv.org/abs/...,
    arxiv.org/pdf/....pdf, arXiv:1234.5678.
    """
    if not text:
        return None
    # Strip trailing .pdf
    cleaned = re.sub(r"\.pdf\s*$", "", text.strip(), flags=re.IGNORECASE)
    match = _ARXIV_ID_PATTERN.search(cleaned)
    if not match:
        return None
    return match.group(1) or match.group(2)


def construct_arxiv_url(arxiv_id: str) -> str:
    """Build canonical arXiv abstract URL."""
    return f"https://arxiv.org/abs/{arxiv_id}"


def normalize_arxiv_url(url: str) -> str:
    """Normalize an arXiv URL: use abs/ form, strip version."""
    arxiv_id = extract_arxiv_id(url)
    if not arxiv_id:
        return url
    # Remove version for canonical form
    base_id = _VERSION_SUFFIX.sub("", arxiv_id)
    return construct_arxiv_url(base_id)


class ArxivRateLimiter:
    """Singleton rate limiter for arXiv API calls.

    Enforces a minimum 3-second delay between consecutive calls.
    Thread-safe.
    """

    _instance: "ArxivRateLimiter | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "ArxivRateLimiter":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._last_call = 0.0
                    inst._call_lock = threading.Lock()
                    cls._instance = inst
        return cls._instance

    def wait(self) -> None:
        """Block until at least 3 seconds since the last call."""
        with self._call_lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < 3.0:
                time.sleep(3.0 - elapsed)
            self._last_call = time.monotonic()
