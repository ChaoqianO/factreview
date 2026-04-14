# Run Issues & Fix Log

## Summary

```json
{
  "last_event": "prepare_error",
  "last_event_data": {
    "error": "docker_paper_image_build_failed",
    "detail": "paper_docker_build_failed: rc=1\n#0 building with \"desktop-linux\" instance using docker driver\n\n#1 [internal] load build definition from Dockerfile\n#1 transferring dockerfile: 5.81kB done\n#1 DONE 0.0s\nDockerfile:113\n--------------------\n 112 |     PY\n 113 | >>>       fi; \\\n 114 | >>>     fi\n 115 |     \n--------------------\nERROR: failed to build: failed to solve: dockerfile parse error on line 113: unknown instruction: fi;\n\nView build details: docker-desktop://dashboard/build/desktop-linux/desktop-linux/rluir3uysrx4rumt7ovzecq1c\n"
  },
  "hint": "See logs/ for detailed command stdout/stderr. If a task failed, check the logs paths in run_failed."
}
```

## Step 1: prepare_start

```json
{
  "paper_key": "compgcn",
  "paper_pdf": "E:\\code\\fastMCP\\ai_review\\code_evaluation\\papers\\compgcn\\compgcn_Composition-based Multi-Relational Graph Convolutional Networks.pdf",
  "paper_root": ""
}
```

## Step 2: prepare_clone_ok

```json
{
  "repo_url": "https://github.com/malllabiisc/CompGCN",
  "dest": "E:\\code\\fastMCP\\ai_review\\code_evaluation\\baseline\\compgcn\\source"
}
```

## Step 3: pdf_extract_skipped

```json
{
  "reason": "disabled_or_unavailable"
}
```

## Step 4: tasks_written

```json
{
  "path": "E:\\code\\fastMCP\\ai_review\\code_evaluation\\baseline\\compgcn\\tasks.yaml",
  "count": 2
}
```

## Step 5: prepare_error

```json
{
  "error": "docker_paper_image_build_failed",
  "detail": "paper_docker_build_failed: rc=1\n#0 building with \"desktop-linux\" instance using docker driver\n\n#1 [internal] load build definition from Dockerfile\n#1 transferring dockerfile: 5.81kB done\n#1 DONE 0.0s\nDockerfile:113\n--------------------\n 112 |     PY\n 113 | >>>       fi; \\\n 114 | >>>     fi\n 115 |     \n--------------------\nERROR: failed to build: failed to solve: dockerfile parse error on line 113: unknown instruction: fi;\n\nView build details: docker-desktop://dashboard/build/desktop-linux/desktop-linux/rluir3uysrx4rumt7ovzecq1c\n"
}
```

