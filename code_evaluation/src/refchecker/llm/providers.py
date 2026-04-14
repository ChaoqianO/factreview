"""Concrete LLM provider implementations.

Each provider lazily imports its SDK so the package works even when
only a subset of backends is installed.
"""

from __future__ import annotations

import logging
from typing import Any

from ..extraction.llm_extractor import LLMProvider

log = logging.getLogger(__name__)

_PROVIDERS: dict[str, type[LLMProvider]] = {}


def create_provider(name: str, config: dict[str, Any]) -> LLMProvider | None:
    """Instantiate the provider identified by *name*, or return ``None``."""
    cls = _PROVIDERS.get(name.lower())
    if cls is None:
        log.error("Unknown LLM provider: %s", name)
        return None
    provider = cls(config)
    if not provider.is_available():
        log.warning("Provider '%s' is not available (missing package or key)", name)
        return None
    return provider


def _register(name: str):
    """Class decorator that registers a provider under *name*."""
    def wrapper(cls: type[LLMProvider]):
        _PROVIDERS[name] = cls
        return cls
    return wrapper


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

@_register("openai")
class OpenAIProvider(LLMProvider):
    """OpenAI ChatCompletion provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.model = config.get("model", "gpt-4.1")
        self.api_key = config.get("api_key")

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def call(self, prompt: str) -> str:
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

@_register("anthropic")
class AnthropicProvider(LLMProvider):
    """Anthropic Messages provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.model = config.get("model", "claude-sonnet-4-20250514")
        self.api_key = config.get("api_key")

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    def call(self, prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        resp = client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text


# ---------------------------------------------------------------------------
# Google (Generative AI)
# ---------------------------------------------------------------------------

@_register("google")
class GoogleProvider(LLMProvider):
    """Google Generative AI provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.model = config.get("model", "gemini-2.5-flash")
        self.api_key = config.get("api_key")

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            import google.generativeai  # noqa: F401
            return True
        except ImportError:
            return False

    def call(self, prompt: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        resp = model.generate_content(prompt)
        return resp.text


# ---------------------------------------------------------------------------
# Azure OpenAI
# ---------------------------------------------------------------------------

@_register("azure")
class AzureProvider(LLMProvider):
    """Azure OpenAI provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.model = config.get("model", "gpt-4")
        self.api_key = config.get("api_key")
        self.endpoint = config.get("endpoint")
        self.api_version = config.get("api_version", "2024-02-15-preview")

    def is_available(self) -> bool:
        if not self.api_key or not self.endpoint:
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def call(self, prompt: str) -> str:
        import openai
        client = openai.AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
        )
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# vLLM (OpenAI-compatible)
# ---------------------------------------------------------------------------

@_register("vllm")
class vLLMProvider(LLMProvider):
    """vLLM provider using the OpenAI-compatible endpoint."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.model = config.get("model", "")
        self.server_url = config.get("server_url", "http://localhost:8000/v1")
        self.api_key = config.get("api_key", "EMPTY")

    def is_available(self) -> bool:
        if not self.model:
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def call(self, prompt: str) -> str:
        import openai
        client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.server_url,
        )
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return resp.choices[0].message.content or ""
