from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from .fs import ensure_dir, write_text


@dataclass(frozen=True)
class CommandResult:
    cmd: List[str]
    cwd: str
    returncode: int
    stdout: str
    stderr: str
    duration_sec: float


def _is_verbose() -> bool:
    v = (os.getenv("CODE_EVAL_VERBOSE") or "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


def _tail(text: str, n: int = 2000) -> str:
    s = text or ""
    if len(s) <= n:
        return s
    return s[-n:]


def run_command(
    cmd: List[str],
    cwd: str,
    timeout_sec: int = 3600,
    env: Dict[str, str] | None = None,
) -> CommandResult:
    start = time.time()
    if _is_verbose():
        try:
            print(f"[code_evaluation][exec] cwd={cwd} timeout_sec={timeout_sec} cmd={' '.join(cmd)}", flush=True)
        except Exception:
            pass
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            env=env or os.environ.copy(),
            shell=False,
            check=False,
        )
        rc = proc.returncode
        out = proc.stdout or ""
        err = proc.stderr or ""
    except Exception as e:
        # Never crash the workflow due to missing executables (WinError 2), permission issues, etc.
        rc = 127
        out = ""
        err = f"{type(e).__name__}: {e}"
    dur = time.time() - start
    if _is_verbose():
        try:
            print(f"[code_evaluation][exec_done] rc={rc} sec={dur:.3f}", flush=True)
            if rc != 0:
                st = _tail(err or "", 2000).strip()
                if st:
                    print(f"[code_evaluation][stderr_tail]\n{st}\n", flush=True)
        except Exception:
            pass
    return CommandResult(
        cmd=cmd,
        cwd=cwd,
        returncode=rc,
        stdout=out,
        stderr=err,
        duration_sec=dur,
    )


def persist_command_result(
    result: CommandResult,
    logs_dir: str | Path,
    prefix: str,
) -> None:
    logs = ensure_dir(logs_dir)
    cmd_path = logs / f"{prefix}_command.txt"
    out_path = logs / f"{prefix}_stdout.log"
    err_path = logs / f"{prefix}_stderr.log"
    write_text(cmd_path, f"cwd: {result.cwd}\ncmd: {' '.join(result.cmd)}\nrc: {result.returncode}\nsec: {result.duration_sec:.3f}\n")
    write_text(out_path, result.stdout)
    write_text(err_path, result.stderr)
    if _is_verbose():
        try:
            print(
                f"[code_evaluation][logs] command={cmd_path} stdout={out_path} stderr={err_path}",
                flush=True,
            )
        except Exception:
            pass


