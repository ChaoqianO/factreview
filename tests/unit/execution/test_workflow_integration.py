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
    """The orchestrator must accept optional integration flags."""
    from execution.graph import CodeEvalOrchestrator

    o = CodeEvalOrchestrator(
        run_root="/tmp/test_run",
        enable_refcheck=True,
        enable_bibtex=True,
        paper_extracted_dir="/tmp/extracted",
        run_dir="/tmp/run",
    )
    assert o.enable_refcheck is True
    assert o.enable_bibtex is True
    assert o.paper_extracted_dir == "/tmp/extracted"
    assert o.run_dir == "/tmp/run"


def test_run_layout_uses_single_run_folder():
    from pathlib import Path

    from util.run_layout import build_run_dir, slugify_run_key

    assert slugify_run_key("CompGCN Paper") == "compgcn_paper"
    expected = Path("/tmp/runs").resolve() / "compgcn_paper_2026-04-25_120000"
    assert build_run_dir("/tmp/runs", "CompGCN Paper", "2026-04-25_120000") == expected


def test_configured_baseline_uses_slugified_key(tmp_path, monkeypatch):
    from execution.nodes import prepare

    baseline_dir = tmp_path / "configs" / "baselines" / "compgcn_paper"
    baseline_dir.mkdir(parents=True)
    monkeypatch.setattr(prepare, "_project_root", lambda: tmp_path)
    monkeypatch.setattr(prepare, "_repo_root", lambda: tmp_path / "src")

    assert prepare._configured_baseline_dir("CompGCN Paper") == baseline_dir.resolve()


def test_fixed_execution_run_dir_reset_removes_stale_outputs(tmp_path):
    from execution.stage_runner import _reset_fixed_execution_run_dir

    stage_root = tmp_path / "stages" / "execution"
    execution_run_dir = stage_root / "run"
    stale_metric = execution_run_dir / "artifacts" / "metrics" / "old.json"
    stale_metric.parent.mkdir(parents=True)
    stale_metric.write_text("{}", encoding="utf-8")
    execution_json = stage_root / "execution.json"
    execution_json.write_text("{}", encoding="utf-8")

    _reset_fixed_execution_run_dir(stage_root=stage_root, execution_run_dir=execution_run_dir)

    assert execution_run_dir.exists()
    assert not stale_metric.exists()
    assert execution_json.exists()


def test_find_latest_code_eval_run_uses_slugified_key(tmp_path):
    from synthesis.integration.code_eval_compare import find_latest_code_eval_run

    run_dir = tmp_path / "runs" / "compgcn_paper_2026-04-25_120000"
    run_dir.mkdir(parents=True)

    assert find_latest_code_eval_run(tmp_path, "CompGCN Paper") == run_dir


def test_paper_image_tag_uses_slugified_key():
    from execution.tools.docker import _paper_image_tag

    image = _paper_image_tag(cfg={}, paper_key="CompGCN Paper", payload="same")

    assert image.startswith("code-eval-paper:compgcn_paper-")
    assert " " not in image


def test_refchecker_package_lazy():
    """refchecker package loads without triggering heavy deps at import time."""
    import refchecker

    assert refchecker.__version__
    # Accessing ArxivReferenceChecker would trigger heavy imports; skip that.
