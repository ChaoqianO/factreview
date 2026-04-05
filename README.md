# Review-Assistant

Automated academic paper review toolkit. Takes a research paper as input and performs multiple forms of structured evaluation: code reproduction, reference verification, and LLM-based reviewing.

## Components

This repository contains three core subsystems and one utility module, each targeting a different aspect of paper review.

### `code_evaluation/` — Paper Reproduction Evidence Pipeline

The central component. Given a paper PDF, it extracts the associated code repository, runs it inside Docker, and produces reviewer-friendly reports with deterministic verification against paper claims.

**Workflow** (LangGraph StateGraph):

```
prepare → plan → run → judge → fix → finalize
```

- **prepare**: Extracts PDF structure (via MinerU), locates or clones the paper's code repo, builds a Docker image
- **plan**: Infers tasks from README/entrypoints (LLM or heuristic), loads baseline checks
- **run**: Executes tasks inside Docker, collects metric artifacts
- **judge**: Runs deterministic baseline checks, paper-table alignment, optional LLM judge, and optional reference checking
- **fix**: Attempts automated recovery for common failures (missing deps, path issues)
- **finalize**: Generates the reproduction report, evidence table, and structured facts pack (`facts.json`)

**Exit codes**: `0` = verified, `1` = failed, `2` = inconclusive

**Integrated capabilities** (optional, off by default):
- `--enable-refcheck` — runs reference accuracy checking as an evidence source
- `--enable-bibtex` — enriches facts.json with BibTeX via Semantic Scholar

```bash
cd code_evaluation
pip install -r requirements.txt
python main.py paper.pdf
```

### `deepreview/` — LLM-Based Paper Reviewing

Uses vLLM with local models (e.g., LLaMA) to generate structured peer reviews. The pipeline:

1. Converts PDF to Markdown via MinerU (`magic-pdf`)
2. Generates review questions about the paper
3. Optionally queries external knowledge (OpenScholar)
4. Produces a structured review with scores and commentary

```bash
cd deepreview
pip install -r requirements.txt
python run_deepreview.py --pdf paper.pdf --model_path /path/to/model
```

### `refchecker/` — Reference Accuracy Checker

Validates that a paper's citations are accurate by cross-referencing against ArXiv, Semantic Scholar, CrossRef, OpenAlex, and OpenReview. Supports ArXiv IDs, URLs, PDFs, LaTeX, and plain text input.

Features:
- Multi-source verification with automatic API fallback
- Parallel reference processing
- Optional LLM-based reference extraction
- Web UI (FastAPI + React)

```bash
cd refchecker
pip install -r requirements.txt
python run_refchecker.py --paper 2401.12345
```

A copy of the core refchecker package is also integrated inside `code_evaluation/refchecker/` and can be invoked as an evidence source in the reproduction pipeline via `--enable-refcheck`.

### `code_evaluation/fact_extraction/` — PDF Conversion Toolkit

Converts academic PDFs to structured text using multiple backends:

- **Grobid** — XML-based scientific document parsing
- **Nougat** — Neural OCR for academic PDFs
- **Science Parse** — Allen AI's PDF parser
- **LlamaIndex** — LLM-augmented document parsing

```bash
cd code_evaluation/fact_extraction
python convert.py -i input_pdfs -c grobid
```

## Repository Structure

```
Review-Assistant/
├── README.md
├── code_evaluation/           # Reproduction evidence pipeline
│   ├── main.py                # CLI entry point
│   ├── src/                   # Core framework
│   │   ├── workflow.py        # LangGraph orchestrator
│   │   ├── nodes/             # prepare, plan, run, judge, fix, finalize
│   │   └── tools/             # docker, metrics, alignment, bibtex, refcheck, ...
│   ├── refchecker/            # Integrated reference checker
│   ├── baseline/              # Per-paper baseline configs
│   ├── tests/                 # Test suite
│   ├── run/                   # Runtime output
│   ├── compare/               # Cross-run comparison reports
│   ├── review/                # Facts packs for final review
│   └── fact_extraction/       # PDF conversion toolkit
├── deepreview/                # LLM-based paper reviewing
│   ├── run_deepreview.py      # CLI entry point
│   └── module/                # Core review logic (vLLM)
├── refchecker/                # Standalone reference checker
│   ├── run_refchecker.py      # CLI entry point
│   ├── src/refchecker/        # Core package
│   ├── backend/               # FastAPI web backend
│   └── web-ui/                # React frontend
└── scripts/                   # Developer utilities
    ├── debug_nodes.py
    ├── node_stepper.py
    └── verify_paper_image.py
```

## How the Components Relate

```
                    Paper PDF
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   code_evaluation  deepreview  refchecker
   (reproduction)   (LLM review) (ref check)
          │                         │
          │    ┌────────────────────┘
          ▼    ▼
   Integrated evidence
   (facts.json + report)
```

- **code_evaluation** is the primary orchestrator. It can optionally invoke refchecker and bibtex lookup as evidence sources within its judge/finalize steps.
- **deepreview** runs independently to produce an LLM-generated review alongside the reproduction evidence.
- **refchecker** exists both as a standalone tool (with its own Web UI) and as an integrated module inside code_evaluation.
- **fact_extraction** is a utility used upstream to convert PDFs into structured text that feeds into the pipeline.

## Development

```bash
# Run code_evaluation tests
cd code_evaluation && python -m pytest tests/ -v

# Run refchecker tests
cd refchecker && python -m pytest tests/ -v
```
