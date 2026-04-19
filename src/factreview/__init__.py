"""FactReview — evidence-grounded AI reviewing.

This package implements the pipeline described in the FactReview paper (§3):

    ingestion → fact_extraction → positioning → execution → synthesis

See `docs/architecture.md` for the high-level picture and `docs/stages/` for
per-stage detail. The top-level orchestrator lives in
:mod:`factreview.orchestrator`.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
