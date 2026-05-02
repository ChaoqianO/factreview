# sacn — code_evaluation report

Generated: 2026-05-02T15:26:15+00:00

This report was produced by `tools/run_demos.py` running the full FactReview
pipeline with `--run-execution` against `paper.pdf` in this directory. The
runner is paper-agnostic; this file is regenerated each time the demo is run.

## Summary

- Category: **Graph**
- Paper key: `graph_sacn`
- Wall time (subprocess): **2m 24s**
- Started: `2026-05-02T15:23:51+00:00`  ·  Finished: `2026-05-02T15:26:15+00:00`
- Pipeline exit code: `1`
- Execution exit_status: `failed`
- Coverage: no baseline checks were defined or evaluated.
- LLM tokens (parse-stage agent): prompt=0 · completion=0 · total=0

## Stage status

| stage | status | error |
| --- | --- | --- |
| parse | ok |  |
| claim_extract | ok |  |
| refcheck | skipped |  |
| positioning | ok |  |
| execution | failed | execution orchestrator exit_status='failed' |
| report | ok |  |
| teaser | ok |  |

## Execution attempts & tasks

- Attempts: 0

_No execution tasks recorded._

## Artefacts (paths relative to this demo)

- Final review (markdown): `_run/graph_sacn_2026-05-02_232353/stages/review/report/final_review.md`
- Final review (PDF): `_run/graph_sacn_2026-05-02_232353/stages/review/report/final_review.pdf`
- Execution payload: `_run/graph_sacn_2026-05-02_232353/stages/fact_generation/execution/execution.json`
- Positioning: `_run/graph_sacn_2026-05-02_232353/stages/fact_generation/positioning/positioning.json`
- Claim extraction: `_run/graph_sacn_2026-05-02_232353/stages/preprocessing/claim_extract/facts.json`
- Parse output: `_run/graph_sacn_2026-05-02_232353/stages/preprocessing/parse/paper.json`
- Teaser prompt: `_run/graph_sacn_2026-05-02_232353/stages/review/teaser/teaser_figure_prompt.txt`

## Notes

- Execution failed: execution orchestrator exit_status='failed'
- Pipeline subprocess exit code: 1
