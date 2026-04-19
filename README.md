# FactReview

Evidence-grounded AI reviewing system. Given a paper PDF (and optionally the
paper's code repository), FactReview ingests the paper, decomposes it into
checkable claims, positions them against the literature, executes the code
inside Docker, and produces a reviewer-ready report whose verdicts are
grounded in deterministic verification.

## Pipeline

```
ingestion → fact_extraction → positioning → execution → synthesis
```

The execution stage is a **6-node LangGraph self-feedback loop**:

```
prepare → plan → run → judge → fix → finalize
```

| Node | Responsibility |
|------|----------------|
| **prepare** | Extract PDF structure (MinerU), locate/clone the code repo, build a Docker image |
| **plan** | Infer runnable tasks from README / entrypoints (LLM or heuristic) and load baseline checks |
| **run** | Execute tasks inside Docker and collect metric artifacts |
| **judge** | Deterministic checks + paper-table alignment + optional LLM judge + optional reference checking |
| **fix** | Automated recovery loop (missing deps, path errors, …) |
| **finalize** | Emit reproduction report, evidence table, and `facts.json` |

The CLI returns three exit codes: `0` verified, `1` failed, `2` inconclusive.

## Repository layout

```
factreview/
├── pyproject.toml              # package metadata, deps, script entry
├── README.md
├── .env.example                # LLM provider credentials template
├── configs/
│   ├── default.yaml            # default RunConfig
│   └── baselines/              # per-paper baseline configs
├── src/                        # flat src layout, top-level packages
│   ├── cli.py                  # `factreview` CLI entry (re-exports main)
│   ├── cli_legacy.py           # argparse + orchestrator wiring
│   ├── ingestion/              # PDF → structured representation
│   ├── fact_extraction/        # claim decomposition + heuristics
│   ├── positioning/            # literature positioning (bibtex, refcheck, …)
│   ├── execution/              # LangGraph pipeline (nodes/, tools/, graph.py)
│   ├── synthesis/              # final review synthesis
│   ├── schemas/                # cross-stage Pydantic contracts
│   ├── llm/                    # LLM client + provider resolution
│   └── util/                   # fs / runner / recorder helpers
├── tools/                      # vendored third-party checkers
│   ├── refchecker/
│   └── s2_title_to_bibtex/
├── tests/
│   └── unit/
└── scripts/                    # developer utilities
```

## Install

Requires Python `>=3.11`.

```bash
pip install -e ".[dev,llm,positioning,execution]"
```

Extras:

| Extra | Use it when you need |
|-------|----------------------|
| `llm` | OpenAI / Anthropic clients |
| `positioning` | BibTeX lookup + reference checking |
| `execution` | Docker-based task execution |
| `ingestion-mineru` | MinerU PDF layout extraction |
| `ingestion-grobid` / `ingestion-nougat` / `ingestion-llama` | alternative PDF backends |
| `dev` | test + lint toolchain |
| `all` | everything above |

## Quick start

```bash
factreview path/to/paper.pdf
```

With optional integrations:

```bash
factreview path/to/paper.pdf \
    --enable-refcheck \
    --enable-bibtex
```

Full flag reference:

```bash
factreview --help
```

Commonly used flags:

| Flag | Purpose |
|------|---------|
| `--paper-pdf PATH` | paper PDF (also accepted as positional) |
| `--paper-key NAME` | folder name under `papers/` (auto-derived if omitted) |
| `--tasks PATH` | tasks YAML/JSON for execution |
| `--baseline PATH` | baseline JSON for deterministic comparison |
| `--auto-tasks [--auto-tasks-mode smoke\|full]` | infer tasks from README/entrypoints |
| `--no-pdf-extract` | skip MinerU; use raw PDF text only |
| `--max-attempts N` | cap the fix loop (default `5`) |
| `--no-llm` | deterministic-only (no LLM calls) |
| `--llm-provider / --llm-model / --llm-base-url` | override LLM routing |
| `--dry-run` | plan only; do not execute |
| `--enable-refcheck` | add reference-accuracy checking as a 4th judge source |
| `--enable-bibtex` | enrich `facts.json` with Semantic-Scholar BibTeX |
| `--quiet` / `--verbose` | toggle step-by-step console tracing |

## LLM credentials

Copy `.env.example` to `.env` and fill what you need. Supported providers
(set `MODEL_PROVIDER`):

| Provider | Key env var |
|----------|-------------|
| `openai` (default) | `OPENAI_API_KEY` |
| `openai-codex` | ChatGPT subscription (browser / cached login) |
| `deepseek` | `DEEPSEEK_API_KEY` |
| `qwen` | `QWEN_API_KEY` |
| `claude` | `CLAUDE_API_KEY` |

If `MODEL_PROVIDER=openai` and `OPENAI_API_KEY` is empty, the workflow falls
back to the OpenAI Codex subscription backend automatically.

## Optional capabilities

### Reference checking — `--enable-refcheck`

Invokes the vendored `tools/refchecker/` package to verify that citations in
the paper resolve to the correct works. Results appear as a 4th evidence
source in `judge` and are summarised in `facts.json`.

### BibTeX enrichment — `--enable-bibtex`

After `finalize`, looks up BibTeX entries for the paper's claims via
Semantic Scholar and appends them to `facts.json["bibtex"]`. Backed by
`tools/s2_title_to_bibtex/`.

### Auto task inference — `--auto-tasks`

Let the pipeline synthesise a `tasks.yaml` from the cloned repo:

```bash
factreview --auto-tasks --auto-tasks-mode smoke path/to/paper.pdf
```

- `smoke` — safe, fast checks (e.g. `python run.py --help`)
- `full`  — heavier tasks, emitted with `enabled: false` for manual review

## Development

```bash
pip install -e ".[dev]"

ruff check .
ruff format --check .
mypy src/schemas src/util        # incremental, warn-only in CI
pytest tests/unit -m "not slow and not e2e and not requires_docker and not requires_llm and not requires_mineru"
```

## License

Apache-2.0.
