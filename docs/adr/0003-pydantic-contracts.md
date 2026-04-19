# ADR-0003: Pydantic schemas as inter-stage contracts

**Status:** Accepted — 2026-04-19

## Context

The legacy code passed a free-form `state["config"]` dict between LangGraph
nodes. New fields accreted over time, typos were only caught at runtime, and
tests had to re-create the dict shape by hand.

## Decision

Every inter-stage boundary uses a **Pydantic v2 model** defined under
`factreview.schemas.*`:

- `schemas.paper.Paper` — ingestion output
- `schemas.claim.Claim` — fact_extraction output
- `schemas.positioning.LiteratureContext` — positioning output
- `schemas.execution.ExecutionEvidence` — per-task execution output
- `schemas.review.FinalReview` — synthesis output
- `schemas.config.RunConfig` — parsed runtime config

Dicts are still used for LangGraph internal state, but every field that
crosses a module boundary is typed.

## Consequences

- IDE auto-completion + mypy coverage across the codebase.
- Validation errors surface at the stage boundary, not ten function calls
  later.
- Breaking schema changes require bumping model versions explicitly, which
  forces a thought about serialized artefacts in `runs/`.
- Some runtime cost (<1% in typical paths) — acceptable.
