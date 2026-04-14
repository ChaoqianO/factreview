"""Centralised configuration for the refchecker package."""

from __future__ import annotations
import copy
import os
from typing import Any, Dict

_DEFAULT: Dict[str, Any] = {
    "semantic_scholar": {
        "base_url": "https://api.semanticscholar.org/graph/v1",
        "rate_limit_delay": 1.0,
        "max_retries": 5,
        "timeout": 30,
    },
    "arxiv": {
        "base_url": "https://export.arxiv.org/api/query",
        "rate_limit_delay": 3.0,
        "max_retries": 5,
        "timeout": 30,
    },
    "arxiv_citation": {
        "base_url": "https://arxiv.org",
        "use_as_authoritative": True,
        "enabled": True,
    },
    "processing": {
        "max_papers": 100,
        "days_back": 7,
        "batch_size": 10,
    },
    "output": {
        "debug_dir": "debug_output",
        "logs_dir": "logs",
        "output_dir": "output",
    },
    "database": {
        "default_path": "semantic_scholar_db/semantic_scholar.db",
        "download_batch_size": 1000,
    },
    "text_processing": {
        "similarity_threshold": 0.85,
        "year_tolerance": 1,
    },
    "llm": {
        "enabled": False,
        "provider": None,
        "fallback_enabled": False,
        "parallel_chunks": False,
        "max_chunk_workers": 3,
        "openai":    {"model": "gpt-4.1",                     "api_key": None},
        "anthropic": {"model": "claude-sonnet-4-20250514",     "api_key": None},
        "google":    {"model": "gemini-2.5-flash",             "api_key": None},
        "azure":     {"model": "gpt-4",  "api_key": None, "endpoint": None, "api_version": "2024-02-15-preview"},
        "vllm":      {"model": None, "server_url": "http://localhost:8000/v1", "auto_download": False},
    },
}

# Environment-variable overrides  (envvar -> config path)
_ENV_MAP = {
    "SEMANTIC_SCHOLAR_API_KEY":  ("semantic_scholar", "api_key"),
    "OPENAI_API_KEY":            ("llm", "openai", "api_key"),
    "ANTHROPIC_API_KEY":         ("llm", "anthropic", "api_key"),
    "GOOGLE_API_KEY":            ("llm", "google", "api_key"),
    "AZURE_OPENAI_API_KEY":      ("llm", "azure", "api_key"),
    "REFCHECKER_LLM_PROVIDER":   ("llm", "provider"),
    "REFCHECKER_LLM_MODEL":      ("llm", "model"),
    "REFCHECKER_LLM_ENABLED":    ("llm", "enabled"),
}


def get_config() -> Dict[str, Any]:
    """Return a fresh config dict with environment-variable overrides applied."""
    cfg = copy.deepcopy(_DEFAULT)
    for envvar, path in _ENV_MAP.items():
        val = os.getenv(envvar)
        if val is None:
            continue
        # Walk the path and set the value
        node = cfg
        for key in path[:-1]:
            node = node.setdefault(key, {})
        # Coerce booleans
        if val.lower() in ("true", "1", "yes"):
            val = True
        elif val.lower() in ("false", "0", "no"):
            val = False
        node[path[-1]] = val
    return cfg
