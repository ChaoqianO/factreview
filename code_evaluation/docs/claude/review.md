# Code Review Checklist

When reviewing changes to the code_evaluation framework:

## Correctness
- [ ] State semantics preserved: status field uses only running/failed/success/inconclusive
- [ ] Judge results list only contains known types: file_exists, json_value, csv_agg, paper_table_alignment, inconclusive_no_baseline, llm_judge
- [ ] Routing logic in workflow.py matches node output semantics
- [ ] Exit code mapping: 0=success, 1=failed, 2=inconclusive

## Evidence integrity
- [ ] Deterministic checks are never replaced by LLM judgments
- [ ] All judge results are appended to state["history"] for audit
- [ ] facts.json contains checks_summary, alignment_summary, coverage_gaps
- [ ] Report distinguishes verified/inconclusive/deviated/execution_failed

## Backward compatibility
- [ ] tasks.yaml without family/dataset fields still works (fallback logic)
- [ ] baseline.json without claim field still works
- [ ] --no-llm mode produces complete output without errors
