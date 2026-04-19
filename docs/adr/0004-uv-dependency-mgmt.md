# ADR-0004: uv for dependency management (with pip fallback)

**Status:** Accepted — 2026-04-19

## Context

The repo previously carried three parallel dependency spec files
(`requirements.txt`, `requirements_pdf.txt`, `environment.yml`). Users ended
up unsure which one was authoritative, and extras were not separable.

## Decision

Single source of truth: `pyproject.toml` with PEP 621 metadata and extras.
Lock resolution via [**uv**](https://github.com/astral-sh/uv) — the de-facto
fast standard from Astral — into `uv.lock`. `pip install -e .` continues to
work for users without uv.

Extras map to stages:

- `factreview[ingestion-mineru|grobid|nougat|scienceparse|llama]`
- `factreview[positioning]`, `factreview[execution]`, `factreview[llm]`
- `factreview[all]` for everything
- `factreview[dev]` for contributors

## Consequences

- Contributors: `uv sync --all-extras` or `pip install -e ".[all,dev]"`.
- `uv.lock` committed to repo → reproducible installs.
- CI uses `pip` (simpler, already cached) but production deploys can prefer
  `uv pip install --system` for speed.
- `requirements*.txt` / `environment.yml` can be regenerated on demand via
  `uv export` when someone actually needs them.
