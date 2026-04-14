"""Reference checkers – one per data source."""

from .base import BaseChecker, VerifyResult
from .arxiv import ArxivChecker
from .semantic_scholar import SemanticScholarChecker
from .crossref import CrossRefChecker
from .openalex import OpenAlexChecker
from .local_db import LocalDBChecker
from .openreview import OpenReviewChecker
from .github import GitHubChecker
from .webpage import WebPageChecker
from .hybrid import HybridChecker

__all__ = [
    "BaseChecker", "VerifyResult",
    "ArxivChecker", "SemanticScholarChecker", "CrossRefChecker",
    "OpenAlexChecker", "LocalDBChecker", "OpenReviewChecker",
    "GitHubChecker", "WebPageChecker", "HybridChecker",
]
