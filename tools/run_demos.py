"""Generic batch runner for FactReview demos.

Walks ``<demos-root>/<category>/<paper>/paper.pdf``, runs the full pipeline
with ``--run-execution`` for each, and writes a per-demo ``README.md``
recording wall-clock time, LLM token usage, baseline-check coverage, and
links to the produced artefacts. The runner is intentionally paper-agnostic:
no paper names, dataset names, or framework-specific behavior is hardcoded.

Output policy: each demo's run artefacts go under
``<demos-root>/<category>/<paper>/<output-subdir>/``. A small ``.gitignore``
is dropped inside that subdir so heavy artefacts (logs, MinerU dumps,
runtime jobs, Docker workspaces, checkpoints) are not committed while the
small JSON summaries and the rendered ``final_review.md`` are.

Usage:

    python tools/run_demos.py \
        --demos-root demos \
        --skip compgcn \
        --concurrency 2 \
        --paper-budget-sec 1800 \
        --max-attempts 2 \
        --auto-tasks --auto-tasks-mode full
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
PIPELINE_SCRIPT = SCRIPTS_DIR / "execute_review_pipeline.py"


# --------------------------- demo discovery ---------------------------


@dataclass
class Demo:
    category: str  # e.g. "Graph"
    name: str  # e.g. "compgcn"
    pdf_path: Path

    @property
    def paper_key(self) -> str:
        # Lowercase + sanitized, paper-agnostic. The framework already accepts
        # arbitrary keys; this just keeps it filesystem-friendly.
        return f"{self.category.lower()}_{self.name.replace(' ', '_')}"

    @property
    def demo_dir(self) -> Path:
        return self.pdf_path.parent


def discover_demos(demos_root: Path, skip: set[str]) -> list[Demo]:
    demos: list[Demo] = []
    for category_dir in sorted(p for p in demos_root.iterdir() if p.is_dir()):
        for paper_dir in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            if paper_dir.name in skip:
                continue
            pdf = paper_dir / "paper.pdf"
            if not pdf.exists():
                continue
            demos.append(Demo(category=category_dir.name, name=paper_dir.name, pdf_path=pdf))
    return demos


# --------------------------- per-demo run ---------------------------


@dataclass
class RunRecord:
    demo: Demo
    started_at: str
    finished_at: str
    wall_sec: float
    return_code: int
    run_dir: Path | None
    timed_out: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


async def run_one_demo(
    demo: Demo,
    *,
    output_subdir: str,
    paper_budget_sec: int,
    max_attempts: int,
    auto_tasks: bool,
    auto_tasks_mode: str,
    extra_args: list[str],
    hard_kill_grace_sec: int,
    log_prefix: str = "",
) -> RunRecord:
    out_root = demo.demo_dir / output_subdir
    out_root.mkdir(parents=True, exist_ok=True)
    _ensure_run_gitignore(out_root)

    cmd: list[str] = [
        sys.executable,
        str(PIPELINE_SCRIPT),
        str(demo.pdf_path),
        "--paper-key",
        demo.paper_key,
        "--run-root",
        str(out_root),
        "--run-execution",
        "--max-attempts",
        str(max_attempts),
    ]
    if paper_budget_sec > 0:
        cmd += ["--paper-budget-sec", str(paper_budget_sec)]
    if auto_tasks:
        cmd += ["--auto-tasks", "--auto-tasks-mode", auto_tasks_mode]
    cmd += list(extra_args or [])

    started = time.monotonic()
    started_iso = datetime.now(UTC).isoformat(timespec="seconds")
    print(f"{log_prefix}[start ] {demo.paper_key}\n  cmd: {shlex.join(cmd)}", flush=True)

    # Hard kill = budget + grace (covers Docker build + parse + report stages).
    hard_timeout = paper_budget_sec + hard_kill_grace_sec if paper_budget_sec > 0 else None

    # On Windows, put the child in a new process group so we can kill the
    # whole tree (Docker, MinerU CLI, child Python) via taskkill /T. On
    # POSIX, start a new session so os.killpg can reach descendants.
    creation_flags = 0
    preexec = None
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        preexec = os.setsid  # type: ignore[assignment]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(ROOT),
        env=os.environ.copy(),
        creationflags=creation_flags,
        preexec_fn=preexec,
    )

    log_path = out_root / f"{demo.paper_key}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    timed_out = False
    try:
        async with _stream_to_file(proc, log_path):
            if hard_timeout:
                try:
                    await asyncio.wait_for(proc.wait(), timeout=hard_timeout)
                except asyncio.TimeoutError:
                    timed_out = True
                    _kill_process_tree(proc.pid)
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=30)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
            else:
                await proc.wait()
    finally:
        rc = proc.returncode if proc.returncode is not None else -1

    wall = time.monotonic() - started
    finished_iso = datetime.now(UTC).isoformat(timespec="seconds")

    # Find the actual run_dir produced (most recent under out_root matching paper_key prefix).
    run_dir = _latest_run_dir(out_root, demo.paper_key)

    print(
        f"{log_prefix}[done  ] {demo.paper_key} "
        f"rc={rc} wall={wall:.1f}s timeout={timed_out} run_dir={run_dir}",
        flush=True,
    )

    return RunRecord(
        demo=demo,
        started_at=started_iso,
        finished_at=finished_iso,
        wall_sec=wall,
        return_code=rc,
        run_dir=run_dir,
        timed_out=timed_out,
    )


class _stream_to_file:
    def __init__(self, proc: asyncio.subprocess.Process, path: Path) -> None:
        self._proc = proc
        self._path = path
        self._task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> "_stream_to_file":
        async def _drain() -> None:
            assert self._proc.stdout is not None
            with self._path.open("ab") as fh:
                while True:
                    chunk = await self._proc.stdout.read(4096)
                    if not chunk:
                        break
                    fh.write(chunk)
                    fh.flush()

        self._task = asyncio.create_task(_drain())
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._task is not None:
            try:
                await self._task
            except Exception:
                pass


def _kill_process_tree(pid: int) -> None:
    """Forcefully terminate a process and all its descendants.

    On Windows ``proc.kill()`` only kills the immediate subprocess, so when
    the pipeline subprocess has spawned its own grandchildren (Docker CLI,
    MinerU client, agent runners), they survive and the wait_for never
    returns. Using ``taskkill /F /T`` walks the full tree. On POSIX we
    rely on the new session id from ``os.setsid`` and ``os.killpg``.
    """
    if pid <= 0:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
                check=False,
            )
        except Exception:
            pass
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass


def _latest_run_dir(out_root: Path, paper_key: str) -> Path | None:
    if not out_root.exists():
        return None
    # The pipeline lowercases the paper key when forming the run-dir name, so
    # match case-insensitively to handle keys like ``text_Prefix-Tuning``.
    prefix = (paper_key + "_").lower()
    candidates = [
        p for p in out_root.iterdir() if p.is_dir() and p.name.lower().startswith(prefix)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


# --------------------------- artifact scraping ---------------------------


def scrape_artifacts(run_dir: Path | None) -> dict[str, Any]:
    """Read everything we want into the per-demo README from the run dir.

    Resilient to partial runs: every key is optional. Returns a dict shaped
    like::

        {
          "stages": {...},  # full_pipeline_summary.json["stages"]
          "stage_errors": {...},
          "outputs": {...},
          "execution": {...},  # execution.json payload
          "execution_summary": {...},  # current/summary.json
          "tokens": {"prompt": ..., "completion": ..., "total": ...},
          "exec_tasks": [{"id": ..., "success": ..., "duration_sec": ...}, ...],
        }
    """
    out: dict[str, Any] = {
        "stages": {},
        "stage_errors": {},
        "outputs": {},
        "execution": {},
        "execution_summary": {},
        "tokens": {"prompt": 0, "completion": 0, "total": 0, "found": False},
        "exec_tasks": [],
        "exec_attempts": 0,
    }
    if run_dir is None or not run_dir.exists():
        return out

    full = _read_json(run_dir / "full_pipeline_summary.json")
    if full:
        out["stages"] = dict(full.get("stages") or {})
        out["stage_errors"] = dict(full.get("stage_errors") or {})
        out["outputs"] = dict(full.get("outputs") or {})

    exec_json = _read_json(
        run_dir / "stages" / "fact_generation" / "execution" / "execution.json"
    )
    if exec_json:
        out["execution"] = exec_json

    exec_summary = _read_json(
        run_dir / "stages" / "fact_generation" / "execution" / "current" / "summary.json"
    )
    if exec_summary:
        out["execution_summary"] = exec_summary
        rr = exec_summary.get("run_result") or {}
        tasks = rr.get("tasks") or []
        if isinstance(tasks, list):
            out["exec_tasks"] = [
                {
                    "id": str(t.get("id") or ""),
                    "family": str(t.get("family") or ""),
                    "success": bool(t.get("success")),
                    "duration_sec": float(t.get("duration_sec") or 0.0),
                    "error": str(t.get("error") or ""),
                }
                for t in tasks
                if isinstance(t, dict)
            ]
        out["exec_attempts"] = int(exec_summary.get("attempts") or 0)

    # Token usage from the parse-stage runtime job.
    job_id = (full or {}).get("job_id") or ""
    if job_id:
        job = _read_json(run_dir / "runtime" / "jobs" / str(job_id) / "job.json")
        if isinstance(job, dict):
            usage = job.get("usage") or {}
            if isinstance(usage, dict):
                out["tokens"] = {
                    "prompt": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
                    "completion": int(
                        usage.get("completion_tokens") or usage.get("output_tokens") or 0
                    ),
                    "total": int(usage.get("total_tokens") or 0),
                    "found": True,
                }

    return out


# --------------------------- README rendering ---------------------------


_STAGE_ORDER = ("parse", "claim_extract", "refcheck", "positioning", "execution", "report", "teaser")


def render_readme(rec: RunRecord, scraped: dict[str, Any]) -> str:
    demo = rec.demo
    stages = scraped.get("stages") or {}
    errors = scraped.get("stage_errors") or {}
    outputs = scraped.get("outputs") or {}
    execution = scraped.get("execution") or {}
    tokens = scraped.get("tokens") or {}
    exec_tasks: list[dict[str, Any]] = scraped.get("exec_tasks") or []
    exec_attempts = int(scraped.get("exec_attempts") or 0)

    exit_status = str(execution.get("exit_status") or "unknown")
    coverage_text = _coverage_text(execution)

    # Stage table
    stage_rows = []
    for name in _STAGE_ORDER:
        status = stages.get(name, "n/a")
        err = errors.get(name) or ""
        stage_rows.append(_md_row([name, status, _truncate(err, 80)]))
    stage_table = _md_table(["stage", "status", "error"], stage_rows)

    # Tasks table
    if exec_tasks:
        rows = []
        for t in exec_tasks:
            rows.append(
                _md_row(
                    [
                        t.get("id", ""),
                        t.get("family") or "",
                        "ok" if t.get("success") else "fail",
                        f"{float(t.get('duration_sec') or 0.0):.1f}s",
                        _truncate(t.get("error") or "", 80),
                    ]
                )
            )
        tasks_table = _md_table(["task", "family", "status", "duration", "error"], rows)
    else:
        tasks_table = "_No execution tasks recorded._"

    if tokens.get("found"):
        token_line = (
            f"- LLM tokens (parse-stage agent): "
            f"prompt={tokens.get('prompt', 0):,} · "
            f"completion={tokens.get('completion', 0):,} · "
            f"total={tokens.get('total', 0):,}"
        )
    else:
        token_line = "- LLM tokens: not recorded for this run."

    # Artefacts list (relative to the demo dir for portability).
    rel_artefacts: list[str] = []
    for label, key in (
        ("Final review (markdown)", "report_md"),
        ("Final review (PDF)", "report_pdf"),
        ("Execution payload", "execution"),
        ("Positioning", "positioning"),
        ("Claim extraction", "claim_extract"),
        ("Parse output", "parse"),
        ("Teaser prompt", "teaser_figure_prompt"),
    ):
        path = outputs.get(key)
        if path:
            rel = _relative_to_demo(Path(path), demo.demo_dir)
            rel_artefacts.append(f"- {label}: `{rel}`")

    if not rel_artefacts:
        rel_artefacts.append("- _No primary artefacts recorded — see run log._")

    notes: list[str] = []
    if rec.timed_out:
        notes.append(
            "- Subprocess hit the hard wall-clock kill timeout; later stages may be missing."
        )
    if exit_status == "partial":
        notes.append(
            "- Execution stage stopped early because the per-paper soft budget was reached."
        )
    elif exit_status == "failed":
        reason = (execution.get("summary") or {}).get("error") or errors.get("execution") or ""
        if reason:
            notes.append(f"- Execution failed: {_truncate(reason, 200)}")
    if rec.return_code != 0:
        notes.append(f"- Pipeline subprocess exit code: {rec.return_code}")

    notes_block = "\n".join(notes) if notes else "_No notable issues._"

    md = f"""# {demo.name} — code_evaluation report

