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

Then edit `.env` and fill the keys you need:
- `OPENAI_API_KEY` (or `API_KEY`) + optional `BASE_URL` for OpenAI-compatible endpoints
- `MINERU_API_TOKEN` for PDF parsing
- optional `GEMINI_API_KEY` for teaser-figure image generation

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

### Run the full pipeline (recommended)

Run the merged full pipeline:

```bash
python scripts/execute_review_pipeline.py path/to/paper.pdf
```

This runs:
`ingestion → fact_extraction → positioning → execution → synthesis`

Useful options:
- `--paper-key <name>`: stable run folder name
- `--skip-execution`: skip repository execution stage, still produce final review + teaser assets
- `--max-attempts <N>`: execution-stage repair loop cap

Example:

```bash
python scripts/execute_review_pipeline.py \
  external_papers/1506.01497_faster_rcnn.pdf \
  --paper-key faster_rcnn_1506.01497 \
  --skip-execution
```

### Run each stage manually (advanced)

Use the same `--run-dir` to keep one combined run:

```bash
python scripts/execute_stage_ingestion.py path/to/paper.pdf --run-dir runs/<paper_key>/<run_id>
python scripts/execute_stage_fact_extraction.py --run-dir runs/<paper_key>/<run_id>
python scripts/execute_stage_positioning.py --run-dir runs/<paper_key>/<run_id>
python scripts/execute_stage_execution.py --run-dir runs/<paper_key>/<run_id>
python scripts/execute_stage_synthesis.py --run-dir runs/<paper_key>/<run_id>
```

### Outputs

Each run writes to:
- `runs/<paper_key>/<run_id>/stages/*`
- `runs/<paper_key>/<run_id>/full_pipeline_summary.json`

Primary artifacts:
- `stages/synthesis/final_review.json`
- `stages/synthesis/final_review.md`
- `stages/synthesis/final_review.pdf`
- `stages/synthesis/teaser_figure_prompt.txt`
- `stages/synthesis/teaser_figure.png` (when image API is enabled)

### Teaser figure generation

```bash
python scripts/generate_teaser_figure.py
```

Defaults:
- `assets/teaser_template/teaser_figure.pdf`
- `assets/teaser_template/teaser_figure.pptx`

Behavior:
- If `TEASER_USE_GEMINI=true` and key is configured, synthesis calls image API and outputs `teaser_figure.png`.
- Otherwise it always outputs prompt-only artifacts, so you can generate manually.

### Run multiple papers

```bash
for pdf in external_papers/*.pdf; do
  key="$(basename "$pdf" .pdf)"
  python scripts/execute_review_pipeline.py "$pdf" --paper-key "$key" --skip-execution
done
```

### Optional integrations

```bash
factreview path/to/paper.pdf --enable-refcheck --enable-bibtex
```

Useful CLI flags:
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
