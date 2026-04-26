"""Review report sub-stage.

Reads the agent-runner's final report artifacts (markdown + audit) from the
parse-stage snapshot, normalises image paths, optionally appends a
``RefChecker`` summary, re-renders the PDF, and writes the canonical review
output to ``stages/review/report/``.

A clean copy of the markdown (without the refcheck section) is also written to
``final_review_clean.md`` so the teaser sub-stage can build its prompt from a
report that has not been polluted by reference-check warnings.
"""

from __future__ import annotations

import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.config import get_settings  # noqa: E402
from common.pipeline_context import (  # noqa: E402
    bootstrap_bridge_state,
    ensure_full_pipeline_context,
    load_bridge_state,
    load_job_state_snapshot,
    load_stage_assets_snapshot,
    read_json_file,
    resolve_artifact_path,
    write_json_file,
)
from fact_generation.refcheck.refcheck import format_reference_check_markdown  # noqa: E402
from review.report.pdf_renderer import build_review_report_pdf  # noqa: E402


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _copy_if_exists(src: Path | None, dst: Path) -> bool:
    if src is None or not src.exists() or not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _render_review_pdf(*, markdown_path: Path, pdf_path: Path, workspace_title: str, source_pdf_name: str) -> bool:
    if not markdown_path.exists() or not markdown_path.is_file():
        return False
    md_text = markdown_path.read_text(encoding="utf-8", errors="ignore")
    overview_path = markdown_path.parent / "overview_figure.jpg"
    if overview_path.exists() and overview_path.is_file():
        md_text = md_text.replace("./overview_figure.jpg", str(overview_path.resolve()))
    try:
        settings = get_settings()
        pdf_bytes = build_review_report_pdf(
            workspace_title=workspace_title,
            source_pdf_name=source_pdf_name,
            run_id=markdown_path.parents[3].name,
            status="completed",
            decision=None,
            estimated_cost=0,
            actual_cost=None,
            exported_at=datetime.now(UTC),
            meta_review={},
            reviewers=[],
            raw_output=None,
            final_report_markdown=md_text,
            source_pdf_bytes=None,
            source_annotations=[],
            review_display_id=None,
            owner_email=None,
            token_usage={},
            agent_model=str(settings.agent_model or "").strip() or "factreview-review",
        )
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(pdf_bytes)
        return True
    except Exception:
        return False


def _absolutize_markdown_image_refs(*, markdown_path: Path, source_base_dirs: list[Path]) -> None:
    if not markdown_path.exists() or not markdown_path.is_file():
        return
    try:
        text = markdown_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return

    def _replace(match: re.Match[str]) -> str:
        whole = match.group(0) or ""
        src = (match.group(1) or "").strip()
        if not src:
            return whole
        src_path = Path(src).expanduser()
        if src_path.is_absolute():
            return whole
        for base_dir in source_base_dirs:
            try:
                resolved = (base_dir / src).resolve()
            except Exception:
                continue
            if resolved.exists() and resolved.is_file():
                target = resolved
                if resolved.name.lower() == "overview_figure.jpg":
                    alias = resolved.with_name("technical_positioning_image.jpg")
                    try:
                        if not alias.exists() or not alias.is_file():
                            shutil.copy2(resolved, alias)
                        target = alias
                    except Exception:
                        target = resolved
                return whole.replace(src, str(target))
        return whole

    updated = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", _replace, text)
    if updated != text:
        markdown_path.write_text(updated, encoding="utf-8")


def _load_reference_check_payload(run_dir: Path) -> dict[str, Any]:
    return read_json_file(run_dir / "stages" / "fact_generation" / "refcheck" / "reference_check.json")


def _append_reference_check_section(
    *,
    markdown_path: Path,
    reference_check: dict[str, Any],
    max_issues: int,
) -> str:
    if not reference_check.get("enabled"):
        return ""
    section = format_reference_check_markdown(reference_check, max_issues=max_issues).strip()
    if not section:
        return ""
    current = _read_text(markdown_path).rstrip()
    markdown_path.write_text(current + "\n\n" + section + "\n", encoding="utf-8")
    return section + "\n"


def report_stage_dir(run_dir: Path) -> Path:
    return run_dir / "stages" / "review" / "report"


