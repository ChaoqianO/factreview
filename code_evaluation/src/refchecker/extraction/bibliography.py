"""Bibliography section detection and extraction from paper text."""

from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Start patterns – tried in order, first match wins
# ---------------------------------------------------------------------------
_START_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\d+\s*references\s*\n", re.IGNORECASE),
    re.compile(r"^references\s*\n", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^bibliography\s*\n", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\\begin\{thebibliography\}", re.IGNORECASE),
    re.compile(r"\\bibliography\{[^}]*\}", re.IGNORECASE),
    # Roman numeral section header, e.g. "IX. References"
    re.compile(
        r"^[IVXLC]+\.\s*references\s*\n", re.IGNORECASE | re.MULTILINE
    ),
]

# ---------------------------------------------------------------------------
# End patterns – searched *after* bibliography start
# ---------------------------------------------------------------------------
_END_PATTERNS: list[re.Pattern[str]] = [
    # Appendix headers: "A. Some Title", "Appendix A", etc.
    re.compile(
        r"^(?:appendix\s+)?[A-C]\.\s+[A-Z]", re.MULTILINE
    ),
    re.compile(r"^appendix\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^SUPPLEMENTARY\s+MATERIAL", re.MULTILINE),
    re.compile(r"^ACKNOWLEDGMENTS?\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^AUTHOR\s+CONTRIBUTIONS?\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\\end\{thebibliography\}", re.IGNORECASE),
    re.compile(r"\\end\{document\}", re.IGNORECASE),
]

# Fallback: cluster of bracketed numbers like [1], [2], ...
_BRACKET_NUM = re.compile(r"\[\d+\]")

_MIN_LENGTH = 50


def find_bibliography(text: str) -> str | None:
    """Find and return the bibliography section from *text*, or ``None``."""
    if not text:
        return None

    start_pos = _find_start(text)
    if start_pos is None:
        return None

    bib_text = text[start_pos:]
    end_pos = _find_end(bib_text)
    if end_pos is not None:
        bib_text = bib_text[:end_pos]

    bib_text = bib_text.strip()
    if len(bib_text) < _MIN_LENGTH:
        return None

    log.debug("Bibliography found (%d chars)", len(bib_text))
    return bib_text


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_start(text: str) -> int | None:
    """Return the character offset where the bibliography begins."""
    for pat in _START_PATTERNS:
        m = pat.search(text)
        if m:
            return m.start()

    # Fallback: look for a cluster of [N] references
    matches = list(_BRACKET_NUM.finditer(text))
    if len(matches) >= 5:
        # Use position of the first bracketed number in the densest cluster
        # Simple heuristic: take the first match in the last third of the text
        third = len(text) // 3
        late_matches = [m for m in matches if m.start() >= third]
        if late_matches:
            return late_matches[0].start()
        return matches[0].start()

    return None


def _find_end(bib_text: str) -> int | None:
    """Return the offset *within bib_text* where the bibliography ends."""
    earliest: int | None = None
    for pat in _END_PATTERNS:
        m = pat.search(bib_text)
        if m and (earliest is None or m.start() < earliest):
            earliest = m.start()
    return earliest
