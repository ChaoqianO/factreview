# FactReview

Evidence-grounded AI reviewing for empirical ML papers. Given a paper PDF
(and optionally its released repository), FactReview extracts the major
claims, positions the paper against nearby literature, executes the
repository under bounded budgets to test the central empirical claims, and
writes a concise review linked to an evidence report.

Every judgment is tagged with one of five labels: **Supported**,
**Supported by the paper**, **Partially supported**, **In conflict**, or
**Inconclusive**.

## Paper

Read the paper on [arXiv](https://arxiv.org/abs/2604.04074) or from the
local PDF at
[`factreview-arxiv-2604.04074v2.pdf`](factreview-arxiv-2604.04074v2.pdf).

If you use FactReview, please cite:

```bibtex
@misc{xu2026factreview,
  title = {FactReview: Evidence-Grounded Reviews with Literature Positioning and Execution-Based Claim Verification},
  author = {Xu, Hang and Yue, Ling and Ouyang, Chaoqian and Liu, Yuchen and Zheng, Libin and Pan, Shaowu and Di, Shimin and Zhang, Min-Ling},
  year = {2026},
  eprint = {2604.04074},
  archivePrefix = {arXiv},
  primaryClass = {cs.AI},
  doi = {10.48550/arXiv.2604.04074},
  url = {https://arxiv.org/abs/2604.04074}
}
```

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

Then edit `.env` and configure one LLM authentication path:

**Option A — OpenAI-compatible API key**

```bash
MODEL_PROVIDER=openai
OPENAI_API_KEY=...
# optional, for compatible gateways:
# BASE_URL=https://...
```

**Option B — ChatGPT/Codex subscription, no OpenAI Platform API key**

If you have a ChatGPT/Codex subscription, FactReview can reuse the Codex CLI
OAuth cache in the same style as
[Foam-Agent](https://github.com/csml-rpi/Foam-Agent#codex-oauth-sign-in-no-api-key):

```bash
# One-time setup on the host:
codex login
# choose "Sign in with ChatGPT", then verify:
ls ~/.codex/auth.json

# .env
MODEL_PROVIDER=openai-codex
OPENAI_CODEX_MODEL=gpt-5.3-codex
OPENAI_CODEX_BASE_URL=https://chatgpt.com/backend-api/codex

# Leave this empty to let execution-stage LLM calls inherit MODEL_PROVIDER:
CODE_EVAL_MODEL_PROVIDER=
```

FactReview searches for Codex OAuth tokens at `$CODEX_HOME/auth.json`,
`~/.codex/auth.json`, `~/.clawdbot/agents/main/agent/auth-profiles.json`,
and compatible OpenClaw agent auth caches. Treat `auth.json` like a password.

Other keys:
- `MINERU_API_TOKEN` for the default PDF parsing backend.
- optional `GEMINI_API_KEY` for teaser-figure image generation.

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
- `--llm-provider / --llm-model / --llm-base-url` — override LLM routing; use
  `--llm-provider openai-codex --llm-model gpt-5.3-codex` to force the Codex
  subscription backend for execution-stage helpers.

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
