"""Multi-strategy reference parsing from bibliography text.

Strategies tried in order:
1. BibTeX  (@article{...})
2. BibLaTeX / .bbl  (numbered [N] entries with \\newblock)
3. Regex   (fallback for plain/PDF-extracted text)
4. LLM     (if an extractor is supplied and earlier methods fail)
"""

from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_references(
    text: str,
    *,
    llm_extractor: Any | None = None,
) -> list[dict]:
    """Parse references from bibliography *text* using best available strategy."""
    if not text or not text.strip():
        return []

    if detect_bibtex_format(text):
        refs = parse_bibtex(text)
        if refs:
            log.info("Parsed %d references via BibTeX", len(refs))
            return refs

    if detect_biblatex_format(text):
        refs = parse_biblatex(text)
        if refs:
            log.info("Parsed %d references via BibLaTeX", len(refs))
            return refs

    refs = parse_regex(text)
    if refs:
        log.info("Parsed %d references via regex", len(refs))
        return refs

    if llm_extractor is not None:
        try:
            refs = llm_extractor.extract(text)
            if refs:
                log.info("Parsed %d references via LLM", len(refs))
                return refs
        except Exception:
            log.warning("LLM extraction failed", exc_info=True)

    log.warning("No references could be parsed from the bibliography text")
    return []


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

_BIBTEX_ENTRY = re.compile(
    r"@(?:article|inproceedings|book|misc|phdthesis|mastersthesis|techreport"
    r"|incollection|conference|unpublished)\s*\{",
    re.IGNORECASE,
)

_BIBLATEX_ENTRY = re.compile(r"^\s*\[\d+\]", re.MULTILINE)


def detect_bibtex_format(text: str) -> bool:
    """Return ``True`` if *text* looks like BibTeX."""
    return len(_BIBTEX_ENTRY.findall(text)) >= 2


def detect_biblatex_format(text: str) -> bool:
    """Return ``True`` if *text* contains numbered [N] entries."""
    return len(_BIBLATEX_ENTRY.findall(text)) >= 3


# ---------------------------------------------------------------------------
# BibTeX parser
# ---------------------------------------------------------------------------

_BIBTEX_BLOCK = re.compile(
    r"@(\w+)\s*\{\s*([^,]*?)\s*,(.*?)\n\s*\}",
    re.DOTALL,
)
_BIBTEX_FIELD = re.compile(
    r"(\w+)\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|\"([^\"]*)\"|(\d+))",
)

_LATEX_ESCAPES = [
    (re.compile(r"\\&"), "&"),
    (re.compile(r"\\'\\i"), "i"),
    (re.compile(r"\\\"\{([a-zA-Z])\}"), r"\1"),  # \"{o} -> o
    (re.compile(r"\\'\{([a-zA-Z])\}"), r"\1"),
    (re.compile(r"\\'([a-zA-Z])"), r"\1"),
    (re.compile(r"\\~\{([a-zA-Z])\}"), r"\1"),
    (re.compile(r"\\`\{([a-zA-Z])\}"), r"\1"),
    (re.compile(r"\\[\"'^`~.=]([a-zA-Z])"), r"\1"),
    (re.compile(r"\{([^{}]*)\}"), r"\1"),
]


def _clean_latex(value: str) -> str:
    for pat, repl in _LATEX_ESCAPES:
        value = pat.sub(repl, value)
    return value.strip()


def parse_bibtex(text: str) -> list[dict]:
    """Parse BibTeX entries, with optional ``bibtexparser`` acceleration."""
    refs = _parse_bibtex_library(text)
    if refs is not None:
        return refs
    return _parse_bibtex_regex(text)


