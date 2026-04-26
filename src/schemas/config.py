"""Structured runtime configuration models.

The main application is configured through `.env` and CLI flags. These
models remain available for callers that want to validate structured
configuration dictionaries.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StageToggles(BaseModel):
    ingestion: bool = True
    fact_extraction: bool = True
    reference_check: bool = False
    positioning: bool = True
    execution: bool = False
    synthesis: bool = True


class IngestionCfg(BaseModel):
    backend: str = "mineru"
    fallback_chain: list[str] = Field(default_factory=lambda: ["grobid", "nougat"])
    timeout_sec: int = 1800


class FactExtractionCfg(BaseModel):
    mode: str = "auto"  # auto | llm | heuristic
    decompose_broad_claims: bool = True


class PositioningCfg(BaseModel):
    enable_bibtex: bool = False
    max_neighbors: int = 12


class ReferenceCheckCfg(BaseModel):
    enabled: bool = False
    max_report_issues: int = 20


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
    provider: str = "openai-codex"
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
    reference_check: ReferenceCheckCfg = Field(default_factory=ReferenceCheckCfg)
    positioning: PositioningCfg = Field(default_factory=PositioningCfg)
    execution: ExecutionCfg = Field(default_factory=ExecutionCfg)
    synthesis: SynthesisCfg = Field(default_factory=SynthesisCfg)
    llm: LLMCfg = Field(default_factory=LLMCfg)
    logging: LoggingCfg = Field(default_factory=LoggingCfg)
