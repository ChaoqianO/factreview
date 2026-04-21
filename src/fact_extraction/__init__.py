"""Stage §3.1b: extract review-relevant :class:`Claim` objects from a paper.

Turns the structured :class:`schemas.paper.Paper` produced by the
ingestion stage into a list of :class:`schemas.claim.Claim`
objects — optionally decomposed into :class:`SubClaim` entries for broad
claims, and paired with :class:`ReportedResult` values extracted from tables.
"""

from fact_extraction.decomposer import decompose_claim, decompose_claims
from fact_extraction.extractor import ExtractionResult, extract_facts
from fact_extraction.heuristics import extract_claims_heuristic
from fact_extraction.results_parser import extract_reported_results

__all__ = [
    "ExtractionResult",
    "decompose_claim",
    "decompose_claims",
    "extract_claims_heuristic",
    "extract_facts",
    "extract_reported_results",
]