def _parse_bibtex_library(text: str) -> list[dict] | None:
    """Try parsing with the ``bibtexparser`` package."""
    try:
        import bibtexparser  # noqa: F811
    except ImportError:
        return None

    try:
        bib_db = bibtexparser.loads(text)
    except Exception:
        log.debug("bibtexparser.loads failed, falling back to regex")
        return None

    refs: list[dict] = []
    for entry in bib_db.entries:
        url_info = _extract_urls_from_text(
            " ".join(entry.get(k, "") for k in ("url", "doi", "eprint", "note"))
        )
        ref: dict[str, Any] = {
            "title": _clean_latex(entry.get("title", "")),
            "authors": _split_authors(entry.get("author", "")),
            "year": entry.get("year", ""),
            "venue": entry.get("journal", "") or entry.get("booktitle", ""),
            "doi": entry.get("doi", "") or url_info.get("doi", ""),
            "url": entry.get("url", "") or url_info.get("url", ""),
            "arxiv_id": entry.get("eprint", "") or url_info.get("arxiv_id", ""),
            "raw_text": str(entry),
            "type": _classify_reference_dict(url_info),
        }
        refs.append(ref)
    return refs


def _parse_bibtex_regex(text: str) -> list[dict]:
    refs: list[dict] = []
    for m in _BIBTEX_BLOCK.finditer(text):
        entry_type = m.group(1).lower()
        raw = m.group(0)
        fields: dict[str, str] = {}
        for fm in _BIBTEX_FIELD.finditer(m.group(3)):
            key = fm.group(1).lower()
            val = fm.group(2) or fm.group(3) or fm.group(4) or ""
            fields[key] = _clean_latex(val)

        url_info = _extract_urls_from_text(
            " ".join(fields.get(k, "") for k in ("url", "doi", "eprint", "note"))
        )
        ref: dict[str, Any] = {
            "title": fields.get("title", ""),
            "authors": _split_authors(fields.get("author", "")),
            "year": fields.get("year", ""),
            "venue": fields.get("journal", "") or fields.get("booktitle", ""),
            "doi": fields.get("doi", "") or url_info.get("doi", ""),
            "url": fields.get("url", "") or url_info.get("url", ""),
            "arxiv_id": fields.get("eprint", "") or url_info.get("arxiv_id", ""),
            "raw_text": raw,
            "type": _classify_reference_dict(url_info),
        }
        refs.append(ref)
    return refs


# ---------------------------------------------------------------------------
# BibLaTeX / .bbl parser
# ---------------------------------------------------------------------------

_BBL_SPLIT = re.compile(r"(?=\[\d+\])")
_BBL_NUM = re.compile(r"^\[(\d+)\]\s*")
_BBL_TITLE_QUOTED = re.compile(r"[\"\"](.*?)[\"\"]")
_BBL_YEAR = re.compile(r"\b((?:19|20)\d{2})\b")


def parse_biblatex(text: str) -> list[dict]:
    """Parse numbered ``[N]`` entries from .bbl or similar text."""
    blocks = _BBL_SPLIT.split(text)
    refs: list[dict] = []
    for block in blocks:
        block = block.strip()
        nm = _BBL_NUM.match(block)
        if not nm:
            continue
        body = block[nm.end():]
        url_info = _extract_urls_from_text(body)

        # Title heuristic: first quoted string, else first sentence
        title = ""
        tm = _BBL_TITLE_QUOTED.search(body)
        if tm:
            title = tm.group(1).strip()
        else:
            sentences = re.split(r"\.(?:\s|$)", body, maxsplit=3)
            if len(sentences) >= 2:
                title = sentences[1].strip()

        # Year
        year = ""
        ym = _BBL_YEAR.search(body)
        if ym:
            year = ym.group(1)

        # Authors: text before the title or first sentence
        authors_text = body.split(".")[0] if "." in body else body[:80]

        ref: dict[str, Any] = {
            "title": _clean_latex(title),
            "authors": _split_authors(authors_text),
            "year": year,
            "venue": "",
            "doi": url_info.get("doi", ""),
            "url": url_info.get("url", ""),
            "arxiv_id": url_info.get("arxiv_id", ""),
            "raw_text": block,
            "type": _classify_reference_dict(url_info),
        }
        refs.append(ref)
    return refs


# ---------------------------------------------------------------------------
# Regex parser (PDF-extracted text)
# ---------------------------------------------------------------------------

