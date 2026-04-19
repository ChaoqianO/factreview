"""Stage §3.1b: extract review-relevant :class:`Claim` objects from an ingested paper.

Turns the structured :class:`factreview.schemas.paper.Paper` produced by the
ingestion stage into a list of :class:`factreview.schemas.claim.Claim` objects
— optionally decomposed into :class:`SubClaim` entries for broad claims.
"""
