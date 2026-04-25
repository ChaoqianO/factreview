from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ingestion.runtime_bridge import (
    bootstrap_bridge_state,
    ensure_full_pipeline_context,
    load_job_state_snapshot,
    load_stage_assets_snapshot,
    load_bridge_state,
    read_json_file,
    resolve_artifact_path,
    write_json_file,
)
from common.runtime_shared.config import get_settings
from synthesis.runtime.report.review_report_pdf import build_review_report_pdf
from synthesis.runtime.report.teaser_figure import _env_true, generate_teaser_figure


@dataclass(frozen=True)
class MineruFigureCandidate:
    image_path: Path
    caption: str
    figure_number: int | None
    line_index: int
    source_md: Path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _copy_if_exists(src: Path | None, dst: Path) -> bool:
    if src is None:
        return False
    if not src.exists() or not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _sync_overview_image_for_markdown(*, source_md: Path, target_dir: Path) -> bool:
    try:
        text = source_md.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", text)
    if not match:
        return False
    src_ref = str(match.group(1) or "").strip()
    if not src_ref:
        return False
    src_path = (source_md.parent / src_ref).resolve() if not Path(src_ref).is_absolute() else Path(src_ref).resolve()
    if not src_path.exists() or not src_path.is_file():
        return False
    dst_path = target_dir / "overview_figure.jpg"
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    if src_path != dst_path:
        shutil.copy2(src_path, dst_path)
    return True


def _rewrite_image_placeholders(markdown_path: Path) -> None:
    if not markdown_path.exists() or not markdown_path.is_file():
        return
    try:
        text = markdown_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    updated = re.sub(r"\[Image:\s*image\s*\]", "![](./overview_figure.jpg)", text, flags=re.IGNORECASE)
    # Normalize any markdown image reference (including absolute paths from upstream final_report.md)
    # to the local synthesis artifact so report and teaser share the same overview file.
    updated = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", "![](./overview_figure.jpg)", updated)
    if updated != text:
        markdown_path.write_text(updated, encoding="utf-8")


def _render_synthesis_pdf(*, markdown_path: Path, pdf_path: Path, workspace_title: str, source_pdf_name: str) -> bool:
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
            run_id=markdown_path.parent.parent.name,
            status="completed",
            decision=None,
            estimated_cost=0,
            actual_cost=None,
            exported_at=datetime.now(timezone.utc),
            meta_review={},
            reviewers=[],
            raw_output=None,
            final_report_markdown=md_text,
            source_pdf_bytes=None,
            source_annotations=[],
            review_display_id=None,
            owner_email=None,
            token_usage={},
            agent_model=str(settings.agent_model or "").strip() or "factreview-synthesis",
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
                        if (not alias.exists()) or (not alias.is_file()):
                            shutil.copy2(resolved, alias)
                        target = alias
                    except Exception:
                        target = resolved
                return whole.replace(src, str(target))
        return whole

    updated = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", _replace, text)
    if updated != text:
        markdown_path.write_text(updated, encoding="utf-8")


def _collect_mineru_figure_candidates(*, repo_root: Path, paper_key: str) -> list[MineruFigureCandidate]:
    key = (paper_key or "").strip()
    mineru_md_candidates = [
        repo_root / "src" / "baseline" / key / "paper_extracted" / "paper.mineru.md",
        repo_root / "configs" / "baselines" / key / "paper_extracted" / "paper.mineru.md",
    ]
    image_re = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    caption_re = re.compile(r"^\s*(?:figure|fig\.)\s*(\d+)", re.IGNORECASE)
    candidates: list[MineruFigureCandidate] = []

    for mineru_md in mineru_md_candidates:
        if not mineru_md.exists() or not mineru_md.is_file():
            continue
        lines = mineru_md.read_text(encoding="utf-8", errors="ignore").splitlines()
        for idx, line in enumerate(lines):
            m = image_re.search(line or "")
            if not m:
                continue
            src = str(m.group(1) or "").strip()
            if not src:
                continue
            image_path = (mineru_md.parent / src).resolve() if not Path(src).is_absolute() else Path(src).resolve()
            if not image_path.exists() or not image_path.is_file():
                continue

            caption = ""
            figure_number: int | None = None
            # MinerU captions may appear before or after the image line.
            for j in range(max(0, idx - 8), min(idx + 10, len(lines))):
                if j == idx:
                    continue
                candidate = (lines[j] or "").strip()
                if not candidate:
                    continue
                cap_match = caption_re.match(candidate)
                if cap_match:
                    caption = candidate
                    try:
                        figure_number = int(cap_match.group(1))
                    except Exception:
                        figure_number = None
                    break

            candidates.append(
                MineruFigureCandidate(
                    image_path=image_path,
                    caption=caption,
                    figure_number=figure_number,
                    line_index=idx,
                    source_md=mineru_md,
                )
            )
    return candidates


