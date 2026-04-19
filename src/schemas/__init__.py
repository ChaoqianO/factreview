"""Cross-stage Pydantic contracts.

Every data structure that crosses a module boundary in the project
is defined here. Internal per-module types stay local.
"""

from __future__ import annotations

from schemas.claim import Claim, ClaimLabel, ClaimType, SubClaim
from schemas.config import RunConfig
from schemas.execution import ExecutionEvidence, RunArtifact, Task
from schemas.paper import Figure, Paper, PaperMetadata, ReportedResult, Section, Table
from schemas.positioning import LiteratureContext, NeighborMethod, NoveltyType
from schemas.review import ClaimAssessment, EvidenceLink, FinalReview

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
