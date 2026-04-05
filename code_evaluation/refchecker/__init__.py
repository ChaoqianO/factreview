"""
RefChecker - Academic Paper Reference Validation Tool

A comprehensive tool for validating reference accuracy in academic papers.
Integrated as an internal capability of code_evaluation.
"""

__version__ = "1.2.1"
__author__ = "RefChecker Team"
__email__ = "markrussinovich@hotmail.com"


def __getattr__(name):
    if name == "ArxivReferenceChecker":
        from .core.refchecker import ArxivReferenceChecker
        return ArxivReferenceChecker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ArxivReferenceChecker"]