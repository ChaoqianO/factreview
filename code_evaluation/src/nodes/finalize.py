from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from ..tools.fs import ensure_dir, write_text
from ..tools.meta import index_artifacts
from ..tools.recorder import append_event, write_issues_md


def finalize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    run_info = state.get("run", {})
    run_dir = Path(run_info.get("dir") or "")
    artifacts_dir = Path(run_info.get("artifacts_dir") or (run_dir / "artifacts"))

    # 1) update issues.md from state history (authoritative, reproducible)
    write_issues_md(run_dir, state.get("history", []))

    # Make final status explicit
    if state.get("judge", {}).get("passed") is True and state.get("status") != "failed":
        state["status"] = "success"
    else:
        # If we cannot judge due to missing baseline but the run itself succeeded, mark as inconclusive.
        results = (state.get("judge", {}) or {}).get("results") or []
        run_ok = bool((state.get("run_result", {}) or {}).get("success"))
        if (
            state.get("status") != "failed"
            and run_ok
            and isinstance(results, list)
            and any(isinstance(r, dict) and r.get("type") == "inconclusive_no_baseline" for r in results)
        ):
            state["status"] = "inconclusive"

    # 2) write a deterministic summary.json in run dir
    artifacts_index = index_artifacts(artifacts_dir)
    summary = {
        "run_id": run_info.get("id"),
        "status": state.get("status"),
        "attempts": state.get("attempt", 0),
        "run_result": state.get("run_result", {}),
        "judge": state.get("judge", {}),
        "artifacts": artifacts_index,
    }
    write_text(run_dir / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

    # 3) mirror report into compare/
    paper_key = str((state.get("config") or {}).get("paper_key") or "paper")
    compare_root = Path(__file__).resolve().parents[2] / "compare" / paper_key
    reports_dir = ensure_dir(compare_root / "reports")
    diffs_dir = ensure_dir(compare_root / "diffs" / str(run_info.get("id") or "unknown"))

    # main report (human-readable)
    md_lines = []
    md_lines.append(f"# Code Evaluation Report: {run_info.get('id')}")
    md_lines.append("")
    md_lines.append(f"- **status**: {state.get('status')}")
    md_lines.append(f"- **attempts**: {state.get('attempt', 0)}")
    md_lines.append(f"- **passed**: {state.get('judge', {}).get('passed')}")
    md_lines.append("")
    md_lines.append("## Judge results")
    md_lines.append("")
    md_lines.append("```json")
    md_lines.append(json.dumps(state.get("judge", {}), ensure_ascii=False, indent=2))
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("## Run result")
    md_lines.append("")
    md_lines.append("```json")
    md_lines.append(json.dumps(state.get("run_result", {}), ensure_ascii=False, indent=2))
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("## Artifacts index")
    md_lines.append("")
    md_lines.append("```json")
    md_lines.append(json.dumps(artifacts_index, ensure_ascii=False, indent=2))
    md_lines.append("```")
    md_lines.append("")

    # Optional: deterministic paper alignment report (if produced by judge/run)
    alignment_md = artifacts_dir / "alignment" / "alignment.md"
    alignment_json = artifacts_dir / "alignment" / "alignment.json"
    if alignment_md.exists() or alignment_json.exists():
        md_lines.append("## Paper alignment (deterministic)")
        md_lines.append("")
        if alignment_md.exists():
            try:
                md_lines.append(alignment_md.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
        else:
            md_lines.append(f"- alignment_json: {alignment_json}")
            md_lines.append("")

    report_path = reports_dir / f"{run_info.get('id')}.md"
    write_text(report_path, "\n".join(md_lines) + "\n")

    # diff artifacts
    write_text(diffs_dir / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

    # 4) "facts pack" for final review writing (separate from baseline/run/compare)
    review_root = Path(__file__).resolve().parents[2] / "review" / paper_key / str(run_info.get("id") or "unknown")
    ensure_dir(review_root)

    cfg = state.get("config") or {}
    run_result = state.get("run_result") or {}
    judge = state.get("judge") or {}

    # Deterministic actionable hints (no LLM)
    suggestions: list[dict[str, Any]] = []
    # missing baseline => can't conclude
    if any(isinstance(r, dict) and r.get("type") == "inconclusive_no_baseline" for r in (judge.get("results") or [])):
        suggestions.append(
            {
                "type": "define_baseline",
                "why": "No baseline checks defined; cannot verify paper results.",
                "next": "Fill baseline/<paper_key>/baseline.json checks to match a paper table row and ensure artifact_paths collect required outputs.",
            }
        )
    # common deps issue
    if isinstance(run_result, dict) and "difflib" in str(run_result.get("stderr_tail") or "").lower():
        suggestions.append(
            {
                "type": "fix_requirements_stdlib",
                "why": "requirements.txt contains Python stdlib module (difflib); pip cannot install it.",
                "next": "Use run/<paper_key>/<run_id>/logs/requirements.cleaned.txt or patch the repo requirements file; update tasks install_deps to point to cleaned file.",
            }
        )
    # LLM config issues
    if any(isinstance(h, dict) and h.get("kind") == "fix_llm_error" for h in (state.get("history") or [])):
        suggestions.append(
            {
                "type": "llm_config",
                "why": "LLM-based fix step failed due to missing/invalid provider config.",
                "next": "Rerun with --no-llm, or set MODEL_PROVIDER/OPENAI_API_KEY (or Claude keys) and a valid model.",
            }
        )

    facts = {
        "paper_key": paper_key,
        "run_id": run_info.get("id"),
        "status": state.get("status"),
        "repo_url": cfg.get("paper_repo_url") or "",
        "paper_pdf": cfg.get("paper_pdf") or "",
        "paper_pdf_extracted_md": cfg.get("paper_pdf_extracted_md") or "",
        "paper_root": cfg.get("paper_root") or "",
        "local_source_path": cfg.get("local_source_path") or "",
        "conda_prefix": cfg.get("conda_prefix") or "",
        "tasks_path": cfg.get("tasks_path") or "",
        "baseline_path": cfg.get("baseline_path") or "",
        "artifacts_index": artifacts_index,
        "run_result": run_result,
        "judge": judge,
        "paths": {
            "run_dir": str(run_dir),
            "issues_jsonl": str(run_dir / "issues.jsonl"),
            "issues_md": str(run_dir / "issues.md"),
            "compare_report": str(report_path),
            "compare_diff_dir": str(diffs_dir),
        },
        "suggestions": suggestions,
    }
    write_text(review_root / "facts.json", json.dumps(facts, ensure_ascii=False, indent=2) + "\n")
    write_text(
        review_root / "README.md",
        "# Review Facts Pack\n\n"
        "This folder contains **facts-only** artifacts to support writing a final review.\n\n"
        f"- `facts.json`: structured evidence and pointers (paper_key={paper_key}, run_id={run_info.get('id')})\n",
    )

    append_event(run_dir, "finalize", {"report": str(report_path), "diff_dir": str(diffs_dir)})
    state.setdefault("history", []).append({"kind": "finalize", "data": {"report": str(report_path)}})
    return state


