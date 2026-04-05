from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure imports like `from src...` work when executing this script directly.
# scripts/ is at repo root; code_evaluation/ is a sibling directory.
_CODE_EVAL = Path(__file__).resolve().parents[1] / "code_evaluation"
if str(_CODE_EVAL) not in sys.path:
    sys.path.insert(0, str(_CODE_EVAL))

from src.nodes.finalize import finalize_node
from src.nodes.fix import fix_node
from src.nodes.judge import judge_node
from src.nodes.prepare import prepare_node
from src.nodes.run import run_node


def _pp(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _print_step(name: str, state: Dict[str, Any]) -> None:
    cfg = state.get("config") or {}
    run = state.get("run") or {}
    print(f"\n=== {name} ===")
    print(f"status={state.get('status')} attempt={state.get('attempt')} run_id={(run.get('id') or '')}")
    if run.get("dir"):
        print(f"run_dir={run.get('dir')}")
    if cfg.get("paper_key"):
        print(f"paper_key={cfg.get('paper_key')}")
    if cfg.get("paper_pdf"):
        print(f"paper_pdf={cfg.get('paper_pdf')}")
    if cfg.get("paper_pdf_extracted_md"):
        print(f"paper_pdf_extracted_md={cfg.get('paper_pdf_extracted_md')}")
    if cfg.get("tasks_path"):
        print(f"tasks_path={cfg.get('tasks_path')}")
    if cfg.get("baseline_path"):
        print(f"baseline_path={cfg.get('baseline_path')}")
    if state.get("run_result"):
        print("run_result=" + _pp(state.get("run_result")))
    if state.get("judge"):
        print("judge=" + _pp(state.get("judge")))


def main() -> int:
    ap = argparse.ArgumentParser(description="Node-by-node debug runner for code_evaluation")
    ap.add_argument("--paper-pdf", required=True)
    ap.add_argument("--paper-key", default="")
    ap.add_argument("--run-root", default=str(_CODE_EVAL / "run"))
    ap.add_argument("--no-pdf-extract", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="Run tasks in dry-run mode (no docker/paper execution).")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--llm-judge-mode", default="off", choices=["off", "assist", "verdict"])
    ap.add_argument("--docker-strategy", default="", help="Docker strategy (only 'paper_image' is supported). Empty uses default.")
    args = ap.parse_args()

    state: Dict[str, Any] = {
        "status": "running",
        "attempt": 0,
        "max_attempts": 2,
        "config": {
            "paper_pdf": args.paper_pdf,
            "paper_key": args.paper_key,
            "paper_root": "",
            "tasks_path": "",
            "baseline_path": "",
            "run_root": args.run_root,
            "no_pdf_extract": bool(args.no_pdf_extract),
            "dry_run": bool(args.dry_run),
            "no_llm": bool(args.no_llm),
            "llm_judge_mode": str(args.llm_judge_mode),
        },
        "history": [],
    }
    if args.docker_strategy:
        if args.docker_strategy != "paper_image":
            raise SystemExit("Only docker strategy supported is: paper_image")
        state["config"]["docker_strategy"] = args.docker_strategy

    # 1) prepare
    st = prepare_node(state)
    _print_step("prepare", st)
    if st.get("status") == "failed":
        print("\n[debug_nodes] prepare failed. Inspect issues/logs in the printed run_dir.")
        return 1

    # 2) run
    st = run_node(st)
    _print_step("run", st)
    if st.get("status") == "failed":
        print("\n[debug_nodes] run failed. Next you would normally enter fix loop.")

    # 3) judge (usually expects artifacts; in dry-run this is mostly schema/path validation)
    st = judge_node(st)
    _print_step("judge", st)

    # 4) finalize
    st = finalize_node(st)
    _print_step("finalize", st)

    # 5) simulate a fix node call (safe mode: no docker, no llm) so you can validate fix_node wiring
    st2 = copy.deepcopy(st)
    st2["status"] = "failed"
    st2["run_result"] = {
        "success": False,
        "failed_task": "repo_smoke",
        "stderr_tail": "ModuleNotFoundError: No module named 'torch_scatter'",
    }
    cfg2 = st2.get("config") or {}
    cfg2["docker_enabled"] = False
    cfg2["no_llm"] = True
    st2["config"] = cfg2
    st2 = fix_node(st2)
    _print_step("fix(simulated)", st2)

    print("\n[debug_nodes] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


