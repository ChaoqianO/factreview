from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .fs import read_text
from .llm import llm_json, resolve_llm_config


@dataclass(frozen=True)
class InferResult:
    tasks: List[Dict[str, Any]]
    evidence: Dict[str, Any]


def _read_optional(path: Path, max_chars: int = 12000) -> str:
    try:
        if not path.exists():
            return ""
        txt = path.read_text(encoding="utf-8", errors="ignore")
        if len(txt) > max_chars:
            return txt[:max_chars] + "\n...(truncated)\n"
        return txt
    except Exception:
        return ""


def _guess_entrypoints(repo_root: Path) -> List[str]:
    # Conservative: only look for common top-level scripts.
    cands = ["launcher.py", "run.py", "eval.py", "main.py", "app.py"]
    out: List[str] = []
    for c in cands:
        if (repo_root / c).exists():
            out.append(c)
    return out


def _extract_example_commands_from_readme(readme_text: str) -> List[str]:
    """
    Extract a few likely shell commands from README code fences.
    Keep it best-effort and small; this is only used as hinting.
    """
    txt = readme_text or ""
    cmds: List[str] = []
    # Grab fenced blocks ```bash ... ```
    for m in re.finditer(r"```(?:bash|sh|shell)\s+([\s\S]*?)```", txt, flags=re.IGNORECASE):
        block = (m.group(1) or "").strip()
        for line in block.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            cmds.append(s)
            if len(cmds) >= 6:
                return cmds
    return cmds


def infer_tasks_heuristic(repo_root: str, mode: str = "smoke") -> InferResult:
    root = Path(repo_root)
    readme = _read_optional(root / "README.md")
    req = _read_optional(root / "requirements.txt", max_chars=8000)
    entrypoints = _guess_entrypoints(root)
    examples = _extract_example_commands_from_readme(readme)

    # Default install step. We keep it lightweight and let the framework's prepare/fix deal with stdlib-in-req.
    tasks: List[Dict[str, Any]] = [
        {
            "id": "install_deps",
            "cwd": "{paper_root}",
            "cmd": ["python", "-m", "pip", "install", "-r", "{paper_root}/requirements.txt"],
            "timeout_sec": 3600,
            "use_conda": True,
        }
    ]

    # Smoke: check --help for a chosen entrypoint.
    ep = entrypoints[0] if entrypoints else ""
    if not ep:
        # last resort: do nothing but print cwd (still validates the runner)
        tasks.append(
            {
                "id": "repo_smoke",
                "cwd": "{paper_root}",
                "cmd": ["python", "-c", "import os; print('cwd=', os.getcwd()); print('ok')"],
                "timeout_sec": 60,
                "use_conda": True,
            }
        )
    else:
        tasks.append(
            {
                "id": "repo_smoke",
                "cwd": "{paper_root}",
                "cmd": ["python", ep, "--help"],
                "timeout_sec": 600,
                "use_conda": True,
            }
        )
        if (root / "eval.py").exists() and ep != "eval.py":
            tasks.append(
                {
                    "id": "eval_smoke",
                    "cwd": "{paper_root}",
                    "cmd": ["python", "eval.py", "--help"],
                    "timeout_sec": 600,
                    "use_conda": True,
                }
            )

    # Full: propose heavier commands but disable them by default.
    if mode == "full":
        if examples:
            tasks.append(
                {
                    "id": "readme_example_1",
                    "enabled": False,
                    "cwd": "{paper_root}",
                    "cmd": ["cmd", "/c", examples[0]] if os.name == "nt" else ["bash", "-lc", examples[0]],
                    "timeout_sec": 3600,
                    "use_conda": True,
                    "artifact_paths": ["results/**", "logs/**"],
                }
            )

    evidence = {
        "mode": mode,
        "entrypoints": entrypoints,
        "readme_has_content": bool(readme.strip()),
        "requirements_present": bool(req.strip()),
        "readme_example_cmds": examples,
    }
    return InferResult(tasks=tasks, evidence=evidence)