def _select_overview_from_mineru_caption(*, repo_root: Path, paper_key: str) -> Path | None:
    candidates = _collect_mineru_figure_candidates(repo_root=repo_root, paper_key=paper_key)
    if not candidates:
        return None

    positive_keywords = (
        "overview",
        "architecture",
        "framework",
        "pipeline",
        "method",
        "model",
        "network architecture",
        "overall",
        "proposed",
        "illustration",
        "system",
    )
    negative_keywords = (
        "ablation",
        "result",
        "results",
        "accuracy",
        "error",
        "loss",
        "comparison",
        "hyperparameter",
        "training curve",
        "qualitative",
        "visualization",
        "attention map",
        "dataset",
    )

    def _score(candidate: MineruFigureCandidate) -> int:
        caption = (candidate.caption or "").strip().lower()
        score = 0

        # Stage 1: structure priors.
        if candidate.figure_number == 1:
            score += 260
        elif candidate.figure_number == 2:
            score += 140
        elif candidate.figure_number == 3:
            score += 70
        elif candidate.figure_number is not None:
            score += max(0, 45 - candidate.figure_number * 6)

        # Earlier figures are more likely to be architecture overview.
        score += max(0, 80 - min(candidate.line_index, 800) // 12)

        # Stage 2: semantic caption priors.
        if caption:
            for kw in positive_keywords:
                if kw in caption:
                    score += 95
            for kw in negative_keywords:
                if kw in caption:
                    score -= 110
            # Short "Figure X ..." captions with almost no semantics are weak.
            word_count = len(re.findall(r"[A-Za-z0-9]+", caption))
            if word_count <= 4:
                score -= 40
        else:
            # No caption metadata: still allow, but lower confidence.
            score -= 30
        return score

    ranked = sorted(
        candidates,
        key=lambda c: (
            _score(c),
            -1 * (c.figure_number if c.figure_number is not None else 10**6),
            -1 * c.line_index,
        ),
        reverse=True,
    )
    return ranked[0].image_path if ranked else None


def _ensure_overview_image_fallback(*, repo_root: Path, paper_key: str, target_dir: Path, allow_overwrite: bool) -> None:
    dst_path = target_dir / "overview_figure.jpg"
    if dst_path.exists() and dst_path.is_file() and not allow_overwrite:
        return
    key = (paper_key or "").strip()
    mineru_images_dirs = [
        repo_root / "src" / "baseline" / key / "paper_extracted" / "mineru_assets" / "images",
        repo_root / "configs" / "baselines" / key / "paper_extracted" / "mineru_assets" / "images",
    ]

    # Priority 1: select best candidate from MinerU caption scoring.
    caption_best = _select_overview_from_mineru_caption(repo_root=repo_root, paper_key=key)
    if caption_best is not None and caption_best.exists() and caption_best.is_file():
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(caption_best, dst_path)
        return

    # Priority 2: fallback to first extracted image (legacy extension-order behavior).
    for images_dir in mineru_images_dirs:
        if images_dir.exists() and images_dir.is_dir():
            for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                for p in sorted(images_dir.glob(ext)):
                    if p.exists() and p.is_file():
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(p, dst_path)
                        return


def run_synthesis_stage(
    *,
    repo_root: Path,
    run_dir: Path,
    paper_pdf: Path | None = None,
    paper_key: str = "",
    reuse_job_id: str = "",
) -> dict[str, Any]:
    ensure_full_pipeline_context(run_dir=run_dir, allow_standalone=True, stage="synthesis")
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
    latest_extraction_raw = str(artifacts.get("latest_output_md_path") or artifacts.get("latest_output_md") or "").strip()

    final_md_snapshot_raw = str(stage_assets.get("final_markdown_snapshot_path") or "").strip()
    final_pdf_snapshot_raw = str(stage_assets.get("report_pdf_snapshot_path") or "").strip()
    final_md_snapshot = Path(final_md_snapshot_raw).resolve() if final_md_snapshot_raw else None
    final_pdf_snapshot = Path(final_pdf_snapshot_raw).resolve() if final_pdf_snapshot_raw else None
    final_md = final_md_snapshot if (final_md_snapshot is not None and final_md_snapshot.exists()) else resolve_artifact_path(repo_root, final_md_raw)
    final_audit = resolve_artifact_path(repo_root, final_audit_raw) if final_audit_raw else None
    final_pdf = final_pdf_snapshot if (final_pdf_snapshot is not None and final_pdf_snapshot.exists()) else resolve_artifact_path(repo_root, final_pdf_raw)
    latest_extraction = resolve_artifact_path(repo_root, latest_extraction_raw) if latest_extraction_raw else None

    synthesis_dir = run_dir / "stages" / "synthesis"
    synthesis_json = synthesis_dir / "final_review.json"
    synthesis_md = synthesis_dir / "final_review.md"
    synthesis_audit = synthesis_dir / "final_review_audit.json"

    md_ok = _copy_if_exists(final_md, synthesis_md)
    audit_ok = _copy_if_exists(final_audit, synthesis_audit)
    pdf_path = synthesis_dir / "final_review.pdf"
    pdf_ok = _copy_if_exists(final_pdf, pdf_path)
    if md_ok:
        if final_md is not None and final_md.exists():
            _absolutize_markdown_image_refs(
                markdown_path=synthesis_md,
                source_base_dirs=[final_md.parent, bridge.job_dir],
            )
        # Keep markdown image references exactly as produced by runtime output.
        # Do not select/replace overview figures in synthesis stage.
        source_name = bridge.paper_pdf.name if bridge.paper_pdf else "paper.pdf"
        pdf_ok = _render_synthesis_pdf(
            markdown_path=synthesis_md,
            pdf_path=pdf_path,
            workspace_title=bridge.paper_key,
            source_pdf_name=source_name,
        ) or pdf_ok

    execution_payload = read_json_file(run_dir / "stages" / "execution" / "execution.json")

    write_json_file(
        synthesis_json,
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
            "final_markdown": _read_text(synthesis_md) if md_ok else "",
            "final_audit_path": str(final_audit_raw) if (final_audit is not None and final_audit.exists()) else "",
            "final_audit": read_json_file(synthesis_audit) if audit_ok else {},
            "final_markdown_path": final_md_raw if (final_md is not None and final_md.exists()) else "",
            "final_pdf_path": final_pdf_raw if (final_pdf is not None and final_pdf.exists()) else "",
        },
    )

    result: dict[str, Any] = {
        "status": "ok" if (final_md is not None and final_md.exists()) else "failed",
        "output_json": str(synthesis_json),
        "output_md": str(synthesis_md),
    }
    if audit_ok:
        result["output_audit_json"] = str(synthesis_audit)
    if pdf_ok:
        result["output_pdf"] = str(pdf_path)

    teaser_payload: dict[str, Any] = {}
    if synthesis_md.exists():
        teaser_output_dir = synthesis_dir
        # Use final_review markdown as the canonical teaser source to ensure
        # prompt extraction follows the finalized report content exactly.
        teaser_source = synthesis_md
        use_gemini = _env_true("TEASER_USE_GEMINI", default=True)
        teaser_result = generate_teaser_figure(
            teaser_source,
            output_dir=teaser_output_dir,
            generate_image=use_gemini,
        )
        teaser_payload = {
            "status": teaser_result.status,
            "message": teaser_result.message,
            "clipboard_copied": teaser_result.clipboard_copied,
            "used_gemini_api": teaser_result.used_gemini_api,
            "model": teaser_result.model,
            "source_markdown_path": teaser_result.source_markdown_path,
            "prompt_path": teaser_result.prompt_path,
            "prompt": teaser_result.prompt,
            "image_path": teaser_result.image_path,
            "response_path": teaser_result.response_path,
        }
        result["teaser_figure"] = teaser_payload
        result["teaser_figure_prompt"] = teaser_result.prompt_path
        if teaser_result.image_path:
            result["teaser_figure_image"] = teaser_result.image_path

    synthesis_payload = read_json_file(synthesis_json)
    if synthesis_payload:
        synthesis_payload["teaser_figure"] = teaser_payload
        write_json_file(synthesis_json, synthesis_payload)

    return result


if __name__ == "__main__":
    raise SystemExit("Internal stage module. Use scripts/execute_review_pipeline.py.")
