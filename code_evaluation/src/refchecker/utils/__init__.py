"""Refchecker utility functions."""

from .text import (
    normalize_text,
    normalize_apostrophes,
    expand_abbreviations,
    strip_latex_commands,
    clean_title,
    clean_title_basic,
    clean_author_name,
)
from .authors import (
    parse_authors,
    is_name_match,
    compare_authors,
    normalize_author_name,
)
from .titles import (
    calculate_title_similarity,
    compare_titles,
    normalize_paper_title,
)
from .doi import (
    extract_doi,
    normalize_doi,
    compare_dois,
    construct_doi_url,
)
from .arxiv import (
    extract_arxiv_id,
    construct_arxiv_url,
    normalize_arxiv_url,
    ArxivRateLimiter,
)
from .urls import (
    deduplicate_urls,
    clean_url,
    get_best_url,
)

__all__ = [
    # text
    "normalize_text",
    "normalize_apostrophes",
    "expand_abbreviations",
    "strip_latex_commands",
    "clean_title",
    "clean_title_basic",
    "clean_author_name",
    # authors
    "parse_authors",
    "is_name_match",
    "compare_authors",
    "normalize_author_name",
    # titles
    "calculate_title_similarity",
    "compare_titles",
    "normalize_paper_title",
    # doi
    "extract_doi",
    "normalize_doi",
    "compare_dois",
    "construct_doi_url",
    # arxiv
    "extract_arxiv_id",
    "construct_arxiv_url",
    "normalize_arxiv_url",
    "ArxivRateLimiter",
    # urls
    "deduplicate_urls",
    "clean_url",
    "get_best_url",
]
