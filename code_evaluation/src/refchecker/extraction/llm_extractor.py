"""LLM-based reference extraction fallback."""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """\
Extract every bibliographic reference from the text below.
Return ONLY a JSON array (no markdown fences, no commentary).
Each element must be an object with these keys:
  title     (string)
  authors   (array of strings – one per author)
  year      (string)
  venue     (string – journal / conference name, or empty string)
  doi       (string or empty)
  url       (string or empty)
  arxiv_id  (string or empty, e.g. "2301.12345")

Text:
{text}
"""

_MAX_CHUNK = 8000
_OVERLAP = 400


# ---------------------------------------------------------------------------
# Abstract provider
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Interface that concrete LLM back-ends must implement."""

    @abstractmethod
    def call(self, prompt: str) -> str:
        """Send *prompt* and return the model's text response."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return ``True`` if the provider is usable (package + credentials)."""


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class LLMExtractor:
    """Wraps an :class:`LLMProvider` to extract references from raw text."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        fallback_enabled: bool = False,
    ) -> None:
        self.provider = provider
        self.fallback_enabled = fallback_enabled

    # -- public --

    def extract(self, bibliography_text: str) -> list[dict]:
        """Extract references from *bibliography_text* via the LLM."""
        if not self.provider.is_available():
            log.warning("LLM provider is not available; skipping extraction")
            return []

        chunks = _chunk_text(bibliography_text)
        all_refs: list[dict] = []
        for i, chunk in enumerate(chunks, 1):
            prompt = _build_prompt(chunk)
            log.debug("Sending chunk %d/%d to LLM (%d chars)", i, len(chunks), len(chunk))
            try:
                response = self.provider.call(prompt)
                refs = _parse_response(response)
                all_refs.extend(refs)
            except Exception:
                log.warning("LLM extraction failed for chunk %d", i, exc_info=True)

        if len(chunks) > 1:
            all_refs = _deduplicate(all_refs)

        log.info("LLM extracted %d references", len(all_refs))
        return all_refs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_prompt(text: str) -> str:
    """Build the extraction prompt with the bibliography text inserted."""
    return _EXTRACTION_PROMPT.format(text=text)


def _chunk_text(text: str, max_chars: int = _MAX_CHUNK) -> list[str]:
    """Split long text into overlapping chunks."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start = end - _OVERLAP
    return chunks


def _parse_response(response: str) -> list[dict]:
    """Parse the LLM JSON response into a list of reference dicts."""
    # Strip markdown fences if present
    cleaned = response.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find a JSON array in the response
        m = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                log.warning("Could not parse LLM response as JSON")
                return []
        else:
            log.warning("No JSON array found in LLM response")
            return []

    if not isinstance(data, list):
        return []

    refs: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ref = {
            "title": str(item.get("title", "")),
            "authors": _ensure_str_list(item.get("authors", [])),
            "year": str(item.get("year", "")),
            "venue": str(item.get("venue", "")),
            "doi": str(item.get("doi", "")),
            "url": str(item.get("url", "")),
            "arxiv_id": str(item.get("arxiv_id", "")),
            "raw_text": "",
            "type": "other",
        }
        # Classify
        if ref["arxiv_id"]:
            ref["type"] = "arxiv"
        elif ref["doi"] or ref["url"]:
            ref["type"] = "non-arxiv"
        refs.append(ref)
    return refs


def _ensure_str_list(val: object) -> list[str]:
    if isinstance(val, list):
        return [str(v) for v in val]
    if isinstance(val, str):
        return [val]
    return []


def _deduplicate(refs: list[dict]) -> list[dict]:
    """Remove duplicate references produced by overlapping chunks."""
    seen: set[str] = set()
    unique: list[dict] = []
    for ref in refs:
        key = _dedup_key(ref)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        unique.append(ref)
    return unique


def _dedup_key(ref: dict) -> str:
    """Create a normalised key for deduplication."""
    title = ref.get("title", "").lower().strip()
    if not title:
        return ""
    # Use first 60 chars of title to handle minor differences
    return title[:60]
