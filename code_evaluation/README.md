# code_evaluation

This module is a **generic** (paper-agnostic) code evaluation framework:

- It uses **LangGraph** to run a 5-node self-feedback loop:
  - `prepare` → `run` → `judge` → `fix` → `finalize`
- It writes all artifacts/logs into `run/<timestamp>/...`.
- It mirrors a human-readable report into `compare/reports/<timestamp>.md`.

## Where to put the paper inputs

**User input is only the PDF file.**

Recommended: put it under `papers/<paper_key>/paper.pdf`, where `<paper_key>` is the folder name you want to use.

### One-command mode (PDF-driven)

If you already have the paper PDF, you can run:

```bash
python main.py --paper-pdf "papers/<paper_key>/paper.pdf"
```

Or the shorter equivalent:

```bash
python main.py "papers/<paper_key>/paper.pdf"
```

The framework will:
- treat `<paper_key>` as **the PDF's parent folder name**
- extract a GitHub repo URL from the PDF
- clone it into `baseline/<paper_key>/source/`
- (optional, default) if MinerU is installed (`magic-pdf`), extract **structured markdown** from the PDF into `baseline/<paper_key>/paper_extracted/mineru/`
- create minimal `baseline/<paper_key>/tasks.yaml` and `baseline/<paper_key>/baseline.json` if missing
- write run outputs into `run/<paper_key>/<timestamp>/...`
- write compare outputs into `compare/<paper_key>/...`

## How to run (skeleton)

### Framework environment (host Python)

The evaluator itself runs on your machine, and needs a Python environment.

Recommended: create a conda env from `environment.yml`, then run `python main.py ...`.

### Paper-code environment (Docker, default)

All paper-code commands are executed inside a Linux Docker container, so the evaluation is OS-agnostic.
You need Docker installed and working on your machine.

By default the workflow uses a **per-paper image** strategy (same style as `mcp-repo-output`):
- build a Docker image from the cloned paper repo (per paper key)
- install `requirements.txt` during `docker build`
- run tasks inside that paper image with `{paper_root}` mapped to `/app`

Docker strategy:
- `paper_image` (default): per-paper image build (the only supported mode)

Optional env vars for conda channels inside the container:
- `CODE_EVAL_PYTORCH_CHANNELS`: comma-separated, default `pytorch,conda-forge`
- `CODE_EVAL_CONDA_FORGE_CHANNELS`: comma-separated, default `conda-forge`
- `CODE_EVAL_TORCH_SCATTER_CHANNELS`: comma-separated, default `pyg,conda-forge`

If you need a specific Python version for the paper code, the system derives it from `requirements.txt` when possible,
or you can set `CODE_EVAL_PYTHON_SPEC`.

### Console logs (flow tracing)

By default, console output prints **step-by-step workflow logs** (prepare/run/judge/fix/finalize) and each command's cwd/cmd/rc.
Most detailed stdout/stderr are still saved into `run/<paper_key>/<timestamp>/logs/*`.

To disable verbose console logs (keep run/* logs):

```bash
python main.py --quiet ...
```

## Auto task inference (LLM-assisted)

Normally you provide a `tasks.yaml` describing how to run the paper code.
If you want the framework to **infer tasks from the cloned repository** (README + entrypoints):

```bash
python main.py --auto-tasks --auto-tasks-mode smoke "papers/<paper_key>/paper.pdf"
```

- **smoke**: safe, fast checks (such as `python run.py --help`), no dataset/model runs.
- **full**: may propose heavier tasks, but they will be generated with `enabled: false` by default (you can turn them on manually).

If a `tasks.yaml` already exists and you want to overwrite it:

```bash
python main.py --auto-tasks --auto-tasks-force "papers/<paper_key>/paper.pdf"
```

### Manual (not recommended)

1) Install deps (in your current python)

```bash
pip install -r requirements.txt
```

2) Provide a tasks file and optional baseline

- `--tasks`: yaml/json describing commands to run
- `--baseline`: json defining deterministic checks (optional)

3) Run

```bash
python main.py --paper-root "<PATH_TO_PAPER_CODE>" --tasks "<PATH_TO_TASKS.yaml>" --baseline "<PATH_TO_BASELINE.json>"
```

To disable all LLM usage:

```bash
python main.py --no-llm ...
```

### LLM-assisted judging (default on)

If no baseline checks are defined, the system uses an LLM to propose baseline checks and artifact expectations.
This is recorded to `run/<paper_key>/<run_id>/logs/judge_llm_prompt.json` and `judge_llm_response.json` for audit.

To disable it, use `--no-llm`.

## PDF table/structure extraction (MinerU, required by default)

By default, when you provide `--paper-pdf`, the system **requires MinerU** (Magic-PDF) and will run it to extract structured markdown.
Its output is saved under:

- `baseline/<paper_key>/paper_extracted/mineru/paper.mineru.md`

If MinerU isn't installed or extraction fails, the workflow fails fast with a clear `prepare_error` and pointers in `run/<paper_key>/<run_id>/logs/`.

### Install (optional)

```bash
pip install -r requirements_pdf.txt
```

### Disable (optional)

```bash
python main.py --no-pdf-extract "papers/<paper_key>/paper.pdf"
```

## Tasks format (important)

`--tasks` is a yaml/json list. Minimal fields:

- `id`: task name
- `cwd`: working directory (supports `{paper_root}`)
- `cmd`: command list (supports `{paper_root}`)
- `timeout_sec`: optional
- `artifact_paths`: optional list of glob paths to copy into `run/<timestamp>/artifacts/`

The runner also exports environment variables to the paper code:

- `CODE_EVAL_RUN_DIR`
- `CODE_EVAL_ARTIFACT_DIR`
- `CODE_EVAL_PAPER_ROOT`


