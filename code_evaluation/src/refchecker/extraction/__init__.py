"""Extraction sub-package: bibliography detection, reference parsing, LLM fallback."""

from .bibliography import find_bibliography
from .parsers import parse_references
from .llm_extractor import LLMExtractor, LLMProvider

__all__ = [
    "find_bibliography",
    "parse_references",
    "LLMExtractor",
    "LLMProvider",
]
