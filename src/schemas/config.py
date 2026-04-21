"""Runtime configuration schema.

Loaded from :file:`configs/default.yaml`, optionally overridden by a user
config file, and finally by CLI flags / environment variables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class StageToggles(BaseModel):
    ingestion: bool = True
    fact_extraction: bool = True
    positioning: bool = True
    execution: bool = True
    synthesis: bool = True


class IngestionCfg(BaseModel):
    backend: str = "mineru"
    fallback_chain: list[str] = Field(default_factory=lambda: ["grobid", "nougat"])
    timeout_sec: int = 1800


class FactExtractionCfg(BaseModel):
    mode: str = "auto"  # auto | llm | heuristic
    decompose_broad_claims: bool = True


class PositioningCfg(BaseModel):
    enable_refcheck: bool = False
    enable_bibtex: bool = False
    max_neighbors: int = 12


class ExecutionCfg(BaseModel):
    docker_enabled: bool = True
    auto_tasks: bool = False
    auto_tasks_mode: str = "smoke"
    python_spec: str = ""


class SynthesisCfg(BaseModel):
    labels: list[str] = Field(
        default_factory=lambda: [
            "supported",
            "supported_by_paper",
            "partially_supported",
            "in_conflict",
            "inconclusive",
        ]
    )


class LLMCfg(BaseModel):
    provider: str = "openai"
    model: str = ""
    base_url: str = ""
    route: dict[str, str] = Field(default_factory=dict)


class LoggingCfg(BaseModel):
    level: str = "INFO"
    verbose_console: bool = True


class RunCfg(BaseModel):
    root: str = "runs"
    report_root: str = "reports"
    max_attempts: int = 5
    dry_run: bool = False


class RunConfig(BaseModel):
    """Top-level runtime configuration."""

    model_config = ConfigDict(extra="ignore")

    run: RunCfg = Field(default_factory=RunCfg)
    stages: StageToggles = Field(default_factory=StageToggles)
    ingestion: IngestionCfg = Field(default_factory=IngestionCfg)
    fact_extraction: FactExtractionCfg = Field(default_factory=FactExtractionCfg)
    positioning: PositioningCfg = Field(default_factory=PositioningCfg)
    execution: ExecutionCfg = Field(default_factory=ExecutionCfg)
    synthesis: SynthesisCfg = Field(default_factory=SynthesisCfg)
    llm: LLMCfg = Field(default_factory=LLMCfg)
    logging: LoggingCfg = Field(default_factory=LoggingCfg)

    # ---- Loaders ------------------------------------------------------------
    @classmethod
    def from_yaml(cls, path: Path | str) -> RunConfig:
        p = Path(path)
        raw: dict[str, Any] = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return cls.model_validate(raw)

    @classmethod
    def layered(cls, *paths: Path | str) -> RunConfig:
        """Later paths override earlier ones. Missing files are skipped."""
        merged: dict[str, Any] = {}
        for p in paths:
            pp = Path(p)
            if not pp.exists():
                continue
            chunk = yaml.safe_load(pp.read_text(encoding="utf-8")) or {}
            merged = _deep_merge(merged, chunk)
        return cls.model_validate(merged)


def _deep_merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out
