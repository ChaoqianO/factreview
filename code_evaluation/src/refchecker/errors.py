"""Custom exceptions and error-creation helpers for reference checking."""

from __future__ import annotations
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class RefCheckError(Exception):
    """Base exception for all reference-checking errors."""


class APIError(RefCheckError):
    """An external API returned an unexpected response."""


class ExtractionError(RefCheckError):
    """Failed to extract bibliography / references from a document."""


class ConfigError(RefCheckError):
    """Invalid or missing configuration."""


# ---------------------------------------------------------------------------
# Standardised error / warning / info dict builders
# ---------------------------------------------------------------------------

def _make(kind: str, category: str, details: str, **extra: Any) -> Dict[str, Any]:
    d: Dict[str, Any] = {f"{kind}_type": category, f"{kind}_details": details}
    d.update(extra)
    return d


def error(category: str, details: str, **kw: Any) -> Dict[str, Any]:
    return _make("error", category, details, **kw)


def warning(category: str, details: str, **kw: Any) -> Dict[str, Any]:
    return _make("warning", category, details, **kw)


def info(category: str, details: str, **kw: Any) -> Dict[str, Any]:
    return _make("info", category, details, **kw)


# --- Convenience constructors for common error types --------------------

def author_error(cited: List[str], correct: List[str], detail: str) -> Dict[str, Any]:
    return error("author", detail, ref_authors_correct=", ".join(correct))


def title_error(cited: str, correct: str) -> Dict[str, Any]:
    detail = f"Title mismatch:\n  Cited:   {cited}\n  Correct: {correct}"
    return error("title", detail, ref_title_correct=correct)


def year_warning(cited: Any, correct: Any, *, flexible: bool = False) -> Dict[str, Any]:
    detail = f"Year mismatch: cited {cited}, correct {correct}"
    return warning("year", detail, ref_year_correct=str(correct))


def doi_error(cited: str, correct: str) -> Dict[str, Any]:
    detail = f"DOI mismatch:\n  Cited:   {cited}\n  Correct: {correct}"
    return error("doi", detail, ref_doi_correct=correct)


def venue_warning(cited: str, correct: str) -> Dict[str, Any]:
    detail = f"Venue mismatch:\n  Cited:   {cited}\n  Correct: {correct}"
    return warning("venue", detail)


def unverified(reason: str) -> Dict[str, Any]:
    return error("unverified", reason)


def api_failure(source: str, detail: str) -> Dict[str, Any]:
    return error("api_failure", f"{source}: {detail}")


# ---------------------------------------------------------------------------
# Year validation
# ---------------------------------------------------------------------------

def validate_year(
    cited_year: Any,
    paper_year: Any,
    *,
    tolerance: int = 1,
    use_flexible: bool = False,
) -> Optional[Dict[str, Any]]:
    """Return a year-warning dict if years differ beyond *tolerance*, else None."""
    if not cited_year or not paper_year:
        return None
    try:
        cy, py = int(cited_year), int(paper_year)
    except (ValueError, TypeError):
        return None
    if abs(cy - py) <= tolerance:
        return None
    return year_warning(cy, py, flexible=use_flexible)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def format_title_mismatch(cited: str, correct: str) -> str:
    return f"Title mismatch:\n  Cited:   {cited}\n  Correct: {correct}"


def format_author_mismatch(cited: List[str], correct: List[str]) -> str:
    return (
        f"Author mismatch:\n"
        f"  Cited:   {', '.join(cited)}\n"
        f"  Correct: {', '.join(correct)}"
    )
