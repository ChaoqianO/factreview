"""
Core functionality for RefChecker
"""


def __getattr__(name):
    if name == "ArxivReferenceChecker":
        from .refchecker import ArxivReferenceChecker
        return ArxivReferenceChecker
    if name == "setup_logging":
        from .refchecker import setup_logging
        return setup_logging
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ArxivReferenceChecker", "setup_logging"]