# FactReview — Architecture

This page maps the paper's §3 pipeline onto concrete Python modules. Every
stage consumes and produces **typed Pydantic models** (the contracts live in
[`src/factreview/schemas/`](../src/factreview/schemas)).

## Pipeline

```mermaid
flowchart LR
  A[paper.pdf + repo link] --> I[1. ingestion]
  I -->|Paper| F[2. fact_extraction]
  F -->|Claim[]| P[3. positioning]
  P -->|LiteratureContext| E[4. execution]
  E -->|ExecutionEvidence[]| S[5. synthesis]
  S --> R[review.md + evidence.md]
```

## Stages

| # | Module | Paper section | Input | Output |
|---|--------|--------------|-------|--------|
| 1 | `factreview.ingestion` | §3.1a | `pdf_path: Path` | `schemas.paper.Paper` |
| 2 | `factreview.fact_extraction` | §3.1b | `Paper` | `list[schemas.claim.Claim]` |
| 3 | `factreview.positioning` | §3.2 | `Paper`, `list[Claim]` | `schemas.positioning.LiteratureContext` |
| 4 | `factreview.execution` | §3.3 | `Paper`, `list[Claim]`, repo | `list[schemas.execution.ExecutionEvidence]` |
| 5 | `factreview.synthesis` | §3.4 | everything above | `schemas.review.FinalReview` |

The top-level orchestrator in [`orchestrator.py`](../src/factreview/orchestrator.py)
wires these five stages as a single LangGraph. Stage 4 is itself a sub-graph
(`prepare → plan → run → judge → fix → collect`) because each of those steps
needs its own retry / resume semantics.

## Non-negotiables

1. **No paper-specific constants in code.** CompGCN is the first fixture, not
   a special case. Anything paper-specific lives in
   [`configs/baselines/<paper_key>/`](../configs/baselines).
2. **Schemas are the contract.** Stages only talk through `schemas.*`
   Pydantic models, never bare `dict`. This keeps each stage independently
   testable and replaceable.
3. **One package, one CLI.** `factreview run …` is the only supported entry
   point. No `cd` dances.

See `docs/adr/` for the decisions behind these rules and `docs/stages/` for
each stage's responsibilities in detail.
