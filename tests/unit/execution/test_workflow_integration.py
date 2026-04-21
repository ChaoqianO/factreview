"""Integration smoke tests for the packaged FactReview layout."""

from __future__ import annotations


def test_workflow_importable():
    from execution.graph import CodeEvalOrchestrator

    assert callable(CodeEvalOrchestrator)


def test_all_nodes_importable():
    from execution.nodes.finalize import finalize_node
    from execution.nodes.fix import fix_node
    from execution.nodes.judge import judge_node
    from execution.nodes.plan import plan_node
    from execution.nodes.prepare import prepare_node
    from execution.nodes.run import run_node

    for fn in [prepare_node, plan_node, run_node, judge_node, fix_node, finalize_node]:
        assert callable(fn)


def test_tools_importable():
    from execution.tools.alignment import run_alignment
    from execution.tools.baseline_checks import Baseline
    from execution.tools.metrics import compute_check
    from positioning.bibtex import lookup_bibtex
    from positioning.refcheck import check_references

    assert callable(lookup_bibtex)
    assert callable(check_references)
    assert callable(run_alignment)
    assert callable(compute_check)
    assert Baseline(raw={}).checks == []


def test_orchestrator_accepts_new_flags():
    """The orchestrator must accept enable_refcheck and enable_bibtex."""
    from execution.graph import CodeEvalOrchestrator

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
