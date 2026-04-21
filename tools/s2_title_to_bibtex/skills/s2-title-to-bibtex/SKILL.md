---
name: s2-title-to-bibtex
description: Convert paper titles into BibTeX by querying Semantic Scholar Graph API (no LLM-generated citations). Use when the user asks for “title -> BibTeX”, “给我这些论文的 bibtex”, batch BibTeX retrieval from a list of titles, or when you need fuzzy fallback matching for near-miss titles.
---

# S2 Title → BibTeX (Semantic Scholar)

Convert one or many paper titles into BibTeX **directly from Semantic Scholar Graph API**.

- Exact match first (normalized title equality)
- Fuzzy fallback when exact match fails (prints the matched title)
- Batch mode via stdin or file

## Inputs / prerequisites

- Requires environment variable: `SEMANTIC_SCHOLAR_API_KEY` (or `S2_API_KEY`)
- Script: `scripts/s2_title_to_bibtex.py`

## Quick usage (run the script)

Single title:

```bash
SEMANTIC_SCHOLAR_API_KEY=... \
  python3 ./skills/s2-title-to-bibtex/scripts/s2_title_to_bibtex.py \
  "Paper Title Here"
```

Batch via stdin (one title per line):

```bash
export SEMANTIC_SCHOLAR_API_KEY=...
printf "%s\n" "Title A" "Title B" \
  | python3 ./skills/s2-title-to-bibtex/scripts/s2_title_to_bibtex.py --stdin
```

Batch via file:

```bash
export SEMANTIC_SCHOLAR_API_KEY=...
python3 ./skills/s2-title-to-bibtex/scripts/s2_title_to_bibtex.py --file titles.txt
```

## Output contract (what to return to the user)

- Return BibTeX entries as-is from `citationStyles.bibtex`.
- Separate entries by a blank line.
- If fuzzy fallback was used, include:
  - `% MATCHED_TITLE: <title>` right before the entry
- If in batch mode and nothing is found, include:
  - `% NOT_FOUND: <original title>`

## Notes / guardrails

- Do **not** reformat/rewrite the BibTeX.
- If the user needs higher precision, ask for arXiv id / DOI / Semantic Scholar URL for the missing titles and extend the script to query by id.