_REF_SPLIT = re.compile(r"(?=\[\d+\]\s)")
_REF_NUM = re.compile(r"^\[(\d+)\]\s*")
_REF_ARXIV_VENUE = re.compile(
    r"arXiv\s+preprint\s+arXiv:(\d{4}\.\d{4,5})", re.IGNORECASE
)
_REF_IN_PROC = re.compile(r"In\s+(Proceedings\s+of\s+.+?),?\s*((?:19|20)\d{2})")
_REF_YEAR_TAIL = re.compile(r",?\s*((?:19|20)\d{2})\.?\s*$")
_REF_AUTHORS_YEAR = re.compile(
    r"^(.+?),\s*((?:19|20)\d{2})\.\s*(.+)",
    re.DOTALL,
)


def parse_regex(text: str) -> list[dict]:
    """Best-effort regex parsing for PDF-extracted bibliography text."""
    blocks = _REF_SPLIT.split(text)
    refs: list[dict] = []
    for block in blocks:
        block = block.strip()
        nm = _REF_NUM.match(block)
        if not nm:
            continue
        body = block[nm.end():]
        ref = _parse_single_regex(body, block)
        if ref:
            refs.append(ref)
    return refs


def _parse_single_regex(body: str, raw: str) -> dict | None:
    """Parse a single reference entry from its text body."""
    url_info = _extract_urls_from_text(body)

    # Try "Authors, Year. Title. Venue." format
    am = _REF_AUTHORS_YEAR.match(body)
    if am:
        return _build_ref(
            authors_text=am.group(1),
            year=am.group(2),
            title=am.group(3).split(".")[0].strip(),
            raw=raw,
            url_info=url_info,
        )

    # Standard: "Authors. Title. Venue, Year."
    parts = re.split(r"\.(?:\s|$)", body, maxsplit=3)
    authors_text = parts[0] if parts else ""
    title = parts[1].strip() if len(parts) > 1 else ""

    year = ""
    ym = _BBL_YEAR.search(body)
    if ym:
        year = ym.group(1)

    arxiv_m = _REF_ARXIV_VENUE.search(body)
    if arxiv_m:
        url_info.setdefault("arxiv_id", arxiv_m.group(1))

    return _build_ref(
        authors_text=authors_text,
        year=year,
        title=title,
        raw=raw,
        url_info=url_info,
    )


def _build_ref(
    *,
    authors_text: str,
    year: str,
    title: str,
    raw: str,
    url_info: dict,
) -> dict:
    return {
        "title": _clean_latex(title),
        "authors": _split_authors(authors_text),
        "year": year,
        "venue": "",
        "doi": url_info.get("doi", ""),
        "url": url_info.get("url", ""),
        "arxiv_id": url_info.get("arxiv_id", ""),
        "raw_text": raw,
        "type": _classify_reference_dict(url_info),
    }


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})")
_DOI_PATTERN = re.compile(r"(?:https?://doi\.org/|doi:\s*)(10\.\d{4,}/[^\s,]+)")
_URL_PATTERN = re.compile(r"https?://[^\s,)]+")


def _extract_urls_from_text(text: str) -> dict:
    """Extract ArXiv IDs, DOIs, and URLs from reference text."""
    info: dict[str, str] = {}

    m = _ARXIV_URL.search(text)
    if m:
        info["arxiv_id"] = m.group(1)

    m = _DOI_PATTERN.search(text)
    if m:
        info["doi"] = m.group(1).rstrip(".")

    m = _URL_PATTERN.search(text)
    if m:
        info["url"] = m.group(0).rstrip(".")

    return info


def _classify_reference_dict(url_info: dict) -> str:
    """Classify a reference as 'arxiv', 'non-arxiv', or 'other'."""
    if url_info.get("arxiv_id"):
        return "arxiv"
    if url_info.get("doi") or url_info.get("url"):
        return "non-arxiv"
    return "other"


# Keep public alias
_classify_reference = _classify_reference_dict


def _split_authors(text: str) -> list[str]:
    """Split an author string into individual names."""
    if not text:
        return []
    # BibTeX uses "and" as separator
    if " and " in text:
        parts = re.split(r"\s+and\s+", text)
    else:
        parts = re.split(r";\s*|,\s*(?=[A-Z])", text)
    return [p.strip() for p in parts if p.strip()]
