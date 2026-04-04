from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ..tools.baseline import Baseline
from ..tools.alignment import run_alignment
from ..tools.llm import llm_json, resolve_llm_config
from ..tools.meta import index_artifacts
from ..tools.metrics import compute_check
from ..tools.recorder import append_event
from ..tools.fs import write_text


def _read_optional(path: str, max_chars: int = 14000) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if len(txt) > max_chars:
            return txt[:max_chars] + "\n...(truncated)\n"
        return txt
    except Exception:
        return ""


def _llm_judge_enabled(cfg: Dict[str, Any]) -> str:
    mode = str(cfg.get("llm_judge_mode") or "").strip().lower()
    if mode in {"assist", "verdict"}:
        return mode
    return "off"


def judge_node(state: Dict[str, Any]) -> Dict[str, Any]:
    run_info = state.get("run", {})
    run_dir = Path(run_info.get("dir") or "")
    artifacts_dir = Path(run_info.get("artifacts_dir") or (run_dir / "artifacts"))
    logs_dir = Path(run_info.get("logs_dir") or (run_dir / "logs"))

    baseline_raw = state.get("baseline") or {}
    baseline = Baseline(raw=baseline_raw if isinstance(baseline_raw, dict) else {})

    checks = baseline.checks
    results: List[Dict[str, Any]] = []
    passed = True
    run_ok = bool(state.get("run_result", {}).get("success"))
    cfg = state.get("config", {}) or {}

    # ── Evidence source 1: Deterministic baseline checks ──
    if not checks:
        passed = False
        results.append({"type": "inconclusive_no_baseline", "passed": False, "run_success": run_ok})
    else:
        for chk in checks:
            r = compute_check(str(artifacts_dir), chk)
            results.append(r)
            if not r.get("passed"):
                passed = False

    # ── Evidence source 2: Paper-table alignment (always, independent of baseline) ──
    try:
        paper_key = str(cfg.get("paper_key") or "").strip() or "paper"
        repo_root = Path(__file__).resolve().parents[2]
        paper_tables_dir = repo_root / "baseline" / paper_key / "paper_extracted" / "tables"
        if paper_tables_dir.exists():
            ar = run_alignment(cfg=cfg, run_dir=run_dir, artifacts_dir=artifacts_dir, paper_extracted_tables_dir=paper_tables_dir)
            results.append(
                {
                    "type": "paper_table_alignment",
                    "passed": bool(ar.matched > 0 and ar.failed == 0 and run_ok),
                    "matched": ar.matched,
                    "passed_n": ar.passed,
                    "failed_n": ar.failed,
                    "unmatched_run_metrics": ar.unmatched_run_metrics,
                    "critiques_n": len(ar.critiques or []),
                    "alignment_artifact": "alignment/alignment.json",
                }
            )
    except Exception as e:
        results.append({"type": "paper_table_alignment", "passed": False, "error": f"{type(e).__name__}: {e}"})

    # ── Evidence source 3: LLM judge (advisory by default) ──
    llm_mode = _llm_judge_enabled(cfg)
    if llm_mode != "off" and (not bool(cfg.get("no_llm"))):
        extracted_md = str(cfg.get("paper_pdf_extracted_md") or "").strip()
        evidence = {
            "paper_key": str(cfg.get("paper_key") or ""),
            "paper_pdf": str(cfg.get("paper_pdf") or ""),
            "paper_root": str(cfg.get("paper_root") or ""),
            "repo_url": str(cfg.get("paper_repo_url") or ""),
            "run_id": str(run_info.get("id") or ""),
            "run_success": run_ok,
            "run_result": state.get("run_result") or {},
            "artifacts_index": index_artifacts(artifacts_dir),
            "paper_extracted_md_excerpt": _read_optional(extracted_md, max_chars=14000),
            "baseline_current": baseline_raw if isinstance(baseline_raw, dict) else {},
        }
        system = (
            "You are judging whether a paper reproduction run matches claimed results.\n"
            "Return JSON only. Do not include prose outside JSON.\n"
            "If evidence is insufficient, keep verdict as inconclusive and propose concrete baseline checks.\n"
        )
        prompt = json.dumps(
            {
                "mode": llm_mode,
                "evidence": evidence,
                "output_schema": {
                    "verdict": "pass|fail|inconclusive",
                    "confidence": 0.0,
                    "why": ["short strings"],
                    "suggested_artifacts": ["paths or patterns to collect"],
                    "suggested_baseline_checks": [
                        {"type": "file_exists", "path": "relative/to/artifacts"},
                        {
                            "type": "json_value",
                            "path": "relative/to/artifacts",
                            "json_path": ["key", 0, "subkey"],
                            "expected": 0.0,
                            "tolerance": 0.0,
                        },
                        {
                            "type": "csv_agg",
                            "path": "relative/to/artifacts",
                            "expr": {"groupby": ["col"], "agg": {"metric": "mean"}},
                            "expected": [{"col": "x", "metric": 0.0}],
                            "tolerance": 0.0,
                        },
                    ],
                },
            },
            ensure_ascii=False,
        )
        llm_cfg = resolve_llm_config(str(cfg.get("llm_provider") or ""), str(cfg.get("llm_model") or ""), str(cfg.get("llm_base_url") or ""))
        resp = llm_json(prompt=prompt, system=system, cfg=llm_cfg)
        try:
            write_text(logs_dir / "judge_llm_prompt.json", prompt + "\n")
            write_text(logs_dir / "judge_llm_response.json", json.dumps(resp, ensure_ascii=False, indent=2) + "\n")
        except Exception:
            pass

        verdict = str(resp.get("verdict") or "").strip().lower() if isinstance(resp, dict) else ""
        conf = resp.get("confidence") if isinstance(resp, dict) else None
        results.append(
            {
                "type": "llm_judge",
                "mode": llm_mode,
                "passed": (verdict == "pass") if llm_mode == "verdict" else False,
                "verdict": verdict or "inconclusive",
                "confidence": conf,
                "response": resp,
            }
        )
        if llm_mode == "verdict" and verdict in {"pass", "fail"}:
            passed = verdict == "pass"

    judge = {"passed": passed, "results": results}
    state["judge"] = judge

    append_event(run_dir, "judge", {"passed": passed, "results": results})
    state.setdefault("history", []).append({"kind": "judge", "data": {"passed": passed, "results": results}})

    # Preserve failed status from earlier nodes; do not overwrite with "running"
    if state.get("status") != "failed":
        state["status"] = "running"
    return state


