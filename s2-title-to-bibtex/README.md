# s2-title-to-bibtex

Convert paper titles into BibTeX **directly from Semantic Scholar Graph API** (no LLM-generated citations).

- Exact match first (normalized title equality)
- Fuzzy fallback when exact match fails (prints `% MATCHED_TITLE: ...`)
- Batch mode via stdin or file

## Requirements

- Python 3.9+
- A Semantic Scholar Graph API key
  - Set **one** of:
    - `SEMANTIC_SCHOLAR_API_KEY` (preferred)
    - `S2_API_KEY`

## Install (CLI)

Recommended via `pipx`:

```bash
pipx install git+https://github.com/LeoYML/s2-title-to-bibtex.git
```

Or via pip:

```bash
pip install git+https://github.com/LeoYML/s2-title-to-bibtex.git
```

This installs the command:

```bash
s2-title-to-bibtex --help
```

## Usage (CLI)

Single title:

```bash
export SEMANTIC_SCHOLAR_API_KEY=...
s2-title-to-bibtex "Paper Title Here"
```

Batch via stdin (one title per line):

```bash
export SEMANTIC_SCHOLAR_API_KEY=...
printf "%s\n" "Title A" "Title B" | s2-title-to-bibtex --stdin
```

Batch via file:

```bash
export SEMANTIC_SCHOLAR_API_KEY=...
s2-title-to-bibtex --file titles.txt
```

## Output contract

- BibTeX entries are returned as-is from `citationStyles.bibtex`.
- Entries are separated by a blank line.
- If fuzzy fallback was used, the tool includes:

```bibtex
% MATCHED_TITLE: <title>
```

right before the entry.

- In batch mode, if nothing is found:

```text
% NOT_FOUND: <original title>
```

## OpenClaw skill

This repo also includes an OpenClaw skill at:

- `skills/s2-title-to-bibtex/`

If you use OpenClaw Skills, you can package that directory into a `.skill` file and install it. (The skill runs the same logic via a bundled script.)

## Development / testing

Unit tests (offline, mocked HTTP):

```bash
python -m pip install -e '.[dev]'
pytest -q
```

Integration tests (real Semantic Scholar API; requires `SEMANTIC_SCHOLAR_API_KEY` or `S2_API_KEY`):

```bash
export SEMANTIC_SCHOLAR_API_KEY=...
pytest -q -m integration
```

## License

MIT. See `LICENSE`.
