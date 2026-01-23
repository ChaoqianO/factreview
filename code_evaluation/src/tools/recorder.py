from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

from .fs import ensure_dir, write_text


@dataclass
class Event:
    ts: float
    kind: str
    data: Dict[str, Any]


def _is_verbose() -> bool:
    v = (os.getenv("CODE_EVAL_VERBOSE") or "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


def _console_event_line(kind: str, data: Dict[str, Any], run_dir: Path) -> str:
    """
    Human-friendly, single-line event summary for console tracing.
    Keep it short; detailed stdout/stderr remains in logs/ files.
    """
    try:
        payload = json.dumps(data or {}, ensure_ascii=False)
    except Exception:
        payload = str(data)
    # avoid flooding the console
    if len(payload) > 800:
        payload = payload[:800] + "...(truncated)"
    return f"[code_evaluation][{kind}] run_dir={str(run_dir)} data={payload}"


def append_event(run_dir: str | Path, kind: str, data: Dict[str, Any]) -> None:
    d = ensure_dir(run_dir)
    ev = Event(ts=time.time(), kind=kind, data=data)
    path = d / "issues.jsonl"
    line = json.dumps(asdict(ev), ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if _is_verbose():
        try:
            print(_console_event_line(kind, data, d), flush=True)
        except Exception:
            # never break workflow due to console printing issues
            pass


def write_issues_md(run_dir: str | Path, history: List[Dict[str, Any]]) -> None:
    """
    Human-readable issue narrative. The 'history' is state-managed so it is always reproducible.
    """
    d = Path(run_dir)
    lines: List[str] = []
    lines.append("# Run Issues & Fix Log")
    lines.append("")

    # Prefer the event stream (issues.jsonl) because it provides a step-by-step timeline
    # including prepare sub-steps (clone/env) and detailed errors.
    events_path = d / "issues.jsonl"
    events: List[Dict[str, Any]] = []
    if events_path.exists():
        try:
            for raw in events_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    events.append(json.loads(raw))
                except Exception:
                    continue
        except Exception:
            events = []

    # Quick summary
    if events:
        last = events[-1]
        last_kind = (last.get("kind") or "").strip()
        lines.append("## Summary")
        lines.append("")
        lines.append("```json")
        lines.append(
            json.dumps(
                {
                    "last_event": last_kind,
                    "last_event_data": last.get("data", {}),
                    "hint": "See logs/ for detailed command stdout/stderr. If a task failed, check the logs paths in run_failed.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        lines.append("```")
        lines.append("")

    # Timeline
    if events:
        for i, ev in enumerate(events, 1):
            lines.append(f"## Step {i}: {ev.get('kind','event')}")
            lines.append("")
            payload = ev.get("data", {})
            lines.append("```json")
            lines.append(json.dumps(payload, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
    else:
        # Fallback: state history (older runs / tests)
        for i, step in enumerate(history, 1):
            lines.append(f"## Step {i}: {step.get('kind','event')}")
            lines.append("")
            payload = step.get("data", {})
            lines.append("```json")
            lines.append(json.dumps(payload, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

    write_text(d / "issues.md", "\n".join(lines) + "\n")


