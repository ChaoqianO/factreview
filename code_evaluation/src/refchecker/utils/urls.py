"""URL deduplication and selection utilities."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .doi import extract_doi, construct_doi_url
from .arxiv import extract_arxiv_id, construct_arxiv_url

_TRAILING_PUNCT = re.compile(r"[.,;:!?)>\]]+$")


def clean_url(url: str) -> str:
    """Remove trailing punctuation and fix common URL issues."""
    url = url.strip()
    url = _TRAILING_PUNCT.sub("", url)
    # Fix double slashes (not after protocol)
    url = re.sub(r"(?<!:)//+", "/", url)
    return url


def _normalize_for_dedup(url: str) -> str:
    """Normalize a URL for deduplication comparison."""
    url = clean_url(url).lower()
    # Remove trailing slash
    url = url.rstrip("/")
    # Remove common tracking params
    parsed = urlparse(url)
    # Use scheme + netloc + path as canonical form
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def deduplicate_urls(urls: list[str]) -> list[str]:
    """Remove duplicate URLs after normalization.

    Preserves order, keeping the first occurrence.
    """
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        key = _normalize_for_dedup(url)
        if key not in seen:
            seen.add(key)
            result.append(url)
    return result


def get_best_url(urls: dict[str, str | None]) -> str | None:
    """Select the best URL from candidates.

    Priority: DOI > ArXiv > Semantic Scholar > other.

    Args:
        urls: Mapping of source label to URL (value may be None).

    Returns:
        Best URL string, or None if no valid URL found.
    """
    # Filter out None values
    valid: dict[str, str] = {k: v for k, v in urls.items() if v}
    if not valid:
        return None

    all_urls = list(valid.values())

    # Check for DOI URL
    for url in all_urls:
        doi = extract_doi(url)
        if doi:
            return construct_doi_url(doi)

    # Check for ArXiv URL
    for url in all_urls:
        arxiv_id = extract_arxiv_id(url)
        if arxiv_id:
            return construct_arxiv_url(arxiv_id)

    # Check for Semantic Scholar
    for url in all_urls:
        if "semanticscholar.org" in url.lower():
            return clean_url(url)

    # Return first available
    return clean_url(all_urls[0])
