"""Structured runtime configuration models.

The main application is configured through `.env` and CLI flags. These
models remain available for callers that want to validate structured
configuration dictionaries against the canonical pipeline shape.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StageToggles(BaseModel):
    parse: bool = True
    claim_extract: bool = True
    refcheck: bool = False
    positioning: bool = True
    execution: bool = False
    report: bool = True
    teaser: bool = True


class ParseCfg(BaseModel):
    backend: str = "mineru"
    fallback_chain: list[str] = Field(default_factory=lambda: ["grobid", "nougat"])
    timeout_sec: int = 1800


class ClaimExtractCfg(BaseModel):
    mode: str = "auto"  # auto | llm | heuristic
    decompose_broad_claims: bool = True


class PositioningCfg(BaseModel):
    enable_bibtex: bool = False
    max_neighbors: int = 12


class RefcheckCfg(BaseModel):
    enabled: bool = False
    max_report_issues: int = 20


class ExecutionCfg(BaseModel):
    docker_enabled: bool = True
    auto_tasks: bool = False
    auto_tasks_mode: str = "smoke"
    python_spec: str = ""


class ReviewCfg(BaseModel):
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
    parse: ParseCfg = Field(default_factory=ParseCfg)
    claim_extract: ClaimExtractCfg = Field(default_factory=ClaimExtractCfg)
    refcheck: RefcheckCfg = Field(default_factory=RefcheckCfg)
    positioning: PositioningCfg = Field(default_factory=PositioningCfg)
    execution: ExecutionCfg = Field(default_factory=ExecutionCfg)
    review: ReviewCfg = Field(default_factory=ReviewCfg)
    llm: LLMCfg = Field(default_factory=LLMCfg)
    logging: LoggingCfg = Field(default_factory=LoggingCfg)
