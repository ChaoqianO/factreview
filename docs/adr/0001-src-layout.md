# ADR-0001: src-layout single package

**Status:** Accepted — 2026-04-19

## Context

Before the 2026-04 restructure, the repo had two top-level folders
(`code_evaluation/`, `fact_extraction/`) with no shared package root. Scripts
only worked after `cd code_evaluation && python main.py …`, tests depended on
implicit `sys.path`, and imports between the two halves were impossible.

## Decision

Collapse everything under a single importable package at
`src/factreview/`, using the standard **src-layout**.

## Consequences

- `pip install -e .` becomes the only setup step; scripts run from anywhere.
- Accidental imports from the working tree during tests become impossible —
  the tests always load the installed package.
- Stage modules (`ingestion/`, `fact_extraction/`, `positioning/`,
  `execution/`, `synthesis/`) live side-by-side and can import each other via
  `from factreview.X import Y`.
- CI configs and editors both pick up `src/` via `pyproject.toml` /
  `tool.ruff.src` / `tool.mypy.mypy_path`.
