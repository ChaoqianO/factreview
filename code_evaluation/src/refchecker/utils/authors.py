"""Author name parsing and comparison utilities."""

import re

from .text import clean_author_name, normalize_text

_SPLIT_AND = re.compile(r"\band\b", re.IGNORECASE)
_ET_AL = re.compile(r"\bet\s+al\.?", re.IGNORECASE)
_INITIAL = re.compile(r"^[A-Z]\.?$")


def normalize_author_name(name: str) -> str:
    """Normalize an author name for comparison.

    Strips punctuation, normalizes whitespace, lowercases,
    and removes diacritics.
    """
    name = clean_author_name(name)
    return normalize_text(name)


def parse_authors(text: str) -> list[str]:
    """Parse author text into a list of individual names.

    Handles formats:
    - "A and B"
    - "A, B, and C"
    - Semicolon-separated
    - BibTeX "Surname, Given" (single comma inside a name)
    - "et al." (dropped)
    - Initials like "J. Smith"
    """
    if not text or not text.strip():
        return []

    # Remove "et al." marker
    text = _ET_AL.sub("", text).strip().rstrip(",").strip()
    if not text:
        return []

    # Split on semicolons first (unambiguous separator)
    if ";" in text:
        parts = [p.strip() for p in text.split(";") if p.strip()]
        return [clean_author_name(p) for p in parts if p]

    # Replace " and " with comma for uniform splitting
    text = _SPLIT_AND.sub(",", text)

    # Split on commas
    parts = [p.strip() for p in text.split(",") if p.strip()]

    # Detect BibTeX "Surname, Given" format:
    # If we have exactly 2 parts and neither looks like a full name
    # with spaces, treat as single name in "Surname, Given" format.
    if len(parts) == 2 and not any(" " in p for p in parts):
        return [clean_author_name(f"{parts[1]} {parts[0]}")]

    # For longer lists, try to detect BibTeX format by checking
    # if odd-indexed parts look like given names (short, possibly initials)
    if len(parts) >= 4 and len(parts) % 2 == 0:
        is_bibtex = all(
            len(parts[i].split()) <= 2 and not " " in parts[i - 1]
            for i in range(1, len(parts), 2)
        )
        if is_bibtex:
            names = []
            for i in range(0, len(parts), 2):
                surname = parts[i]
                given = parts[i + 1] if i + 1 < len(parts) else ""
                names.append(clean_author_name(f"{given} {surname}".strip()))
            return names

    # Default: each comma-separated part is one author
    return [clean_author_name(p) for p in parts if p]


def _extract_surname(name: str) -> str:
    """Extract likely surname from a name string."""
    parts = name.strip().split()
    if not parts:
        return ""
    # If comma-separated, surname is first part
    if "," in name:
        return parts[0].rstrip(",").lower()
    # Otherwise surname is last non-initial part
    for p in reversed(parts):
        if not _INITIAL.match(p):
            return p.lower()
    return parts[-1].lower()


def _extract_initials(name: str) -> list[str]:
    """Extract initial letters from given names."""
    parts = name.strip().split()
    if "," in name:
        # "Surname, G. N." format
        idx = name.index(",")
        given_parts = name[idx + 1:].strip().split()
    else:
        given_parts = parts[:-1]  # everything except surname

    return [p[0].upper() for p in given_parts if p and p[0].isalpha()]


def is_name_match(name1: str, name2: str) -> bool:
    """Check if two author names refer to the same person.

    Handles initials, surname-first vs given-first, and
    case-insensitive matching.
    """
    n1 = normalize_author_name(name1)
    n2 = normalize_author_name(name2)

    if not n1 or not n2:
        return False

    # Exact match after normalization
    if n1 == n2:
        return True

    # Compare surnames
    s1 = _extract_surname(name1)
    s2 = _extract_surname(name2)
    s1_norm = normalize_text(s1)
    s2_norm = normalize_text(s2)

    if s1_norm != s2_norm:
        return False

    # Surnames match - check initials compatibility
    init1 = _extract_initials(name1)
    init2 = _extract_initials(name2)

    if not init1 or not init2:
        return True  # surname match with no initials to contradict

    # Check that available initials are compatible
    min_len = min(len(init1), len(init2))
    return all(init1[i] == init2[i] for i in range(min_len))


def compare_authors(
    cited: list[str], correct: list[str]
) -> tuple[bool, str]:
    """Compare cited author list against correct author list.

    Returns (match, error_message). Matching rules:
    - If either list has "et al.", only compare available names
    - First author must match
    - At least 50% of remaining authors should match
    """
    if not cited and not correct:
        return True, ""
    if not cited:
        return False, "No cited authors"
    if not correct:
        return False, "No correct authors to compare against"

    # Check first author
    if not is_name_match(cited[0], correct[0]):
        return False, (
            f"First author mismatch: '{cited[0]}' vs '{correct[0]}'"
        )

    # For single-author works or "et al." with only first author
    if len(cited) <= 1 or len(correct) <= 1:
        return True, ""

    # Check remaining authors
    cited_rest = cited[1:]
    correct_rest = correct[1:]
    matched = 0

    for c_author in cited_rest:
        if any(is_name_match(c_author, r_author) for r_author in correct_rest):
            matched += 1

    min_to_check = min(len(cited_rest), len(correct_rest))
    if min_to_check == 0:
        return True, ""

    match_ratio = matched / min_to_check
    if match_ratio < 0.5:
        return False, (
            f"Author list mismatch: only {matched}/{min_to_check} "
            f"co-authors matched"
        )

    return True, ""
