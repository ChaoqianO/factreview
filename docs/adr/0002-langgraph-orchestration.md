# ADR-0002: LangGraph as orchestration runtime

**Status:** Accepted — 2026-04-19

## Context

The §3.3 execution stage already uses LangGraph (prepare → plan → run → judge →
fix). Extending that same style to the outer pipeline (ingest → extract →
position → execute → synthesize) keeps a single mental model and gives us
checkpointing, resumption, and per-node retry for free.

## Decision

Use LangGraph's `StateGraph` at two levels:

1. **Outer graph** (`factreview.orchestrator`) — one node per paper §3
   section. State is a typed object from `factreview.schemas`.
2. **Inner graph** (`factreview.execution.graph`) — the existing 6-node
   sub-graph for execution verification. Invoked as a compiled sub-workflow
   from the outer node.

## Consequences

- Each stage can be `resume`d from a checkpoint without re-running previous
  stages (e.g. re-run synthesis with a different LLM without re-extracting
  claims).
- The graph definition becomes the **single source of truth** for what the
  pipeline does; prose docs just cross-reference it.
- A future migration off LangGraph is possible because stages are decoupled
  by Pydantic schemas — LangGraph only glues them.
