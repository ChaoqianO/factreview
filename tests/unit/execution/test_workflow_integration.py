"""Integration smoke tests: verify that all modules and workflow can be imported
without path/import errors after the restructuring."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_workflow_importable():
    from src.workflow import CodeEvalOrchestrator
    assert callable(CodeEvalOrchestrator)


def test_all_nodes_importable():
    from src.nodes.prepare import prepare_node
    from src.nodes.plan import plan_node
    from src.nodes.run import run_node
    from src.nodes.judge import judge_node
    from src.nodes.fix import fix_node
    from src.nodes.finalize import finalize_node
    for fn in [prepare_node, plan_node, run_node, judge_node, fix_node, finalize_node]:
        assert callable(fn)


def test_tools_importable():
    from src.tools.bibtex import lookup_bibtex, title_similarity
    from src.tools.refcheck import check_references
    from src.tools.baseline import Baseline
    from src.tools.alignment import run_alignment
    from src.tools.metrics import compute_check
    assert callable(lookup_bibtex)
    assert callable(check_references)


def test_orchestrator_accepts_new_flags():
    """The orchestrator must accept enable_refcheck and enable_bibtex."""
    from src.workflow import CodeEvalOrchestrator
    o = CodeEvalOrchestrator(
        run_root="/tmp/test_run",
        enable_refcheck=True,
        enable_bibtex=True,
    )
    assert o.enable_refcheck is True
    assert o.enable_bibtex is True


def test_refchecker_package_lazy():
    """refchecker package loads without triggering heavy deps at import time."""
    import refchecker
    assert refchecker.__version__
    # Accessing ArxivReferenceChecker would trigger heavy imports; skip that.