Generated: {rec.finished_at}

This report was produced by `tools/run_demos.py` running the full FactReview
pipeline with `--run-execution` against `paper.pdf` in this directory. The
runner is paper-agnostic; this file is regenerated each time the demo is run.

## Summary

- Category: **{demo.category}**
- Paper key: `{demo.paper_key}`
- Wall time (subprocess): **{_fmt_seconds(rec.wall_sec)}**
- Started: `{rec.started_at}`  ·  Finished: `{rec.finished_at}`
- Pipeline exit code: `{rec.return_code}`{' (timed out)' if rec.timed_out else ''}
- Execution exit_status: `{exit_status}`
- {coverage_text}
{token_line}

## Stage status

{stage_table}

## Execution attempts & tasks

- Attempts: {exec_attempts}

{tasks_table}

## Artefacts (paths relative to this demo)

{chr(10).join(rel_artefacts)}

## Notes

{notes_block}
"""
    return md


# --------------------------- helpers ---------------------------


def _md_row(cells: list[str]) -> str:
    safe = [str(c).replace("|", "\\|").replace("\n", " ") for c in cells]
    return "| " + " | ".join(safe) + " |"


def _md_table(headers: list[str], rows: list[str]) -> str:
    head = _md_row(headers)
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    return "\n".join([head, sep, *rows])


def _truncate(text: str, n: int) -> str:
    s = str(text or "").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def _coverage_text(execution: dict[str, Any]) -> str:
    summary = (execution.get("summary") or {})
    judge = summary.get("judge") or {}
    results = judge.get("results") or []
    if isinstance(results, list) and results:
        passed = sum(1 for r in results if isinstance(r, dict) and r.get("ok") is True)
        total = len(results)
        pct = (passed * 100 // total) if total else 0
        return f"Coverage: **{passed} / {total} baseline checks passed ({pct}%)**"
    return "Coverage: no baseline checks were defined or evaluated."


def _fmt_seconds(s: float) -> str:
    s = max(0.0, float(s))
    if s < 60:
        return f"{s:.1f}s"
    m, sec = divmod(int(s), 60)
    if m < 60:
        return f"{m}m {sec}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m {sec}s"


def _relative_to_demo(path: Path, demo_dir: Path) -> str:
    try:
        return str(path.resolve().relative_to(demo_dir.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _ensure_run_gitignore(out_root: Path) -> None:
    """Drop a small .gitignore so we keep small JSON summaries but skip bulk."""
    gitignore = out_root / ".gitignore"
    if gitignore.exists():
        return
    gitignore.write_text(
        "# Auto-generated by tools/run_demos.py.\n"
        "# Keep run dirs (per-paper timestamped) but exclude bulky subtrees.\n"
        "**/runtime/\n"
        "**/workspace/\n"
        "**/logs/\n"
        "**/debug/\n"
        "**/artifacts/\n"
        "**/inputs/source_pdf/\n"
        "**/inputs/baseline/*/paper.pdf\n"
        "**/inputs/paper_extracted/mineru_assets/\n"
        "**/stages/fact_generation/execution/current/artifacts/\n"
        "**/stages/fact_generation/execution/current/logs/\n"
        "**/stages/fact_generation/execution/current/workspace/\n"
        "**/stages/fact_generation/execution/history/\n"
        "**/stages/fact_generation/execution/current.*/\n"
        "*.log\n",
        encoding="utf-8",
    )


# --------------------------- driver ---------------------------


async def main_async(args: argparse.Namespace) -> int:
    demos_root = Path(args.demos_root).resolve()
    if not demos_root.exists():
        print(f"[error] demos root not found: {demos_root}", file=sys.stderr)
        return 2
    skip = {s.strip() for s in str(args.skip or "").split(",") if s.strip()}
    demos = discover_demos(demos_root, skip)
    if not demos:
        print(f"[error] no demo papers under {demos_root}", file=sys.stderr)
        return 2
    print(f"[plan] {len(demos)} demos: {', '.join(d.paper_key for d in demos)}")

    extra_args = list(args.extra or [])
    sem = asyncio.Semaphore(max(1, int(args.concurrency)))
    results: list[RunRecord] = []

    async def _bound(demo: Demo, idx: int) -> RunRecord:
        async with sem:
            return await run_one_demo(
                demo,
                output_subdir=args.output_subdir,
                paper_budget_sec=int(args.paper_budget_sec),
                max_attempts=int(args.max_attempts),
                auto_tasks=bool(args.auto_tasks),
                auto_tasks_mode=str(args.auto_tasks_mode),
                extra_args=extra_args,
                hard_kill_grace_sec=int(args.hard_kill_grace_sec),
                log_prefix=f"[{idx + 1}/{len(demos)}] ",
            )

    coros = [_bound(d, i) for i, d in enumerate(demos)]
    for fut in asyncio.as_completed(coros):
        rec = await fut
        results.append(rec)

        try:
            scraped = scrape_artifacts(rec.run_dir)
            md = render_readme(rec, scraped)
            readme = rec.demo.demo_dir / "README.md"
            readme.write_text(md, encoding="utf-8")
            print(f"[readme] wrote {readme}")
        except Exception as exc:
            print(f"[readme-error] {rec.demo.paper_key}: {exc}", file=sys.stderr)

    # Emit a top-level batch summary at demos-root level for convenience.
    try:
        batch = {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "demos_root": str(demos_root),
            "skipped": sorted(skip),
            "concurrency": int(args.concurrency),
            "paper_budget_sec": int(args.paper_budget_sec),
            "max_attempts": int(args.max_attempts),
            "auto_tasks": bool(args.auto_tasks),
            "auto_tasks_mode": str(args.auto_tasks_mode),
            "results": [
                {
                    "paper_key": r.demo.paper_key,
                    "category": r.demo.category,
                    "name": r.demo.name,
                    "started_at": r.started_at,
                    "finished_at": r.finished_at,
                    "wall_sec": round(r.wall_sec, 2),
                    "return_code": r.return_code,
                    "timed_out": r.timed_out,
                    "run_dir": str(r.run_dir or ""),
                }
                for r in results
            ],
        }
        (demos_root / "_run_demos_summary.json").write_text(
            json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except Exception as exc:
        print(f"[summary-error] {exc}", file=sys.stderr)

    failures = [r for r in results if r.return_code != 0]
    return 0 if not failures else 1


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser("run_demos")
    p.add_argument("--demos-root", default="demos", help="Root directory containing <category>/<paper>/paper.pdf")
    p.add_argument("--skip", default="", help="Comma-separated paper-folder names to skip")
    p.add_argument("--concurrency", type=int, default=2)
    p.add_argument("--paper-budget-sec", type=int, default=1800)
    p.add_argument("--max-attempts", type=int, default=2)
    p.add_argument("--auto-tasks", action="store_true")
    p.add_argument("--auto-tasks-mode", choices=("smoke", "full"), default="smoke")
    p.add_argument("--output-subdir", default="_run", help="Subdir under each demo for run outputs")
    p.add_argument(
        "--hard-kill-grace-sec",
        type=int,
        default=900,
        help="Extra seconds added to paper-budget-sec before forcibly killing the subprocess.",
    )
    p.add_argument(
        "--extra",
        nargs=argparse.REMAINDER,
        default=[],
        help="Trailing args after `--` are forwarded verbatim to execute_review_pipeline.py",
    )
    return p.parse_args(list(argv) if argv is not None else None)


def main() -> int:
    args = parse_args()
    if not PIPELINE_SCRIPT.exists():
        print(f"[error] pipeline entrypoint not found: {PIPELINE_SCRIPT}", file=sys.stderr)
        return 2
    if shutil.which("docker") is None:
        print("[warn] docker not on PATH — execution stage will fail in prepare", file=sys.stderr)
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
