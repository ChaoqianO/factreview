from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure the project root (code_evaluation/) is importable when running this script directly.
# scripts/ is at repo root; code_evaluation/ is a sibling directory.
_CODE_EVAL = Path(__file__).resolve().parents[1] / "code_evaluation"
if str(_CODE_EVAL) not in sys.path:
    sys.path.insert(0, str(_CODE_EVAL))

from src.nodes.finalize import finalize_node  # noqa: E402
from src.nodes.fix import fix_node  # noqa: E402
from src.nodes.judge import judge_node  # noqa: E402
from src.nodes.prepare import prepare_node  # noqa: E402
from src.nodes.run import run_node  # noqa: E402

State = Dict[str, Any]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", errors="ignore")


def _build_initial_state(args: argparse.Namespace) -> State:
    return {
        "status": "running",
        "attempt": 0,
        "max_attempts": int(args.max_attempts),
        "config": {
            "paper_root": args.paper_root or "",
            "paper_pdf": args.paper_pdf or "",
            "paper_key": args.paper_key or "",
            "tasks_path": args.tasks or "",
            "baseline_path": args.baseline or "",
            "local_source_path": args.local_source or "",
            "run_root": args.run_root or str(_CODE_EVAL / "run"),
            "no_llm": bool(args.no_llm),
            "no_pdf_extract": bool(args.no_pdf_extract),
            "llm_provider": args.llm_provider or "",
            "llm_model": args.llm_model or "",
            "llm_base_url": args.llm_base_url or "",
            "dry_run": bool(args.dry_run),
            "auto_tasks": bool(args.auto_tasks),
            "auto_tasks_mode": args.auto_tasks_mode or "smoke",
            "auto_tasks_force": bool(args.auto_tasks_force),
        },
        "history": [],
    }


def _state_path_from_state(st: State) -> Path:
    run = st.get("run") or {}
    if not isinstance(run, dict):
        run = {}
    run_dir = Path(run.get("dir") or "")
    if not run_dir:
        raise SystemExit("state has no run.dir; did prepare run?")
    return run_dir / "state.json"


def _print_summary(st: State) -> None:
    run = st.get("run") or {}
    cfg = st.get("config") or {}
    print(
        json.dumps(
            {
                "status": st.get("status"),
                "attempt": st.get("attempt"),
                "paper_key": cfg.get("paper_key"),
                "paper_root": cfg.get("paper_root"),
                "paper_pdf": cfg.get("paper_pdf"),
                "tasks_path": cfg.get("tasks_path"),
                "baseline_path": cfg.get("baseline_path"),
                "run_id": run.get("id"),
                "run_dir": run.get("dir"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Step through code_evaluation nodes using a persisted state.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Run prepare node and persist state.json into run_dir")
    p_init.add_argument("--paper-pdf", default="")
    p_init.add_argument("--paper-key", default="")
    p_init.add_argument("--paper-root", default="")
    p_init.add_argument("--local-source", default="")
    p_init.add_argument("--tasks", default="")
    p_init.add_argument("--baseline", default="")
    p_init.add_argument("--run-root", default="")
    p_init.add_argument("--max-attempts", type=int, default=5)
    p_init.add_argument("--no-llm", action="store_true")
    p_init.add_argument("--llm-provider", default="")
    p_init.add_argument("--llm-model", default="")
    p_init.add_argument("--llm-base-url", default="")
    p_init.add_argument("--no-pdf-extract", action="store_true")
    p_init.add_argument("--dry-run", action="store_true")
    p_init.add_argument("--auto-tasks", action="store_true")
    p_init.add_argument("--auto-tasks-mode", choices=["smoke", "full"], default="smoke")
    p_init.add_argument("--auto-tasks-force", action="store_true")

    p_step = sub.add_parser("step", help="Load a state.json and run one node, then overwrite state.json")
    p_step.add_argument("--state", required=True, help="Path to run_dir/state.json")
    p_step.add_argument("--node", choices=["run", "judge", "fix", "finalize"], required=True)

    args = ap.parse_args()

    if args.cmd == "init":
        st = _build_initial_state(args)
        st = prepare_node(st)
        # If prepare created a run dir, persist state there even on failure.
        try:
            sp = _state_path_from_state(st)
            _write_json(sp, st)
            print(f"[node_stepper] state_written={sp}")
        except Exception as e:
            print(f"[node_stepper] state_not_written: {type(e).__name__}: {e}")
        _print_summary(st)
        return 0 if st.get("status") != "failed" else 1

    # step mode
    st_path = Path(args.state)
    st = _read_json(st_path)
    if not isinstance(st, dict):
        raise SystemExit("state.json is not a JSON object")

    if args.node == "run":
        st = run_node(st)
    elif args.node == "judge":
        st = judge_node(st)
    elif args.node == "fix":
        st = fix_node(st)
    elif args.node == "finalize":
        st = finalize_node(st)
    else:
        raise SystemExit("unknown node")

    _write_json(st_path, st)
    print(f"[node_stepper] state_updated={st_path}")
    _print_summary(st)
    return 0 if st.get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())


