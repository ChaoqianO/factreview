"""Minimal tests for src.tools.refcheck (reference-checking adapter)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_refcheck_adapter_importable():
    """The adapter module must be importable without heavy refchecker deps."""
    from src.tools.refcheck import check_references
    assert callable(check_references)


def test_refcheck_nonexistent_paper():
    """Passing a non-existent file should return ok=False gracefully."""
    try:
        import arxiv  # noqa: F401
    except ImportError:
        pytest.skip("refchecker deps (arxiv) not installed")

    from src.tools.refcheck import check_references
    result = check_references(paper="/nonexistent/paper.pdf")
    # The adapter calls refchecker which will fail; should not raise.
    assert isinstance(result, dict)
    assert "ok" in result
    assert "error_message" in result


def test_refchecker_package_importable():
    """The refchecker package should be importable (lazy init, no heavy deps needed)."""
    import refchecker
    assert hasattr(refchecker, "__version__")
    assert refchecker.__version__
