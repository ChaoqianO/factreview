"""DOI extraction and comparison utilities."""

from __future__ import annotations

import re

# Matches DOI patterns: 10.XXXX/...
# DOI can appear as: doi:10.xxx/yyy, https://doi.org/10.xxx/yyy, bare 10.xxx/yyy
_DOI_PATTERN = re.compile(
    r"(?:https?://(?:dx\.)?doi\.org/|doi:\s*)"
    r"(10\.\d{4,9}/[^\s,;\"')\]}>]+)"
    r"|"
    r"\b(10\.\d{4,9}/[^\s,;\"')\]}>]+)",
    re.IGNORECASE,
)


def extract_doi(text: str) -> str | None:
    """Extract a DOI from text or URL.

    Handles doi.org URLs, 'doi:' prefix, and bare 10.XXXX/... patterns.
    Returns the normalized DOI or None.
    """
    if not text:
        return None
    match = _DOI_PATTERN.search(text)
    if not match:
        return None
    raw = match.group(1) or match.group(2)
    return normalize_doi(raw)


def normalize_doi(doi: str) -> str:
    """Normalize a DOI: lowercase and strip common prefixes."""
    doi = doi.strip()
    # Remove URL prefixes
    for prefix in ("https://doi.org/", "http://doi.org/",
                   "https://dx.doi.org/", "http://dx.doi.org/"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
            break
    # Remove "doi:" prefix
    if doi.lower().startswith("doi:"):
        doi = doi[4:].strip()
    # Strip trailing punctuation that may have been captured
    doi = doi.rstrip(".,;:)")
    return doi.lower()


def compare_dois(doi1: str, doi2: str) -> bool:
    """Compare two DOIs after normalization."""
    if not doi1 or not doi2:
        return False
    return normalize_doi(doi1) == normalize_doi(doi2)


def construct_doi_url(doi: str) -> str:
    """Build a canonical DOI URL."""
    doi = normalize_doi(doi)
    return f"https://doi.org/{doi}"
