"""Title comparison utilities for reference checking."""

import re

from .text import clean_title, normalize_text


def normalize_paper_title(title: str) -> str:
    """Normalize a paper title for exact matching.

    Lowercases, removes all spaces and punctuation.
    """
    title = clean_title(title)
    title = normalize_text(title)
    return re.sub(r"[\s']+", "", title)


def calculate_title_similarity(title1: str, title2: str) -> float:
    """Calculate word-overlap similarity (0-1) between two titles.

    Uses a Jaccard-like metric on normalized word sets.
    """
    words1 = set(normalize_text(title1).split())
    words2 = set(normalize_text(title2).split())

    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


def compare_titles(
    cited: str, correct: str, threshold: float = 0.85
) -> float:
    """Compare a cited title against the correct title.

    Cleans LaTeX markup before comparison. Returns similarity
    score (0-1). Score >= threshold indicates a match.
    """
    cited_clean = clean_title(cited)
    correct_clean = clean_title(correct)

    # Quick exact match check
    if normalize_paper_title(cited_clean) == normalize_paper_title(correct_clean):
        return 1.0

    return calculate_title_similarity(cited_clean, correct_clean)
