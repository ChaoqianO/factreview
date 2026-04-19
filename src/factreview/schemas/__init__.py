"""Cross-stage Pydantic contracts.

Every data structure that crosses a module boundary in
:mod:`factreview` is defined here. Internal per-module types stay local.
"""

from __future__ import annotations

from factreview.schemas.claim import Claim, ClaimLabel, ClaimType, SubClaim
from factreview.schemas.config import RunConfig
from factreview.schemas.execution import ExecutionEvidence, RunArtifact, Task
from factreview.schemas.paper import Figure, Paper, PaperMetadata, ReportedResult, Section, Table
from factreview.schemas.positioning import LiteratureContext, NeighborMethod, NoveltyType
from factreview.schemas.review import ClaimAssessment, EvidenceLink, FinalReview

__all__ = [
    "Claim",
    "ClaimAssessment",
    "ClaimLabel",
    "ClaimType",
    "EvidenceLink",
    "ExecutionEvidence",
    "Figure",
    "FinalReview",
    "LiteratureContext",
    "NeighborMethod",
    "NoveltyType",
    "Paper",
    "PaperMetadata",
    "ReportedResult",
    "RunArtifact",
    "RunConfig",
    "Section",
    "SubClaim",
    "Table",
    "Task",
]