def run_report_stage(
    *,
    repo_root: Path,
    run_dir: Path,
    paper_pdf: Path | None = None,
    paper_key: str = "",
    reuse_job_id: str = "",
) -> dict[str, Any]:
    ensure_full_pipeline_context(run_dir=run_dir, allow_standalone=True, stage="report")
    bridge = load_bridge_state(run_dir)
    if bridge is None:
        bridge = bootstrap_bridge_state(
            repo_root=repo_root,
            run_dir=run_dir,
            paper_pdf=paper_pdf,
            paper_key=paper_key,
            reuse_job_id=reuse_job_id,
        )

    job_state = load_job_state_snapshot(run_dir) or read_json_file(bridge.job_json_path)
    stage_assets = load_stage_assets_snapshot(run_dir)
    artifacts = job_state.get("artifacts") if isinstance(job_state.get("artifacts"), dict) else {}
    metadata = job_state.get("metadata") if isinstance(job_state.get("metadata"), dict) else {}
    final_md_raw = str(artifacts.get("final_markdown_path") or "").strip()
    final_audit_raw = str(artifacts.get("final_report_audit_path") or "").strip()
    final_pdf_raw = str(artifacts.get("report_pdf_path") or "").strip()

    final_md_snapshot_raw = str(stage_assets.get("final_markdown_snapshot_path") or "").strip()
    final_pdf_snapshot_raw = str(stage_assets.get("report_pdf_snapshot_path") or "").strip()
    final_md_snapshot = Path(final_md_snapshot_raw).resolve() if final_md_snapshot_raw else None
    final_pdf_snapshot = Path(final_pdf_snapshot_raw).resolve() if final_pdf_snapshot_raw else None
    final_md = (
        final_md_snapshot
        if (final_md_snapshot is not None and final_md_snapshot.exists())
        else resolve_artifact_path(repo_root, final_md_raw)
    )
    final_audit = resolve_artifact_path(repo_root, final_audit_raw) if final_audit_raw else None
    final_pdf = (
        final_pdf_snapshot
        if (final_pdf_snapshot is not None and final_pdf_snapshot.exists())
        else resolve_artifact_path(repo_root, final_pdf_raw)
    )

    out_dir = report_stage_dir(run_dir)
    review_json = out_dir / "final_review.json"
    review_md = out_dir / "final_review.md"
    review_md_clean = out_dir / "final_review_clean.md"
    review_audit = out_dir / "final_review_audit.json"
    pdf_path = out_dir / "final_review.pdf"

    md_ok = _copy_if_exists(final_md, review_md)
    audit_ok = _copy_if_exists(final_audit, review_audit)
    pdf_ok = _copy_if_exists(final_pdf, pdf_path)

    settings = get_settings()
    reference_check_payload = _load_reference_check_payload(run_dir)
    reference_check_markdown = ""
    reference_check_appended = False

    if md_ok:
        if final_md is not None and final_md.exists():
            _absolutize_markdown_image_refs(
                markdown_path=review_md,
                source_base_dirs=[final_md.parent, bridge.job_dir],
            )
        # Always snapshot the clean (no-refcheck) version for the teaser sub-stage.
        shutil.copy2(review_md, review_md_clean)

        if reference_check_payload.get("enabled"):
            reference_check_markdown = _append_reference_check_section(
                markdown_path=review_md,
                reference_check=reference_check_payload,
                max_issues=max(1, int(settings.reference_check_report_max_issues)),
            )
            reference_check_appended = bool(reference_check_markdown.strip())

        source_name = bridge.paper_pdf.name if bridge.paper_pdf else "paper.pdf"
        rendered_pdf_ok = _render_review_pdf(
            markdown_path=review_md,
            pdf_path=pdf_path,
            workspace_title=bridge.paper_key,
            source_pdf_name=source_name,
        )
        if reference_check_appended:
            pdf_ok = rendered_pdf_ok
            if not pdf_ok and pdf_path.exists():
                try:
                    pdf_path.unlink()
                except OSError:
                    pass
        else:
            pdf_ok = rendered_pdf_ok or pdf_ok

    execution_payload = read_json_file(run_dir / "stages" / "fact_generation" / "execution" / "execution.json")

    write_json_file(
        review_json,
        {
            "paper_key": bridge.paper_key,
            "run_id": run_dir.name,
            "job_id": bridge.job_id,
            "status": bridge.own_payload.get("status"),
            "message": bridge.own_payload.get("message"),
            "error": bridge.own_payload.get("error"),
            "usage": bridge.own_payload.get("usage") or {},
            "metadata": metadata,
            "execution": execution_payload,
            "reference_check": reference_check_payload,
            "reference_check_markdown": reference_check_markdown,
            "final_markdown": _read_text(review_md) if md_ok else "",
            "final_audit_path": str(final_audit_raw) if (final_audit is not None and final_audit.exists()) else "",
            "final_audit": read_json_file(review_audit) if audit_ok else {},
            "final_markdown_path": final_md_raw if (final_md is not None and final_md.exists()) else "",
            "final_pdf_path": final_pdf_raw if (final_pdf is not None and final_pdf.exists()) else "",
        },
    )

    result: dict[str, Any] = {
        "status": "ok" if (final_md is not None and final_md.exists()) else "failed",
        "output_json": str(review_json),
        "output_md": str(review_md),
        "output_md_clean": str(review_md_clean) if review_md_clean.exists() else "",
    }
    if audit_ok:
        result["output_audit_json"] = str(review_audit)
    if pdf_ok:
        result["output_pdf"] = str(pdf_path)
    return result


if __name__ == "__main__":
    raise SystemExit("Internal stage module. Use scripts/execute_review_pipeline.py.")
