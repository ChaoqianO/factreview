# FactReview

FactReview extracts claims and their conditions, checks them against literature, theory, code and experiments, and produces a review with traceable evidence. Each claim is assessed as `supported`, `flawed`, `questioned` or `unverified`. It assists reviewers and provides no publication decision.

## Pipeline

[![FactReview pipeline](docs/factreview-pipeline.png)](docs/factreview-pipeline.pdf)

Screening includes writing, figure, table and reference checks. Claims retain their source locations and conditions; a coverage review checks for omitted or merged claims. Verification follows the evidence needs of each claim. Missing evidence and failed checks remain visible in the report.

## Quick start

Requirements: Python 3.11+, a configured language model with image support, and a MinerU API token. Docker is required only for optional execution.

From the downloaded repository directory:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[runtime,refcheck,positioning]"
cp .env.example .env              # Windows PowerShell: Copy-Item .env.example .env
```

Edit `.env` and set `MINERU_API_TOKEN`. The supplied model configuration uses a local Codex login; run `codex login` before using it. To use an OpenAI-compatible endpoint, set `MODEL_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL` and, when needed, `OPENAI_BASE_URL`. The selected model must accept images for visual checks. Optional `VLM_*` settings in `.env.example` select a separate visual model.

## Run

Review a paper:

```bash
python scripts/execute_review_pipeline.py path/to/paper.pdf \
  --paper-key my_paper --submission-deadline YYYY-MM-DD
```

Replace `YYYY-MM-DD` with the venue's actual submission deadline. Literature treats the preceding three calendar months as concurrent work; a missing deadline leaves its assessment unresolved. A PDF URL or arXiv abstract URL can also be used as input.

| Option | Purpose |
|---|---|
| `--repository-root path/to/repo` | Bind a local copy of the paper's released implementation. |
| `--repository-url URL` | Bind the paper's released repository by URL. |
| `--run-execution` | Enable Docker execution; off by default. |
| `--approval-mode interactive` | Review execution plans before running them; default is `auto`. |
| `--training-budget N` | Limit training runs, including retries; default is `0`. |
| `--report-presentation layered` | Produce a reading report, technical appendix and combined PDF. |

Reference checking uses the bundled RefCopilot library. Literature retrieval uses arXiv by default; further provider settings are documented in `.env.example`. Use `--help` for all options.

## Outputs

Each run is saved under `runs/<paper-key>_<timestamp>_<unique-id>/`:

- `review/report/final_review.{json,md,pdf}`: claim assessments, evidence and reviewer advice.
- `review/teaser/teaser.{json,svg}`: local four-status summary.
- `materials/`, `screening/`, `verification/`, `execution/`: source records and stage audits.
- `full_pipeline_summary.json`, `run_stats.json`, `cutoff.json`: completion, usage and literature cutoff records.

See [demos](demos/README.md) for example papers.

## Tests

```bash
pip install -e ".[runtime,refcheck,positioning,dev]"
python -m pytest
```

The default suite excludes tests marked as slow or requiring live LLM, MinerU or Docker services.

## License

[AGPL-3.0](LICENSE).
