from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    base_url: str | None
    api_key: str | None
    temperature: float = 0.1
    max_tokens: int = 1500


def resolve_llm_config(provider: str = "", model: str = "", base_url: str = "") -> LLMConfig:
    prov = (provider or os.getenv("MODEL_PROVIDER", "openai")).lower().strip()
    if prov == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        mdl = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    elif prov == "qwen":
        api_key = os.getenv("QWEN_API_KEY")
        base = base_url or os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        mdl = model or os.getenv("QWEN_MODEL", "qwen-3")
    elif prov == "claude":
        api_key = os.getenv("CLAUDE_API_KEY")
        base = base_url or os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com")
        mdl = model or os.getenv("CLAUDE_MODEL", "claude-4-sonnet")
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        base = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        mdl = model or os.getenv("OPENAI_MODEL", "gpt-5")

    return LLMConfig(provider=prov, model=mdl, base_url=base, api_key=api_key)


def llm_json(
    prompt: str,
    system: str,
    cfg: LLMConfig,
) -> Dict[str, Any]:
    """
    Minimal OpenAI-compatible JSON response helper.
    Works with OpenAI-compatible endpoints (OpenAI/DeepSeek/Qwen compatible-mode).
    Claude supported via anthropic SDK.
    """
    try:
        if cfg.provider == "claude":
            # Keep dependency footprint minimal: import only when used.
            from anthropic import Anthropic

            client = Anthropic(api_key=cfg.api_key)
            resp = client.messages.create(
                model=cfg.model,
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            # anthropic returns list of content blocks
            text = ""
            try:
                if resp.content and len(resp.content) > 0:
                    text = (resp.content[0].text or "").strip()
            except Exception:
                text = str(resp).strip()
        else:
            # OpenAI-compatible endpoints
            from openai import OpenAI

            client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
            resp = client.chat.completions.create(
                model=cfg.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
            )
            text = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        # Never crash the workflow because of LLM provider/model issues.
        return {
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
            "provider": cfg.provider,
            "model": cfg.model,
            "base_url": cfg.base_url,
        }

    # best-effort JSON extraction
    try:
        return json.loads(text)
    except Exception:
        # try find first {...}
        import re

        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {"status": "unknown", "raw": text}


