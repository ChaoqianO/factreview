"""
refchecker – Academic paper reference validation.

Validates references in academic papers by extracting bibliographies,
checking metadata against multiple sources (ArXiv, Semantic Scholar,
CrossRef, OpenAlex, etc.), and reporting discrepancies.
"""

__version__ = "3.0.0"

from .checker import ReferenceChecker  # noqa: F401

__all__ = ["ReferenceChecker"]
