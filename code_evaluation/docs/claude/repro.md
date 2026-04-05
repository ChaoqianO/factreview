# Paper Reproduction Run Guide

## Directory structure
- `baseline/<paper_key>/` — tasks.yaml, baseline.json, source/, paper_extracted/
- `run/<paper_key>/<timestamp>/` — logs, artifacts, summary.json
- `compare/<paper_key>/reports/` — reviewer-facing report
- `review/<paper_key>/<run_id>/` — facts.json evidence pack

## Running a reproduction
```bash
cd code_evaluation/code_evaluation
python main.py baseline/<paper_key>/paper.pdf --no-llm
```

## Exit codes
- 0 = verified (baseline checks passed)
- 1 = failed (execution or check failure)
- 2 = inconclusive (ran OK but no/insufficient baseline)

## tasks.yaml structured fields
Each task supports optional: `family` (train/eval/prepare/smoke), `dataset`, `claims` (list of paper claim strings).

## baseline.json check types
- `file_exists`: artifact file must exist
- `json_value`: JSON path must match expected value within tolerance
- `csv_agg`: pandas groupby/agg must match

## Key principle
The pipeline produces **facts**, not opinions. If evidence is insufficient, the verdict is `inconclusive`, never a fabricated `pass`.
