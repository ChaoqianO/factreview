# Run Issues & Fix Log

## Summary

```json
{
  "last_event": "judge",
  "last_event_data": {
    "passed": false,
    "results": [
      {
        "type": "inconclusive_no_baseline",
        "passed": false,
        "run_success": true
      },
      {
        "type": "paper_table_alignment",
        "passed": false,
        "matched": 0,
        "passed_n": 0,
        "failed_n": 0,
        "unmatched_run_metrics": [],
        "critiques_n": 0,
        "alignment_artifact": "alignment/alignment.json"
      }
    ]
  },
  "hint": "See logs/ for detailed command stdout/stderr. If a task failed, check the logs paths in run_failed."
}
```

## Step 1: prepare_start

```json
{
  "paper_key": "compgcn",
  "paper_pdf": "",
  "paper_root": "E:\\code\\fastMCP\\ai_review\\code_evaluation\\baseline\\compgcn\\source"
}
```

## Step 2: prepare_ok

```json
{
  "paper_root": "E:\\code\\fastMCP\\ai_review\\code_evaluation\\baseline\\compgcn\\source",
  "python_spec": "3.11"
}
```

## Step 3: plan_start

```json
{
  "paper_key": "compgcn",
  "paper_root": "E:\\code\\fastMCP\\ai_review\\code_evaluation\\baseline\\compgcn\\source"
}
```

## Step 4: tasks_patch_disable_install_deps

```json
{
  "path": "E:\\code\\fastMCP\\ai_review\\code_evaluation\\baseline\\compgcn\\tasks.yaml"
}
```

## Step 5: tasks_persist_run_dir

```json
{
  "path": "run\\compgcn\\2026-03-09_195349\\tasks.yaml"
}
```

## Step 6: plan_ok

```json
{
  "tasks_path": "run\\compgcn\\2026-03-09_195349\\tasks.yaml",
  "baseline_path": "E:\\code\\fastMCP\\ai_review\\code_evaluation\\baseline\\compgcn\\baseline.json"
}
```

## Step 7: task_start

```json
{
  "task": "install_deps",
  "attempt": 0,
  "cwd": "/app",
  "cmd": [
    "python",
    "-m",
    "pip",
    "install",
    "-r",
    "/app/requirements.txt"
  ],
  "timeout_sec": 3600,
  "use_conda": true,
  "enabled": false
}
```

## Step 8: task_skipped

```json
{
  "task": "install_deps",
  "attempt": 0,
  "reason": "enabled=false"
}
```

## Step 9: task_start

```json
{
  "task": "repo_smoke",
  "attempt": 0,
  "cwd": "/app",
  "cmd": [
    "python",
    "run.py",
    "--help"
  ],
  "timeout_sec": 600,
  "use_conda": true,
  "enabled": true
}
```

## Step 10: task_done

```json
{
  "task": "repo_smoke",
  "attempt": 0,
  "success": true,
  "dry_run": true
}
```

## Step 11: run_ok

```json
{
  "tasks": [
    {
      "id": "install_deps",
      "success": true,
      "skipped": true
    },
    {
      "id": "repo_smoke",
      "success": true,
      "dry_run": true
    }
  ]
}
```

## Step 12: judge

```json
{
  "passed": false,
  "results": [
    {
      "type": "inconclusive_no_baseline",
      "passed": false,
      "run_success": true
    },
    {
      "type": "paper_table_alignment",
      "passed": false,
      "matched": 0,
      "passed_n": 0,
      "failed_n": 0,
      "unmatched_run_metrics": [],
      "critiques_n": 0,
      "alignment_artifact": "alignment/alignment.json"
    }
  ]
}
```

