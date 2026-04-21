# FactReview

Evidence-grounded AI reviewing for empirical ML papers. Given a paper PDF
(and optionally its released repository), FactReview extracts the major
claims, positions the paper against nearby literature, executes the
repository under bounded budgets to test the central empirical claims, and
writes a concise review linked to an evidence report.

Every judgment is tagged with one of five labels: **Supported**,
**Supported by the paper**, **Partially supported**, **In conflict**, or
**Inconclusive**.

## Pipeline

```
ingestion → fact_extraction → positioning → execution → synthesis
```

The `execution/` stage is a LangGraph workflow:
`prepare → plan → run → judge → fix → finalize`.

## Installation

**Requirements:** Python 3.11+, Docker (only for the `execution` stage).

```bash
git clone https://github.com/ChaoqianO/factreview.git
cd factreview

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[all,dev]"
cp .env.example .env
```

Then edit `.env` and set `MODEL_PROVIDER` plus the matching API key
(`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `QWEN_API_KEY`, or `CLAUDE_API_KEY`).
Leave `MODEL_PROVIDER=openai` with an empty `OPENAI_API_KEY` to auto-fall
back to a cached ChatGPT browser login. Pass `--no-llm` at run time to skip
LLM calls entirely.

The default PDF ingestion backend (MinerU) and the vendored reference
checker are installed separately only when needed:

```bash
pip install -e ".[ingestion-mineru]"   # for the default PDF backend
pip install -e tools/refchecker        # for --enable-refcheck
```

## Usage

```bash
factreview path/to/paper.pdf
```

Run the merged full pipeline (ingestion → fact_extraction → positioning → synthesis):

```bash
python scripts/execute_review_pipeline.py path/to/paper.pdf
```

Outputs are written to:
- `runs/<paper_key>/<run_id>/stages/*`
- `runs/<paper_key>/<run_id>/full_pipeline_summary.json`
- `output/latest_extraction.md` and `output/latest_extraction.json`

With optional integrations:

```bash
factreview path/to/paper.pdf --enable-refcheck --enable-bibtex
```

Useful flags:

- `--tasks PATH` — tasks YAML/JSON for execution
- `--baseline PATH` — baseline JSON for deterministic comparison
- `--auto-tasks [--auto-tasks-mode smoke|full]` — infer tasks from README / entrypoints
- `--max-attempts N` — cap the bounded repair loop (default `5`)
- `--no-pdf-extract` — skip MinerU; use raw PDF text only
- `--dry-run` — plan only; do not execute
- `--no-llm` — deterministic only
- `--llm-provider / --llm-model / --llm-base-url` — override LLM routing

Full flag list: `factreview --help`.

Exit codes: `0` verified, `1` failed, `2` inconclusive.

## Project layout

```
factreview/
├── configs/                # default.yaml, per-paper baselines/
├── src/
│   ├── cli.py              # `factreview` CLI entry
│   ├── cli_legacy.py
│   ├── ingestion/          # PDF → structured representation
│   ├── fact_extraction/    # claim decomposition
│   ├── positioning/        # literature positioning
│   ├── execution/          # LangGraph workflow + tools
│   ├── synthesis/          # review + evidence report
│   ├── schemas/            # cross-stage Pydantic contracts
│   ├── llm/                # provider-agnostic LLM client
│   └── util/
├── tools/                  # vendored checkers (refchecker, s2_title_to_bibtex)
├── tests/unit/
└── scripts/
```

## Development

```bash
pip install -e ".[dev]"

ruff check .
ruff format --check .
mypy src/schemas src/util
pytest tests/unit -m "not slow and not e2e and not requires_docker and not requires_llm and not requires_mineru"
```

## License

Apache-2.0.
