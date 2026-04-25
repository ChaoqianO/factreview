# FactReview

Evidence-grounded AI reviewing for empirical ML papers. Given a paper PDF,
FactReview extracts the major claims, positions the paper against nearby
literature, and writes a concise review linked to evidence. Repository/code
execution is available, but disabled by default.

## Quick Start

**Requirements:** Python 3.11+ and a local Codex login.
Docker is only needed if you explicitly enable code execution.

```bash
git clone https://github.com/ChaoqianO/factreview.git
cd factreview

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[runtime]"
codex login

cp .env.example .env
```

If `codex` is not on your PATH, install the Codex CLI first, then rerun
`codex login`.

Edit `.env` and fill:

```bash
MODEL_PROVIDER=openai-codex
MINERU_API_TOKEN=your_mineru_token
```

Then run the bundled CompGCN demo:

```bash
python scripts/run_demo_compgcn.py
```

Run your own PDF:

```bash
python scripts/execute_review_pipeline.py path/to/paper.pdf --paper-key my_paper
```

The first useful output to open is:

```text
runs/<paper_key>_<timestamp>/stages/synthesis/final_review.md
```

## Required Configuration

FactReview intentionally keeps routine configuration to two places:

- `.env` / environment variables for secrets and normal runtime choices.
- CLI flags for one-off overrides.

Advanced developer knobs live in `configs/default.yaml`.

### LLM Backend

The default backend is Codex login:

```bash
MODEL_PROVIDER=openai-codex
OPENAI_CODEX_MODEL=gpt-5.3-codex
```

Run `codex login` once and choose the ChatGPT sign-in flow. FactReview reads
the local Codex OAuth cache, so no OpenAI Platform API key is needed for the
default path.

### MinerU PDF Parsing

`MINERU_API_TOKEN` is required. FactReview uses MinerU's cloud API by default
because it is free to start with generous quota and avoids local CUDA/GPU and
MinerU model setup.

```bash
MINERU_API_TOKEN=your_mineru_token
```

You can also pass it once from CLI:

```bash
python scripts/execute_review_pipeline.py paper.pdf --mineru-api-token your_mineru_token
```

### Gemini Teaser Figure

Gemini is optional. If `GEMINI_API_KEY` is empty, FactReview treats teaser
generation as successful prompt-only output: it writes
`teaser_figure_prompt.txt`, copies the prompt to the clipboard when possible,
and tells you to paste it into the Gemini web app. If `GEMINI_API_KEY` is set,
FactReview uses it automatically.

```bash
GEMINI_API_KEY=
```

To force prompt-only output even when a Gemini key is configured:

```bash
TEASER_USE_GEMINI=false
```

## Running

Full default pipeline:

```bash
python scripts/execute_review_pipeline.py path/to/paper.pdf --paper-key paper_name
```

This runs:

```text
ingestion -> fact_extraction -> positioning -> synthesis
```

Code execution is off by default. Enable it only when you want repository/code
evaluation:

```bash
python scripts/execute_review_pipeline.py path/to/paper.pdf --run-execution
```

Useful one-off overrides:

```bash
python scripts/execute_review_pipeline.py paper.pdf \
  --llm-provider openai-codex \
  --llm-model gpt-5.3-codex \
  --teaser-mode prompt
```

`--teaser-mode prompt` forces the prompt-only Gemini fallback even when a key
is configured.

## Outputs

Each run writes to:

```text
runs/<paper_key>_<timestamp>/
```

Primary artifacts:

- `full_pipeline_summary.json`
- `runtime/jobs/<job_id>/` for raw runtime job state, MinerU output, prompts, and agent traces
- `inputs/` for copied PDFs, paper extraction snapshots, and execution baseline snapshots
- `stages/execution/run/workspace/source/` for the run-local paper code checkout when execution is enabled
- `stages/synthesis/final_review.json`
- `stages/synthesis/final_review.md`
- `stages/synthesis/final_review.pdf`
- `stages/synthesis/teaser_figure_prompt.txt`
- `stages/synthesis/teaser_figure.png` when image API generation is enabled

## Pipeline

Judgments use five labels: **Supported**, **Supported by the paper**,
**Partially supported**, **In conflict**, and **Inconclusive**.

The optional execution stage is a bounded workflow:

```text
prepare -> plan -> run -> judge -> fix -> finalize
```

## Development

```bash
pip install -e ".[runtime,dev]"

ruff check .
ruff format --check .
mypy src/schemas src/util
pytest tests/unit -m "not slow and not e2e and not requires_docker and not requires_llm and not requires_mineru"
```

## Paper

Read the paper on [arXiv](https://arxiv.org/abs/2604.04074) or from the local
PDF at [`factreview.pdf`](factreview.pdf).

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

## License

Apache-2.0.
