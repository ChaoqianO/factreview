"""RefCopilot — reference-accuracy checker for academic papers.

Parts of the implementation and design were informed by Mark Russinovich's
refchecker (https://github.com/markrussinovich/refchecker).
"""

from refcopilot.models import (
    CheckedReference,
    ExternalRecord,
    HallucinationVerdict,
    Issue,
    IssueCategory,
    MergedRecord,
    Reference,
    Report,
    Severity,
    Verdict,
)
from refcopilot.pipeline import RefCopilotPipeline

__all__ = [
    "CheckedReference",
    "ExternalRecord",
    "HallucinationVerdict",
    "Issue",
    "IssueCategory",
    "MergedRecord",
    "Reference",
    "RefCopilotPipeline",
    "Report",
    "Severity",
    "Verdict",
]

__version__ = "0.1.0"
