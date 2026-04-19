# ADR-0005: No paper-specific constants in framework code

**Status:** Accepted — 2026-04-19

## Context

CompGCN is the case study in §4.2 of the paper and the first e2e fixture in
the codebase. It is tempting to embed CompGCN-shaped assumptions (dataset
names like `FB15k-237`, metric names like `MRR`, specific baseline entries
like `PATCHY-SAN 92.6%`) in the framework while "just trying to get it
working."

## Decision

Framework code under `src/factreview/` must **never** hardcode paper-specific
strings, numbers, URLs, or heuristics. All such values live under
`configs/baselines/<paper_key>/` as data files (baseline.json, tasks.yaml,
per-paper prompt overrides, etc.).

When the pipeline needs a paper-specific hint (e.g. "the authors report MRR
on FB15k-237 in Table 4"), the extractor must **derive** that hint from the
ingested `Paper` (section text, table captions) — or the hint must be
promoted to a general mechanism that works for arbitrary papers.

## Enforcement

- A pre-commit check forbids the string `compgcn` (case-insensitive) in
  `src/factreview/**/*.py` (see `scripts/check_no_paper_specific.py` — to
  land in M6).
- Any exception requires an ADR amendment with explicit justification.

## Consequences

- Slight upfront cost: heuristics must be parameterised rather than inlined.
- Long-term benefit: adding a second paper = adding a `configs/baselines/<X>/`
  directory, no code change.
