# FactReview

Automated reproduction evidence pipeline for academic papers. Given a paper PDF, it extracts the associated code repository, executes it inside Docker, and produces reviewer-ready reports with deterministic verification against the paper's claimed metrics.

## Overview

FactReview runs a **6-node self-feedback loop** (LangGraph StateGraph):

```
prepare → plan → run → judge → fix → finalize
```

| Node | What it does |
|------|-------------|
| **prepare** | Extracts PDF structure (MinerU), locates/clones the code repo, builds a Docker image |
| **plan** | Infers tasks from README/entrypoints (LLM or heuristic), loads baseline checks |
| **run** | Executes tasks inside Docker, collects metric artifacts |
| **judge** | Runs deterministic checks, paper-table alignment, optional LLM judge, optional reference checking |
| **fix** | Attempts automated recovery (missing deps, path errors) |
| **finalize** | Generates reproduction report, evidence table, and `facts.json` |

**Exit codes**: `0` = verified, `1` = failed, `2` = inconclusive

### Optional integrated capabilities

Both are off by default and activated via CLI flags:

| Flag | What it adds |
|------|-------------|
| `--enable-refcheck` | Reference-accuracy checking as a 4th judge evidence source |
| `--enable-bibtex` | Enriches `facts.json` with BibTeX entries via Semantic Scholar |

## Repository Structure

```
factreview/
├── README.md
├── code_evaluation/           # Reproduction evidence pipeline (main module)
│   ├── main.py                # CLI entry point
│   ├── requirements.txt
│   ├── env_example.txt
│   ├── src/
│   │   ├── workflow.py        # LangGraph orchestrator
│   │   ├── nodes/             # prepare, plan, run, judge, fix, finalize
│   │   └── tools/             # docker, metrics, alignment, bibtex, refcheck, …
│   ├── refchecker/            # Integrated reference-accuracy checker
│   ├── scripts/               # Developer utilities (debug_nodes, node_stepper, …)
│   ├── tests/                 # Test suite
│   ├── baseline/              # Per-paper baseline configs
│   ├── papers/                # Input PDFs (git-ignored)
│   ├── run/                   # Runtime output (git-ignored)
│   ├── compare/               # Cross-run comparison reports
│   └── review/                # Facts packs for downstream review
└── fact_extraction/           # PDF-to-text conversion toolkit
    ├── convert.py
    └── converters/            # Grobid, Nougat, Science-Parse, LlamaIndex backends
```

## Quick Start

```bash
cd code_evaluation
pip install -r requirements.txt          # core deps
# pip install -r requirements_pdf.txt   # optional: MinerU for PDF extraction

python main.py papers/<paper_key>/paper.pdf
```

With optional integrations:

```bash
python main.py papers/compgcn/paper.pdf \
    --enable-refcheck \
    --enable-bibtex
```

Full flag reference:

```
python main.py --help
```

## LLM Authentication

Copy `code_evaluation/env_example.txt` to `.env` (or set env vars directly).

Supported providers (set `MODEL_PROVIDER`):

| Provider | Key env var |
|----------|------------|
| `openai` (default) | `OPENAI_API_KEY` |
| `openai-codex` | Codex subscription (browser login fallback) |
| `deepseek` | `DEEPSEEK_API_KEY` |
| `qwen` | `QWEN_API_KEY` |
| `claude` | `CLAUDE_API_KEY` |

If `MODEL_PROVIDER=openai` and `OPENAI_API_KEY` is empty, the workflow automatically falls back to the OpenAI Codex subscription backend.

## PDF Extraction (MinerU)

By default the pipeline requires MinerU (`magic-pdf`) to extract structured markdown from the PDF:

```bash
pip install -r code_evaluation/requirements_pdf.txt
```

To skip extraction (use raw PDF text only):

```bash
python main.py --no-pdf-extract papers/<paper_key>/paper.pdf
```

## Auto Task Inference

Let the framework infer how to run the code from the repo README/entrypoints:

```bash
python main.py --auto-tasks --auto-tasks-mode smoke papers/<paper_key>/paper.pdf
```

- `smoke` — safe, fast checks (e.g., `python run.py --help`)
- `full` — heavier tasks; generated with `enabled: false` for manual review

## Reference Checking (`--enable-refcheck`)

Invokes the integrated `refchecker/` package to verify that references cited in the paper are accurate. Results appear as a 4th evidence source in `judge` and are summarised in `facts.json`.

Requires the extra dependencies listed in `requirements.txt` under `# Reference checker`.

## BibTeX Enrichment (`--enable-bibtex`)

After `finalize`, looks up BibTeX entries for the paper's claims via the Semantic Scholar API and appends them to `facts.json["bibtex"]`.

## Testing

```bash
cd code_evaluation
python -m pytest tests/ -v
```

## fact_extraction

Standalone PDF-to-text toolkit used upstream to convert papers before they enter the pipeline:

```bash
cd fact_extraction
python convert.py -i input_pdfs -c grobid   # or nougat / science-parse / llamaindex
```