def infer_tasks_llm(
    repo_root: str,
    mode: str,
    cfg_provider: str,
    cfg_model: str,
    cfg_base_url: str,
    paper_md_excerpt: str = "",
) -> InferResult:
    """
    LLM-assisted task inference. Must be safe by design:
    - Prefer smoke tasks.
    - Heavy tasks must be generated with enabled=false unless explicitly requested by user.
    - Only wrapper commands (no source edits).
    """
    root = Path(repo_root)
    readme = _read_optional(root / "README.md", max_chars=14000)
    req = _read_optional(root / "requirements.txt", max_chars=8000)
    entrypoints = _guess_entrypoints(root)

    # Keep prompt small but informative. The goal is to produce tasks that actually reflect the repo's README
    # (download/preprocess/train/eval) while staying safe by default.
    prompt = {
        "goal": "Generate tasks.yaml for running/evaluating this repo in a reproducible way.",
        "mode": mode,
        "platform": {"os": os.name},
        "repo_root": str(root),
        "files_top_level": [p.name for p in sorted(root.iterdir())][:200],
        "entrypoints_detected": entrypoints,
        "readme_md_excerpt": readme,
        "paper_mineru_md_excerpt": (paper_md_excerpt or ""),
        "requirements_txt_excerpt": req,
        "schema": {
            "tasks": [
                {
                    "id": "string",
                    "enabled": True,
                    "cwd": "{paper_root}",
                    "cmd": ["python", "run.py", "--help"],
                    "timeout_sec": 600,
                    "use_conda": True,
                    "artifact_paths": ["results/**"],
                }
            ],
            "notes": ["string"],
        },
        "constraints": [
            "Return JSON only, no prose outside JSON.",
            "You MUST derive commands from README when possible; do not output generic placeholder tasks if the README provides concrete steps.",
            "Prefer: install deps -> (optional) download/preprocess -> run/eval -> collect artifacts.",
            "Include at least one smoke task (help/print/version) as an early, fast validation step.",
            "If proposing any heavy task (downloads dataset, trains model), set enabled=false unless mode=='full'.",
            "Do not propose source code edits.",
            "Commands must be compatible with shell=False: use cmd arrays; if on Windows and you need a shell, use ['cmd','/c', '<command>'].",
            "For multi-step shell pipelines, use ['bash','-lc','...'] (Linux) or ['cmd','/c','...'] (Windows).",
            "Use {paper_root} in cwd/cmd paths instead of hardcoding absolute paths.",
        ],
    }
    system = "You are a senior engineer generating a safe, reproducible tasks.yaml for a research repo."
    llm_cfg = resolve_llm_config(cfg_provider, cfg_model, cfg_base_url)
    resp = llm_json(prompt=json.dumps(prompt, ensure_ascii=False), system=system, cfg=llm_cfg)
    if not isinstance(resp, dict) or resp.get("status") == "error":
        # fallback to heuristics if LLM fails
        hr = infer_tasks_heuristic(repo_root, mode=mode)
        ev = dict(hr.evidence)
        ev["llm_error"] = resp
        return InferResult(tasks=hr.tasks, evidence=ev)

    tasks = resp.get("tasks")
    if not isinstance(tasks, list):
        hr = infer_tasks_heuristic(repo_root, mode=mode)
        ev = dict(hr.evidence)
        ev["llm_bad_shape"] = resp
        return InferResult(tasks=hr.tasks, evidence=ev)

    cleaned: List[Dict[str, Any]] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        cmd = t.get("cmd")
        if not isinstance(tid, str) or not isinstance(cmd, list) or not all(isinstance(x, str) for x in cmd):
            continue
        cleaned.append(t)

    evidence = {"mode": mode, "llm_used": True, "llm_provider": llm_cfg.provider, "llm_model": llm_cfg.model, "raw": resp}
    return InferResult(tasks=cleaned or infer_tasks_heuristic(repo_root, mode=mode).tasks, evidence=evidence)




