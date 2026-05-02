# lrcn — code_evaluation report

Generated: 2026-05-02T06:31:51+00:00

This report was produced by `tools/run_demos.py` running the full FactReview
pipeline with `--run-execution` against `paper.pdf` in this directory. The
runner is paper-agnostic; this file is regenerated each time the demo is run.

## Summary

- Category: **Image**
- Paper key: `image_lrcn`
- Wall time (subprocess): **17.3s**
- Started: `2026-05-02T06:31:34+00:00`  ·  Finished: `2026-05-02T06:31:51+00:00`
- Pipeline exit code: `0`
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
| report | failed | agent runner produced no final_markdown_path |
| teaser | failed | no review markdown produced by the report stage (checked final_review_clean.md … |

## Execution attempts & tasks

- Attempts: 0

_No execution tasks recorded._

## Artefacts (paths relative to this demo)

- Execution payload: `_run/image_lrcn_2026-05-02_143135/stages/fact_generation/execution/execution.json`
- Positioning: `_run/image_lrcn_2026-05-02_143135/stages/fact_generation/positioning/positioning.json`
- Claim extraction: `_run/image_lrcn_2026-05-02_143135/stages/preprocessing/claim_extract/facts.json`
- Parse output: `_run/image_lrcn_2026-05-02_143135/stages/preprocessing/parse/paper.json`

## Notes

- Execution failed: execution orchestrator exit_status='failed'
