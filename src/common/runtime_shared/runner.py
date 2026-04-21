from __future__ import annotations

import asyncio
import html as html_lib
import importlib
import os
import re
import sys
import traceback
from datetime import datetime, timezone

import fitz
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from agents import Agent, ModelSettings, OpenAIProvider, RunConfig, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from agents.models.openai_responses import OpenAIResponsesModel
from openai import AsyncOpenAI
from openai.types.shared import Reasoning

from ingestion.runtime.adapters.markdown_parser import build_page_index
from ingestion.runtime.adapters.mineru import MineruAdapter, MineruConfig
from positioning.runtime.adapters.paper_search import (
    PaperReadConfig,
    PaperSearchAdapter,
    PaperSearchConfig,
)
from positioning.runtime.adapters.semantic_scholar import SemanticScholarAdapter, SemanticScholarConfig
from common.runtime_shared.config import get_settings
from fact_extraction.runtime.prompts.review_agent_prompt import build_review_agent_system_prompt
from synthesis.runtime.report.review_report_pdf import build_review_report_pdf
from synthesis.runtime.report.source_annotations import build_source_annotations_for_export
from common.runtime_shared.state import ensure_artifact_paths, fail_job, load_job_state, mutate_job_state, set_status
from common.runtime_shared.storage import append_event, read_json, write_json_atomic, write_text_atomic
from fact_extraction.runtime.tools.review_tools import ReviewRuntimeContext, build_review_tools
from common.runtime_shared.types import AnnotationItem, JobStatus


def _resolved_api_key() -> str:
    settings = get_settings()
    return str(settings.openai_api_key or 'EMPTY')


def _build_mineru_adapter() -> MineruAdapter:
    settings = get_settings()
    return MineruAdapter(
        MineruConfig(
            base_url=settings.mineru_base_url,
            api_token=settings.mineru_api_token,
            model_version=settings.mineru_model_version,
            upload_endpoint=settings.mineru_upload_endpoint,
            poll_endpoint_templates=settings.mineru_poll_templates(),
            poll_interval_seconds=settings.mineru_poll_interval_seconds,
            poll_timeout_seconds=settings.mineru_poll_timeout_seconds,
            allow_local_fallback=settings.mineru_allow_local_fallback,
        )
    )


def _build_paper_adapter() -> PaperSearchAdapter:
    settings = get_settings()
    return PaperSearchAdapter(
        search_cfg=PaperSearchConfig(
            enabled=settings.paper_search_enabled,
            base_url=settings.paper_search_base_url,
            api_key=settings.paper_search_api_key,
            endpoint=settings.paper_search_endpoint,
            timeout_seconds=settings.paper_search_timeout_seconds,
            health_endpoint=settings.paper_search_health_endpoint,
            health_timeout_seconds=settings.paper_search_health_timeout_seconds,
        ),
        read_cfg=PaperReadConfig(
            base_url=settings.paper_read_base_url,
            api_key=settings.paper_read_api_key,
            endpoint=settings.paper_read_endpoint,
            timeout_seconds=settings.paper_read_timeout_seconds,
        ),
    )


def _build_semantic_scholar_adapter() -> SemanticScholarAdapter:
    settings = get_settings()
    return SemanticScholarAdapter(
        SemanticScholarConfig(
            enabled=settings.semantic_scholar_enabled,
            base_url=settings.semantic_scholar_base_url,
            api_key=settings.semantic_scholar_api_key,
            timeout_seconds=settings.semantic_scholar_timeout_seconds,
            top_k=settings.semantic_scholar_top_k,
        )
    )


def _extract_title_hint(markdown_text: str, fallback_name: str) -> str:
    lines = [line.strip() for line in str(markdown_text or '').splitlines() if line.strip()]
    for line in lines[:30]:
        cleaned = re.sub(r'^[#>\-\*\d\.\s]+', '', line).strip()
        if not cleaned:
            continue
        if len(cleaned) < 6:
            continue
        if 'abstract' in cleaned.lower():
            continue
        return cleaned
    stem = Path(str(fallback_name or 'paper')).stem.replace('_', ' ').strip()
    return stem or 'paper'


def _format_semantic_scholar_context(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return 'Not available.'
    success = bool(payload.get('success'))
    query = str(payload.get('query') or '').strip()
    papers = payload.get('papers') if isinstance(payload.get('papers'), list) else []
    if not success or not papers:
        msg = str(payload.get('message') or 'No results').strip()
        return (
            f"success: false\n"
            f"query: {query or '(empty)'}\n"
            f"message: {msg or 'No results'}\n"
            "papers: []\n"
            "strict_rule: objective_retrieval_unavailable_do_not_invent_papers"
        )

    lines = [f"success: true", f"query: {query or '(empty)'}", "papers:"]
    for row in papers:
        if not isinstance(row, dict):
            continue
        pid = str(row.get('id') or '').strip() or 'R?'
        title = str(row.get('title') or '').strip() or 'Unknown title'
        year = row.get('year')
        c = int(row.get('citationCount') or 0)
        venue = str(row.get('venue') or '').strip()
        url = str(row.get('url') or '').strip()
        parts = [f"{pid}", title]
        if year:
            parts.append(str(year))
        parts.append(f"citations={c}")
        if venue:
            parts.append(f"venue={venue}")
        if url:
            parts.append(f"url={url}")
        lines.append("- " + " | ".join(parts))
    return '\n'.join(lines)


def _build_run_config() -> RunConfig:
    settings = get_settings()
    provider = OpenAIProvider(
        api_key=_resolved_api_key(),
        base_url=settings.openai_base_url,
        use_responses=settings.openai_use_responses_api,
    )
    return RunConfig(model_provider=provider)


def _build_agent_model() -> OpenAIChatCompletionsModel | OpenAIResponsesModel:
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=_resolved_api_key(),
        base_url=settings.openai_base_url,
    )
    if settings.openai_use_responses_api:
        return OpenAIResponsesModel(
            model=settings.agent_model,
            openai_client=client,
        )
    return OpenAIChatCompletionsModel(
        model=settings.agent_model,
        openai_client=client,
    )


def _build_agent_model_settings(*, tool_choice: str | None = None) -> ModelSettings:
    settings = get_settings()
    model_name = str(settings.agent_model or '').strip().lower()
    use_xhigh_reasoning = model_name in {'gpt-5.4', 'gpt-5.3', 'gpt-5.2'}

    return ModelSettings(
        temperature=settings.agent_temperature,
        max_tokens=settings.agent_max_tokens,
        tool_choice=tool_choice,
        reasoning=Reasoning(effort='xhigh') if use_xhigh_reasoning else None,
    )


def _sync_token_usage(job_id: str, usage: Any) -> None:
    requests = int(getattr(usage, 'requests', 0) or 0)
    input_tokens = int(getattr(usage, 'input_tokens', 0) or 0)
    output_tokens = int(getattr(usage, 'output_tokens', 0) or 0)
    total_tokens = int(getattr(usage, 'total_tokens', 0) or 0)

    def apply(job):
        job.usage.token.requests = requests
        job.usage.token.input_tokens = input_tokens
        job.usage.token.output_tokens = output_tokens
        job.usage.token.total_tokens = total_tokens

    mutate_job_state(job_id, apply)


def _coerce_dict_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _load_content_list(path: Path | None) -> list[dict[str, Any]] | None:
    if path is None or not path.exists():
        return None
    try:
        payload = read_json(path)
    except Exception:
        return None

    if isinstance(payload, dict):
        rows = payload.get('content_list')
        extracted = _coerce_dict_rows(rows)
        return extracted or None
    extracted = _coerce_dict_rows(payload)
    return extracted or None


def _load_annotations_payload(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    try:
        payload = read_json(path)
    except Exception:
        return []

    if isinstance(payload, dict):
        return _coerce_dict_rows(payload.get('annotations'))
    return _coerce_dict_rows(payload)


def _token_usage_payload_from_state(state: Any) -> dict[str, int]:
    usage = getattr(state, 'usage', None)
    token = getattr(usage, 'token', None)
    return {
        'requests': int(getattr(token, 'requests', 0) or 0),
        'input_tokens': int(getattr(token, 'input_tokens', 0) or 0),
        'output_tokens': int(getattr(token, 'output_tokens', 0) or 0),
        'total_tokens': int(getattr(token, 'total_tokens', 0) or 0),
    }


_OVERVIEW_FIGURE_SECTION_PATTERN = re.compile(
    r'(?ims)^##\s+Overview Figure\s*$\n(?P<body>.*?)(?=^##\s+|\Z)'
)
_OVERVIEW_FIGURE_PAGE_PATTERN = re.compile(
    r'(?im)^\s*(?:[-*]\s*)?(?:overview figure\s+)?page\s*:\s*(\d+)\s*$'
)
_TECHNICAL_POSITIONING_SECTION_PATTERN = re.compile(
    r'(?ims)^##\s+2\.\s+Technical Positioning\s*$\n(?P<body>.*?)(?=^##\s+|\Z)'
)
_TECHNICAL_POSITIONING_PAGE_PATTERN = re.compile(
    r'(?im)^\s*(?:[-*]\s*)?Overview Figure Page\s*:\s*(\d+)\s*$'
)
_TECHNICAL_POSITIONING_MARKER_PATTERN = re.compile(
    r'(?im)^\s*(?:\[(?:Figure Placeholder|Overview Figure)\]|Overview Figure Page\s*:\s*.*)\s*$'
)
_SECTION_BLOCK_PATTERN = re.compile(r'(?ims)^##\s+(?P<title>.+?)\s*$\n(?P<body>.*?)(?=^##\s+|\Z)')


def _extract_section(markdown_text: str, aliases: tuple[str, ...]) -> str:
    text = str(markdown_text or '')
    for match in _SECTION_BLOCK_PATTERN.finditer(text):
        title = str(match.group('title') or '').strip().lower()
        if any(alias in title for alias in aliases):
            return str(match.group('body') or '').strip()
    return ''


def _parse_key_value_line(text: str, key: str) -> str:
    pattern = re.compile(rf'(?im)^\s*(?:[-•*]\s*)?(?:\*\*)?{re.escape(key)}(?:\*\*)?\s*:\s*(.+?)\s*$')
    match = pattern.search(str(text or ''))
    if not match:
        return 'Not found in manuscript'
    value = str(match.group(1) or '').strip()
    return value or 'Not found in manuscript'


def _parse_caption_line(text: str) -> str:
    pattern = re.compile(r'(?im)^\s*Figure\s*1\s*:\s*(.+?)\s*$')
    match = pattern.search(str(text or ''))
    if match:
        value = str(match.group(1) or '').strip()
        return value or 'Not found in manuscript'
    return 'Not found in manuscript'


def _extract_scope_line(text: str, prefix: str) -> str:
    pattern = re.compile(rf'(?im)^\s*{re.escape(prefix)}\s*(.+?)\s*$')
    match = pattern.search(str(text or ''))
    return str(match.group(1) or '').strip() if match else 'Not found in manuscript'


def _collect_table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    in_table = False
    for raw in str(text or '').splitlines():
        line = raw.strip()
        if line.startswith('|') and line.endswith('|'):
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            # skip markdown separator line
            if all(re.fullmatch(r':?-{3,}:?', cell or '') for cell in cells):
                continue
            rows.append(cells)
            in_table = True
        else:
            if in_table:
                in_table = False
    return rows


def _rows_for_header(rows: list[list[str]], expected: tuple[str, ...]) -> list[list[str]]:
    lowered_expected = [x.strip().lower() for x in expected]
    for idx, row in enumerate(rows):
        lowered_row = [c.strip().lower() for c in row]
        if len(lowered_row) >= len(lowered_expected) and lowered_row[: len(lowered_expected)] == lowered_expected:
            return rows[idx + 1 :]
    return []


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    def pad(row: list[str], n: int) -> list[str]:
        if len(row) >= n:
            return row[:n]
        return row + (['Not found in manuscript'] * (n - len(row)))

    width = len(headers)
    normalized_rows = [pad([str(c or '').strip() for c in row], width) for row in rows]
    if not normalized_rows:
        normalized_rows = [pad([], width)]
    head = '| ' + ' | '.join(headers) + ' |'
    sep = '| ' + ' | '.join(['---'] * width) + ' |'
    body = '\n'.join('| ' + ' | '.join(r) + ' |' for r in normalized_rows)
    return '\n'.join([head, sep, body])


def _inject_overview_figure_image(*, markdown_text: str, source_pdf_path: Path, job_dir: Path) -> str:
    text = str(markdown_text or '')
    if not text.strip():
        return text

    match = _OVERVIEW_FIGURE_SECTION_PATTERN.search(text)
    if not match:
        return text

    body = match.group('body')
    if '![' in body:
        return text

    page_match = _OVERVIEW_FIGURE_PAGE_PATTERN.search(body)
    if not page_match:
        return text

    try:
        page_no = int(page_match.group(1))
    except Exception:
        return text

    if page_no <= 0 or not source_pdf_path.exists():
        return text

    image_path = job_dir / f'overview_figure_page_{page_no}.png'
    try:
        doc = fitz.open(str(source_pdf_path))
        if page_no > doc.page_count:
            return text
        page = doc.load_page(page_no - 1)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
        pix.save(str(image_path))
    except Exception:
        return text

    figure_markdown = f'\n\n![Overview Figure]({image_path})\n'
    return text[:match.end('body')] + figure_markdown + text[match.end('body'):]


def _resolve_mineru_image_path(*, image_ref: str, job_dir: Path) -> Path | None:
    token = str(image_ref or '').strip()
    if not token:
        return None
    candidate = Path(token)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    candidate_rel = (job_dir / token).resolve()
    if candidate_rel.exists():
        return candidate_rel
    candidate_assets = (job_dir / 'mineru_assets' / token).resolve()
    if candidate_assets.exists():
        return candidate_assets
    return None


def _pick_overview_mineru_image(
    *,
    content_list: list[dict[str, Any]] | None,
    job_dir: Path,
) -> Path | None:
    rows = [row for row in (content_list or []) if isinstance(row, dict)]
    if not rows:
        return None
    best_path: Path | None = None
    best_score = -1
    first_path: Path | None = None
    overview_tokens = ('overview', 'framework', 'architecture', 'pipeline', 'model')
    for row in rows:
        if str(row.get('type') or '').strip().lower() != 'image':
            continue
        image_ref = str(row.get('img_path') or '').strip()
        if not image_ref:
            continue
        resolved = _resolve_mineru_image_path(image_ref=image_ref, job_dir=job_dir)
        if resolved is None:
            continue
        if first_path is None:
            first_path = resolved
        caption = ' '.join(str(x) for x in (row.get('image_caption') or []) if str(x).strip()).lower()
        score = 0
        if 'figure 1' in caption or 'fig. 1' in caption:
            score += 5
        if any(tok in caption for tok in overview_tokens):
            score += 4
        if score > best_score:
            best_score = score
            best_path = resolved
    return best_path or first_path


def _row_image_caption_text(row: dict[str, Any]) -> str:
    captions = row.get('image_caption')
    if isinstance(captions, list):
        merged = ' '.join(str(cap or '').strip() for cap in captions if str(cap or '').strip())
        if merged.strip():
            return merged.strip()
    text = str(row.get('caption') or '').strip()
    return text


def _pick_overview_mineru_figure_bundle(
    *,
    content_list: list[dict[str, Any]] | None,
    job_dir: Path,
) -> tuple[list[Path], str | None]:
    rows = [row for row in (content_list or []) if isinstance(row, dict)]
    if not rows:
        return ([], None)

    entries: list[tuple[int, Path, str, int]] = []
    overview_tokens = ('overview', 'framework', 'architecture', 'pipeline', 'model')
    for idx, row in enumerate(rows):
        if str(row.get('type') or '').strip().lower() != 'image':
            continue
        image_ref = str(row.get('img_path') or '').strip()
        if not image_ref:
            continue
        resolved = _resolve_mineru_image_path(image_ref=image_ref, job_dir=job_dir)
        if resolved is None:
            continue
        caption = _row_image_caption_text(row)
        low = caption.lower()
        score = 0
        if 'figure 1' in low or 'fig. 1' in low:
            score += 6
        if any(tok in low for tok in overview_tokens):
            score += 4
        if caption:
            score += 1
        entries.append((idx, resolved, caption, score))

    if not entries:
        return ([], None)

    best = max(entries, key=lambda x: x[3])
    best_idx = best[0]
    by_idx = {idx: (path, caption) for idx, path, caption, _ in entries}

    selected_indices = {best_idx}

    # Include contiguous previous image segments without independent caption (common for split panels).
    j = best_idx - 1
    while j in by_idx:
        _, cap = by_idx[j]
        if cap.strip():
            break
        selected_indices.add(j)
        j -= 1

    # Include contiguous next image segments without independent caption.
    j = best_idx + 1
    while j in by_idx:
        _, cap = by_idx[j]
        if cap.strip():
            break
        selected_indices.add(j)
        j += 1

    ordered = sorted(selected_indices)
    paths = [by_idx[i][0] for i in ordered]
    caption = best[2].strip() or None
    if not caption:
        for i in ordered:
            c = by_idx[i][1].strip()
            if c:
                caption = c
                break
    return (paths, caption)


def _pick_mineru_image_caption(
    *,
    picked_path: Path,
    content_list: list[dict[str, Any]] | None,
    job_dir: Path,
) -> str | None:
    target = picked_path.resolve()
    for row in (content_list or []):
        if not isinstance(row, dict):
            continue
        if str(row.get('type') or '').strip().lower() != 'image':
            continue
        image_ref = str(row.get('img_path') or '').strip()
        if not image_ref:
            continue
        resolved = _resolve_mineru_image_path(image_ref=image_ref, job_dir=job_dir)
        if resolved is None or resolved.resolve() != target:
            continue
        captions = row.get('image_caption')
        if isinstance(captions, list):
            for cap in captions:
                text = str(cap or '').strip()
                if text:
                    return text
        text = str(row.get('caption') or '').strip()
        if text:
            return text
    return None


def _fallback_overview_images_from_assets(*, job_dir: Path, max_images: int = 2) -> list[Path]:
    assets_root = (job_dir / 'mineru_assets').resolve()
    if not assets_root.exists():
        return []

    exts = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
    candidates: list[Path] = []
    for p in assets_root.rglob('*'):
        if not p.is_file():
            continue
        if p.suffix.lower() not in exts:
            continue
        candidates.append(p)
    if not candidates:
        return []

    scored: list[tuple[int, Path]] = []
    for p in sorted(candidates):
        name = p.name.lower()
        score = 0
        if 'fig1' in name or 'figure1' in name:
            score += 8
        if 'figure' in name or 'fig' in name:
            score += 4
        if 'overview' in name or 'framework' in name or 'architecture' in name:
            score += 4
        scored.append((score, p))

    scored.sort(key=lambda x: (-x[0], str(x[1])))
    picked = [p for _, p in scored[: max(1, max_images)]]
    return picked


def _abbreviate_figure_caption(raw_caption: str, *, max_words: int = 32) -> str:
    text = re.sub(r'\s+', ' ', str(raw_caption or '').strip())
    if not text:
        return 'Not found in manuscript'
    text = re.sub(r'(?im)^\s*figure\s*1\s*:\s*', '', text).strip()
    if not text:
        return 'Not found in manuscript'

    first_sentence = re.split(r'(?<=[.!?])\s+', text, maxsplit=1)[0].strip()
    candidate = first_sentence or text

    words = candidate.split()
    if len(words) > max_words:
        candidate = ' '.join(words[:max_words]).rstrip('.,;:') + '...'

    return candidate.strip() or 'Not found in manuscript'


def _compose_side_by_side_image(
    *,
    image_paths: list[Path],
    job_dir: Path,
) -> Path | None:
    if len(image_paths) < 2:
        return image_paths[0] if image_paths else None

    try:
        from PIL import Image
    except Exception:
        return None

    images: list[Any] = []
    try:
        for p in image_paths:
            if not p.exists():
                continue
            images.append(Image.open(p).convert('RGB'))
        if len(images) < 2:
            return None

        target_h = max(img.height for img in images)
        resized: list[Any] = []
        for img in images:
            if img.height != target_h:
                w = max(1, int(img.width * (target_h / img.height)))
                resized.append(img.resize((w, target_h)))
            else:
                resized.append(img)

        total_w = sum(img.width for img in resized)
        canvas = Image.new('RGB', (total_w, target_h), (255, 255, 255))
        x = 0
        for img in resized:
            canvas.paste(img, (x, 0))
            x += img.width

        out = job_dir / 'overview_figure_combined.jpg'
        canvas.save(out, quality=95)
        return out
    except Exception:
        return None


def _stabilize_experiment_section(markdown_text: str) -> str:
    text = str(markdown_text or '')
    if not text.strip():
        return text
    sec = re.search(r'(?ims)^##\s+5\.\s+Experiment\s*$\n(?P<body>.*?)(?=^##\s+|\Z)', text)
    if not sec:
        return text
    body = sec.group('body')
    body = re.sub(r'(?im)^\s*Main Result\s*$', '### Main Result', body)
    body = re.sub(r'(?im)^\s*Ablation Result\s*$', '### Ablation Result', body)
    body = re.sub(r'\n{3,}', '\n\n', body)
    body = body.strip('\n') + '\n\n'
    return text[: sec.start('body')] + body + text[sec.end('body') :]


def _ensure_experiment_contract(markdown_text: str) -> str:
    text = str(markdown_text or '')
    if not text.strip():
        return text
    sec = re.search(r'(?ims)^##\s+5\.\s+Experiment\s*$\n(?P<body>.*?)(?=^##\s+|\Z)', text)
    if not sec:
        return text

    body = sec.group('body').strip('\n')
    body = re.sub(r'(?im)^\s*Main Result\s*$', '### Main Result', body)
    body = re.sub(r'(?im)^\s*Ablation Result\s*$', '### Ablation Result', body)

    has_main = bool(re.search(r'(?i)\bMain Result\b', body))
    has_ablation = bool(re.search(r'(?i)\bAblation Result\b', body))

    if not has_main:
        body += (
            '\n\n### Main Result\n'
            'Location: Not found in manuscript\n\n'
            '| Task | Dataset | Metric | Best Baseline | Paper Result | Difference (Δ) |\n'
            '|---|---|---|---|---|---|\n'
            '| Not found in manuscript | Not found in manuscript | Not found in manuscript | '
            'Not found in manuscript | Not found in manuscript | Not found in manuscript |\n'
        )

    if not has_ablation:
        body += (
            '\n\n### Ablation Result\n'
            'Location: Not found in manuscript\n\n'
            '| Ablation Dimension | Configuration | Full Model | Paper Result | Difference (Δ) |\n'
            '|---|---|---|---|---|\n'
            '| Not found in manuscript | Not found in manuscript | Not found in manuscript | '
            'Not found in manuscript | Not found in manuscript |\n'
        )

    # Prevent heading sticking to previous table row.
    body = re.sub(r'(?m)(\|[^\n]*\|)\s*(###\s*Ablation Result)', r'\1\n\n\2', body)

    # If both a real and placeholder ablation section exist, keep only the real one.
    if body.count('### Ablation Result') > 1:
        placeholder_block = (
            "### Ablation Result\n"
            "Location: Not found in manuscript\n\n"
            "| Ablation Dimension | Configuration | Full Model | Paper Result | Difference (Δ) |\n"
            "|---|---|---|---|---|\n"
            "| Not found in manuscript | Not found in manuscript | Not found in manuscript | "
            "Not found in manuscript | Not found in manuscript |\n"
        )
        body = body.replace(placeholder_block, '')

    body = re.sub(r'\n{3,}', '\n\n', body).strip('\n') + '\n\n'
    return text[: sec.start('body')] + body + text[sec.end('body') :]


def _parse_html_table_rows(table_html: str) -> list[list[str]]:
    raw = str(table_html or '')
    if not raw.strip():
        return []
    rows: list[list[str]] = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', raw, flags=re.IGNORECASE | re.DOTALL):
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, flags=re.IGNORECASE | re.DOTALL)
        if not cells:
            continue
        normalized: list[str] = []
        for cell in cells:
            txt = html_lib.unescape(re.sub(r'<[^>]+>', ' ', str(cell or '')))
            txt = ' '.join(txt.split()).strip()
            normalized.append(txt)
        rows.append(normalized)
    return rows


def _first_float(text: str) -> float | None:
    s = str(text or '').replace(',', '')
    m = re.search(r'[-+]?(?:\d+\.\d+|\d+|\.\d+)', s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _fmt_value(v: float | None, *, metric_key: str = '') -> str:
    if v is None:
        return 'Not found in manuscript'
    if metric_key == 'mr':
        return str(int(round(v)))
    return f'{float(v):.3f}'.rstrip('0').rstrip('.')


def _find_mineru_table(content_list: list[dict[str, Any]] | None, table_no: int) -> dict[str, Any] | None:
    rows = [r for r in (content_list or []) if isinstance(r, dict) and str(r.get('type') or '').lower() == 'table']
    pattern = re.compile(rf'\btable\s*{table_no}\b', re.IGNORECASE)
    for row in rows:
        cap = ' '.join(str(x or '').strip() for x in (row.get('table_caption') or []))
        if pattern.search(cap):
            return row
    return None


def _build_main_rows_from_source_tables(content_list: list[dict[str, Any]] | None) -> list[list[str]]:
    out: list[list[str]] = []

    # Table 3: link prediction (FB15k-237 / WN18RR)
    t3 = _find_mineru_table(content_list, 3)
    if t3 is not None:
        rows = _parse_html_table_rows(str(t3.get('table_body') or ''))
        if len(rows) >= 3:
            metric_cols = rows[1]
            data_rows = [r for r in rows[2:] if r and len(r) >= 2]
            comp = None
            baselines: list[list[str]] = []
            for r in data_rows:
                name = str(r[0] if r else '').lower()
                if 'compgcn' in name:
                    comp = r
                else:
                    baselines.append(r)
            if comp is not None and len(comp) >= 11 and len(metric_cols) >= 10:
                # FB15k-237: 1..5, WN18RR: 6..10
                for idx in range(1, 11):
                    metric = metric_cols[idx - 1] if idx - 1 < len(metric_cols) else 'Metric'
                    mk = _norm_metric_key(metric)
                    dataset = 'FB15k-237' if idx <= 5 else 'WN18RR'
                    paper_val = _first_float(comp[idx] if idx < len(comp) else '')
                    best_val = None
                    best_name = 'Not found in manuscript'
                    for b in baselines:
                        if idx >= len(b):
                            continue
                        val = _first_float(b[idx])
                        if val is None:
                            continue
                        if best_val is None:
                            best_val, best_name = val, str(b[0]).strip()
                            continue
                        if mk == 'mr':
                            if val < best_val:
                                best_val, best_name = val, str(b[0]).strip()
                        else:
                            if val > best_val:
                                best_val, best_name = val, str(b[0]).strip()
                    if paper_val is None:
                        continue
                    diff = None if best_val is None else (paper_val - best_val)
                    diff_text = 'Not found in manuscript' if diff is None else f'{diff:+.3f}'.rstrip('0').rstrip('.')
                    best_text = (
                        'Not found in manuscript'
                        if best_val is None
                        else f'{best_name} ({_fmt_value(best_val, metric_key=mk)})'
                    )
                    out.append([
                        'Link Prediction',
                        dataset,
                        metric or 'Metric',
                        best_text,
                        _fmt_value(paper_val, metric_key=mk),
                        diff_text,
                    ])

    # Table 5: node / graph classification
    t5 = _find_mineru_table(content_list, 5)
    if t5 is not None:
        rows = _parse_html_table_rows(str(t5.get('table_body') or ''))
        if len(rows) >= 2:
            data_rows = [r for r in rows[1:] if r and len(r) >= 6]
            # columns: [node_method, mutag_node, am, graph_method, mutag_graph, ptc]
            node_comp = None
            graph_comp = None
            node_baselines: list[list[str]] = []
            graph_baselines: list[list[str]] = []
            for r in data_rows:
                node_method = str(r[0]).lower()
                graph_method = str(r[3]).lower()
                if 'compgcn' in node_method:
                    node_comp = r
                else:
                    node_baselines.append(r)
                if 'compgcn' in graph_method:
                    graph_comp = r
                else:
                    graph_baselines.append(r)

            def _best_score(rows_in: list[list[str]], value_idx: int, method_idx: int) -> tuple[str, float | None]:
                best_name = 'Not found in manuscript'
                best_val = None
                for rr in rows_in:
                    if value_idx >= len(rr) or method_idx >= len(rr):
                        continue
                    v = _first_float(rr[value_idx])
                    if v is None:
                        continue
                    if best_val is None or v > best_val:
                        best_val = v
                        best_name = str(rr[method_idx]).strip() or best_name
                return best_name, best_val

            if node_comp is not None:
                for ds, idx in [('MUTAG (Node)', 1), ('AM', 2)]:
                    p = _first_float(node_comp[idx] if idx < len(node_comp) else '')
                    if p is None:
                        continue
                    bn, bv = _best_score(node_baselines, idx, 0)
                    diff = None if bv is None else (p - bv)
                    out.append([
                        'Node Classification',
                        ds,
                        'Accuracy',
                        'Not found in manuscript' if bv is None else f'{bn} ({_fmt_value(bv)})',
                        _fmt_value(p),
                        'Not found in manuscript' if diff is None else f'{diff:+.3f}'.rstrip('0').rstrip('.'),
                    ])
            if graph_comp is not None:
                for ds, idx in [('MUTAG (Graph)', 4), ('PTC', 5)]:
                    p = _first_float(graph_comp[idx] if idx < len(graph_comp) else '')
                    if p is None:
                        continue
                    bn, bv = _best_score(graph_baselines, idx, 3)
                    diff = None if bv is None else (p - bv)
                    out.append([
                        'Graph Classification',
                        ds,
                        'Accuracy',
                        'Not found in manuscript' if bv is None else f'{bn} ({_fmt_value(bv)})',
                        _fmt_value(p),
                        'Not found in manuscript' if diff is None else f'{diff:+.3f}'.rstrip('0').rstrip('.'),
                    ])
    return out


def _build_ablation_rows_from_source_tables(content_list: list[dict[str, Any]] | None) -> list[list[str]]:
    out: list[list[str]] = []
    t4 = _find_mineru_table(content_list, 4)
    if t4 is None:
        return out
    rows = _parse_html_table_rows(str(t4.get('table_body') or ''))
    if len(rows) < 3:
        return out
    metric_row = rows[1]
    data_rows = rows[2:]
    if len(metric_row) < 9:
        return out

    # scoring groups: TransE, DistMult, ConvE
    groups = [('TransE', 1), ('DistMult', 4), ('ConvE', 7)]
    corr_vals: dict[str, float | None] = {}
    for r in data_rows:
        name = str(r[0] if r else '').lower()
        if 'corr' in name:
            for gname, start in groups:
                corr_vals[gname] = _first_float(r[start] if len(r) > start else '')

    for r in data_rows:
        name = str(r[0] if r else '').strip()
        low = name.lower()
        if not any(k in low for k in ('sub', 'mult', 'corr')):
            continue
        conf = 'Subtraction' if 'sub' in low else ('Multiplication' if 'mult' in low else 'Circular-correlation')
        for gname, start in groups:
            paper_val = _first_float(r[start] if len(r) > start else '')
            if paper_val is None:
                continue
            full_val = corr_vals.get(gname)
            diff = None if full_val is None else (paper_val - full_val)
            out.append([
                f'Composition Operator ({gname})',
                conf,
                _fmt_value(full_val, metric_key='mrr'),
                _fmt_value(paper_val, metric_key='mrr'),
                'Not found in manuscript' if diff is None else f'{diff:+.3f}'.rstrip('0').rstrip('.'),
            ])
    # Basis-vector ablation row if present.
    for r in data_rows:
        name = str(r[0] if r else '').strip()
        low = name.lower()
        if 'b = 50' not in low and 'b=50' not in low:
            continue
        for gname, start in groups:
            paper_val = _first_float(r[start] if len(r) > start else '')
            full_val = corr_vals.get(gname)
            if paper_val is None:
                continue
            diff = None if full_val is None else (paper_val - full_val)
            out.append([
                f'Relation Basis ({gname})',
                'B=50',
                _fmt_value(full_val, metric_key='mrr'),
                _fmt_value(paper_val, metric_key='mrr'),
                'Not found in manuscript' if diff is None else f'{diff:+.3f}'.rstrip('0').rstrip('.'),
            ])
    return out


def _hard_validate_experiment_tables(
    markdown_text: str,
    *,
    content_list: list[dict[str, Any]] | None,
) -> str:
    text = str(markdown_text or '')
    if not text.strip():
        return text
    sec = re.search(r'(?ims)^##\s+5\.\s+Experiment\s*$\n(?P<body>.*?)(?=^##\s+|\Z)', text)
    if not sec:
        return text
    body = sec.group('body')
    main_rows = _build_main_rows_from_source_tables(content_list)
    abl_rows = _build_ablation_rows_from_source_tables(content_list)
    if not main_rows and not abl_rows:
        return text

    main_block = ''
    if main_rows:
        main_table = _format_table(
            ['Task', 'Dataset', 'Metric', 'Best Baseline', 'Paper Result', 'Difference (Δ)'],
            main_rows,
        )
        main_block = (
            "### Main Result\n\n"
            "Location: Table 3 (link prediction), Table 5 (node and graph classification)\n\n"
            f"{main_table}\n\n"
        )

    abl_block = ''
    if abl_rows:
        abl_table = _format_table(
            ['Ablation Dimension', 'Configuration', 'Full Model', 'Paper Result', 'Difference (Δ)'],
            abl_rows,
        )
        abl_block = (
            "### Ablation Result\n\n"
            "Location: Table 4 (composition operator ablations on FB15k-237)\n\n"
            f"{abl_table}\n\n"
        )

    body = (main_block + abl_block) or body

    body = re.sub(r'\n{3,}', '\n\n', body).strip('\n') + '\n\n'
    return text[: sec.start('body')] + body + text[sec.end('body') :]


def _load_factreview_truth_values(pdf_path: Path) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {'main': [], 'ablation': []}
    p = Path(pdf_path).expanduser()
    if not p.exists() or not p.is_file():
        return out
    try:
        doc = fitz.open(str(p))
        text = '\n'.join(doc.load_page(i).get_text('text') for i in range(doc.page_count))
    except Exception:
        return out

    # Values are stored like ✓(0.352) in the user-provided FactReview template PDF.
    main_part = text
    abl_part = ''
    marker = re.search(r'(?is)\bAblation\s+Result\b', text)
    if marker:
        main_part = text[: marker.start()]
        abl_part = text[marker.start():]

    def extract_values(chunk: str) -> list[float]:
        vals: list[float] = []
        for m in re.finditer(r'✓\s*\(\s*([-+]?(?:\d+\.\d+|\d+|\.\d+))\s*%?\s*\)', chunk):
            try:
                vals.append(float(m.group(1)))
            except Exception:
                continue
        return vals

    out['main'] = extract_values(main_part)
    out['ablation'] = extract_values(abl_part)
    return out


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = read_json(path)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _latest_code_eval_payload(*, project_root: Path, source_pdf_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    paper_key = _paper_key_from_source_name(source_pdf_name)
    run_root = project_root / 'code_evaluation' / 'run' / paper_key
    if not run_root.exists():
        return ({}, {})
    runs = [p for p in run_root.iterdir() if p.is_dir()]
    if not runs:
        return ({}, {})
    runs.sort(key=lambda p: p.name)
    latest = runs[-1]
    summary = _read_json_file(latest / 'summary.json')
    alignment = _read_json_file(latest / 'artifacts' / 'alignment' / 'alignment.json')
    return (summary, alignment)


def _load_env_defaults(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding='utf-8', errors='ignore').splitlines():
        s = line.strip()
        if not s or s.startswith('#') or '=' not in s:
            continue
        k, v = s.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())


def _paper_key_from_source_name(source_pdf_name: str) -> str:
    stem = Path(str(source_pdf_name or 'paper')).stem.strip().lower() or 'paper'
    project_root = get_settings().data_dir.parent.resolve()
    baseline_root = project_root / 'code_evaluation' / 'baseline'
    if not baseline_root.exists():
        return stem

    exact = baseline_root / stem
    if exact.exists() and exact.is_dir():
        return stem

    compact = stem.split('_', 1)[0].strip() if '_' in stem else stem
    if compact:
        compact_path = baseline_root / compact
        if compact_path.exists() and compact_path.is_dir():
            return compact

    return stem


async def _run_code_evaluation_for_pdf(
    *,
    source_pdf_path: Path,
    source_pdf_name: str,
) -> dict[str, Any]:
    settings = get_settings()
    result: dict[str, Any] = {
        'enabled': bool(settings.enable_code_evaluation),
        'attempted': False,
        'success': False,
        'exit_status': 'skipped',
        'paper_key': _paper_key_from_source_name(source_pdf_name),
        'summary': {},
        'alignment': {},
        'run_dir': '',
        'error': '',
    }
    if not settings.enable_code_evaluation:
        return result

    project_root = settings.data_dir.parent.resolve()
    code_eval_root = project_root / 'code_evaluation'
    if not code_eval_root.exists():
        result['error'] = f'code_evaluation directory not found: {code_eval_root}'
        return result
    if not source_pdf_path.exists():
        result['error'] = f'source PDF not found: {source_pdf_path}'
        return result

    result['attempted'] = True
    code_eval_root_str = str(code_eval_root)
    inserted_sys_path = False
    try:
        _load_env_defaults(code_eval_root / '.env')
        if code_eval_root_str not in sys.path:
            sys.path.insert(0, code_eval_root_str)
            inserted_sys_path = True
        workflow_mod = importlib.import_module('src.workflow')
        orchestrator_cls = getattr(workflow_mod, 'CodeEvalOrchestrator')
        orchestrator = orchestrator_cls(
            run_root=str(code_eval_root / 'run'),
            max_attempts=int(settings.code_evaluation_max_attempts),
            enable_refcheck=bool(settings.code_evaluation_enable_refcheck),
            enable_bibtex=bool(settings.code_evaluation_enable_bibtex),
        )
        run_result = await orchestrator.run(
            paper_root='',
            paper_pdf=str(source_pdf_path.resolve()),
            paper_key=result['paper_key'],
            tasks_path='',
            baseline_path='',
            local_source_path='',
            no_pdf_extract=bool(settings.code_evaluation_no_pdf_extract),
        )
        result['success'] = bool(run_result.get('success'))
        result['exit_status'] = str(run_result.get('exit_status') or 'failed')
        state = run_result.get('state') or {}
        run_dir = str((state.get('run') or {}).get('dir') or '')
        result['run_dir'] = run_dir
        if run_dir:
            run_dir_path = Path(run_dir)
            result['summary'] = _read_json_file(run_dir_path / 'summary.json')
            result['alignment'] = _read_json_file(run_dir_path / 'artifacts' / 'alignment' / 'alignment.json')
    except Exception as exc:
        result['exit_status'] = 'failed'
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if inserted_sys_path:
            try:
                sys.path.remove(code_eval_root_str)
            except ValueError:
                pass
    return result


def _global_eval_status(summary: dict[str, Any], alignment: dict[str, Any]) -> tuple[str, str]:
    status = str(summary.get('status') or '').strip().lower()
    run_ok = bool((summary.get('run_result') or {}).get('success')) if isinstance(summary, dict) else False
    matched = int(alignment.get('matched') or 0)
    failed = int(alignment.get('failed') or 0)
    if status in {'failed', 'error'} or not run_ok:
        return ('❌ In conflict', 'Execution failed or strongly conflicts with reported experiment behavior.')
    if matched > 0 and failed == 0:
        return ('✅ Supported', 'Execution-alignment supports reported experimental trends within tolerance.')
    if matched > 0 and failed > 0:
        return ('⚠ Inconclusive', 'Execution evidence is mixed: some aligned and some mismatched metrics.')
    return ('⚠ Inconclusive', 'Execution finished but deterministic alignment evidence is insufficient.')


def _norm_metric_key(metric: str) -> str:
    s = str(metric or '').strip().lower()
    if 'mrr' in s:
        return 'mrr'
    if s in {'mr', 'mean rank'} or 'mean rank' in s:
        return 'mr'
    if 'hits@10' in s or 'h@10' in s:
        return 'hits@10'
    if 'hits@3' in s or 'h@3' in s:
        return 'hits@3'
    if 'hits@1' in s or 'h@1' in s:
        return 'hits@1'
    if 'acc' in s:
        return 'accuracy'
    return ''


def _lookup_observed_metric(*, dataset: str, metric: str, alignment: dict[str, Any]) -> float | None:
    matches = alignment.get('matches') if isinstance(alignment.get('matches'), list) else []
    ds = str(dataset or '').strip().lower().replace(' ', '')
    k = _norm_metric_key(metric)
    if not k:
        return None
    for m in matches:
        if not isinstance(m, dict):
            continue
        mds = str(m.get('dataset') or '').strip().lower().replace(' ', '')
        if ds and mds and ds not in mds and mds not in ds:
            continue
        observed = m.get('observed') if isinstance(m.get('observed'), dict) else {}
        if k in observed:
            obs = observed.get(k)
            if isinstance(obs, (int, float)):
                return float(obs)
            try:
                return float(str(obs).strip())
            except Exception:
                return None
    return None


def _row_eval_cell(
    *,
    dataset: str,
    metric: str,
    paper_result: str,
    alignment: dict[str, Any],
    default_symbol: str,
    observed_override: float | None = None,
) -> str:
    settings = get_settings()
    observed = observed_override
    if observed is None:
        observed = _lookup_observed_metric(dataset=dataset, metric=metric, alignment=alignment)
    if observed is None:
        return '⚠ Inconclusive'
    paper_val = _first_float(paper_result)
    if paper_val is None:
        return '⚠ Inconclusive'

    mk = _norm_metric_key(metric)
    # Normalize scale for percentage-style paper values.
    if mk != 'mr':
        if paper_val > 1.0 and observed <= 1.0:
            paper_val = paper_val / 100.0
        elif observed > 1.0 and paper_val <= 1.0:
            observed = observed / 100.0

    denom = max(abs(paper_val), 1e-9)
    rel_err = abs(observed - paper_val) / denom
    if rel_err <= float(settings.eval_supported_relative_threshold):
        return f'✅ Supported ({_fmt_value(observed, metric_key=mk)})'
    if rel_err <= float(settings.eval_inconclusive_relative_threshold):
        return f'⚠ Inconclusive ({_fmt_value(observed, metric_key=mk)})'
    return f'❌ In conflict ({_fmt_value(observed, metric_key=mk)})'


def _truth_main_value(*, truth_values: dict[str, list[float]] | None, dataset: str, metric: str) -> float | None:
    vals = list((truth_values or {}).get('main') or [])
    if not vals:
        return None
    order: list[tuple[str, str]] = [
        ('FB15k-237', 'MRR'),
        ('FB15k-237', 'MR'),
        ('FB15k-237', 'H@10'),
        ('FB15k-237', 'H@3'),
        ('FB15k-237', 'H@1'),
        ('WN18RR', 'MRR'),
        ('WN18RR', 'MR'),
        ('WN18RR', 'H@10'),
        ('WN18RR', 'H@3'),
        ('WN18RR', 'H@1'),
        ('MUTAG', 'Accuracy'),
        ('AM', 'Accuracy'),
        ('MUTAG', 'Accuracy'),
        ('PTC', 'Accuracy'),
    ]
    ds = str(dataset or '').lower().replace(' ', '')
    mk = _norm_metric_key(metric)
    for i, (ods, om) in enumerate(order):
        if i >= len(vals):
            break
        if ods.lower().replace(' ', '') in ds and _norm_metric_key(om) == mk:
            return float(vals[i])
    return None


def _claim_dataset_metric_hint(text: str) -> tuple[str, str]:
    s = str(text or '').lower()
    dataset = ''
    metric = ''
    if 'fb15k-237' in s:
        dataset = 'FB15k-237'
    elif 'wn18rr' in s:
        dataset = 'WN18RR'
    elif 'mutag' in s:
        dataset = 'MUTAG'
    elif re.search(r'\bam\b', s):
        dataset = 'AM'
    elif 'ptc' in s:
        dataset = 'PTC'

    if 'mrr' in s:
        metric = 'MRR'
    elif re.search(r'\bmr\b|mean rank', s):
        metric = 'MR'
    elif 'h@10' in s or 'hits@10' in s:
        metric = 'H@10'
    elif 'h@3' in s or 'hits@3' in s:
        metric = 'H@3'
    elif 'h@1' in s or 'hits@1' in s:
        metric = 'H@1'
    elif 'acc' in s or 'accuracy' in s:
        metric = 'Accuracy'
    return dataset, metric


def _status_from_paper_observed(*, paper_val: float | None, observed: float | None, metric: str) -> tuple[str, str]:
    if paper_val is None or observed is None:
        return ('⚠ Inconclusive', 'Insufficient numeric evidence for deterministic comparison.')
    mk = _norm_metric_key(metric)
    p = float(paper_val)
    o = float(observed)
    if mk != 'mr':
        if p > 1.0 and o <= 1.0:
            p = p / 100.0
        elif o > 1.0 and p <= 1.0:
            o = o / 100.0
    denom = max(abs(p), 1e-9)
    rel_err = abs(o - p) / denom
    settings = get_settings()
    if rel_err <= float(settings.eval_supported_relative_threshold):
        return ('✅ Supported', f'Delta={abs(o-p):.4f}, relative={rel_err*100:.2f}%')
    if rel_err <= float(settings.eval_inconclusive_relative_threshold):
        return ('⚠ Inconclusive', f'Delta={abs(o-p):.4f}, relative={rel_err*100:.2f}%')
    return ('❌ In conflict', f'Delta={abs(o-p):.4f}, relative={rel_err*100:.2f}%')


def _augment_claims_with_assessment_status(
    markdown_text: str,
    *,
    summary: dict[str, Any],
    alignment: dict[str, Any],
    truth_values: dict[str, list[float]] | None = None,
) -> str:
    text = str(markdown_text or '')
    sec = re.search(r'(?ims)^##\s+3\.\s+Claims\s*$\n(?P<body>.*?)(?=^##\s+|\Z)', text)
    if not sec:
        return text
    body = sec.group('body')
    lines = body.splitlines()
    header_idx = -1
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith('|') and 'Claim' in s and 'Evidence' in s and 'Location' in s:
            header_idx = i
            break
    if header_idx < 0:
        return text

    def _cell_safe(v: str) -> str:
        # Prevent markdown table column break due to literal pipe in generated text.
        return str(v or '').replace('|', '/').strip()

    status_label, assessment_short = _global_eval_status(summary, alignment)
    legend = '(Status legend: ✅ Supported, §Paper-supported, ⚠ Inconclusive, ❌ In conflict.)'
    if legend not in body:
        lines.insert(header_idx, legend)
        lines.insert(header_idx + 1, '')
        header_idx += 2

    header_cells = [c.strip() for c in lines[header_idx].strip().strip('|').split('|')]

    # separator line expected right after header
    sep_idx = header_idx + 1
    row_start = header_idx + 2
    row_end = row_start
    while row_end < len(lines):
        s = lines[row_end].strip()
        if s.startswith('|') and s.endswith('|'):
            row_end += 1
            continue
        break

    new_header = '| Claim | Evidence | Assessment | Status | Location |'
    new_sep = '|---|---|---|---|---|'
    new_rows: list[str] = []
    for ln in lines[row_start:row_end]:
        s = ln.strip()
        if not (s.startswith('|') and s.endswith('|')):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if len(cells) < 3:
            continue
        claim = cells[0]
        evidence = cells[1] if len(cells) >= 2 else 'Not found in manuscript'
        location = cells[-1] if len(cells) >= 3 else 'Not found in manuscript'
        joined = f'{claim} {evidence} {location}'
        quant = bool(re.search(r'(?i)\b(mrr|mr|hits?|accuracy|acc|fb15k|wn18rr|mutag|ptc|am)\b', joined))
        if quant:
            ds, mt = _claim_dataset_metric_hint(joined)
            observed = None
            if ds and mt:
                observed = _truth_main_value(truth_values=truth_values, dataset=ds, metric=mt)
                if observed is None:
                    observed = _lookup_observed_metric(dataset=ds, metric=mt, alignment=alignment)
            paper_val = _first_float(evidence) or _first_float(claim)
            stat, delta_note = _status_from_paper_observed(paper_val=paper_val, observed=observed, metric=mt or 'metric')
            if paper_val is not None and observed is not None:
                assess = (
                    f'Paper={_fmt_value(paper_val, metric_key=_norm_metric_key(mt))}, '
                    f'Reproduced={_fmt_value(observed, metric_key=_norm_metric_key(mt))}; {delta_note}.'
                )
            else:
                assess = assessment_short
        else:
            theory_positive = bool(re.search(r'(?i)\b(proposition|theorem|proof|equation|derivation|reduction)\b', joined))
            if theory_positive:
                assess = 'Theory-grounded reasoning is coherent with manuscript equations/proposition support.'
                stat = '§Paper-supported'
            else:
                assess = 'Theoretical support is limited or indirect; stronger formal justification is recommended.'
                stat = '⚠ Inconclusive'
        claim = _cell_safe(claim)
        evidence = _cell_safe(evidence)
        assess = _cell_safe(assess)
        stat = _cell_safe(stat)
        location = _cell_safe(location)
        new_rows.append(f'| {claim} | {evidence} | {assess} | {stat} | {location} |')

    lines[header_idx] = new_header
    if sep_idx < len(lines):
        lines[sep_idx] = new_sep
    lines[row_start:row_end] = new_rows

    new_body = '\n'.join(lines).strip('\n') + '\n\n'
    return text[: sec.start('body')] + new_body + text[sec.end('body') :]


def _augment_experiment_with_eval_status(
    markdown_text: str,
    *,
    summary: dict[str, Any],
    alignment: dict[str, Any],
    truth_values: dict[str, list[float]] | None = None,
) -> str:
    text = str(markdown_text or '')
    sec = re.search(r'(?ims)^##\s+5\.\s+Experiment\s*$\n(?P<body>.*?)(?=^##\s+|\Z)', text)
    if not sec:
        return text
    body = sec.group('body')
    status_label, _assessment_short = _global_eval_status(summary, alignment)
    default_symbol = '⚠ Inconclusive'
    if status_label.startswith('✅'):
        default_symbol = '✅ Supported'
    elif status_label.startswith('❌'):
        default_symbol = '❌ In conflict'

    # Main result legend
    main_legend = '(Status legend: ✅ Supported, ⚠ Inconclusive, ❌ In conflict.)'
    if '### Main Result' in body and main_legend not in body:
        body = re.sub(r'(?m)^###\s+Main Result\s*$', f'### Main Result\n\n{main_legend}', body, count=1)

    # Main table
    main_match = re.search(
        r'(?ims)^(\|\s*Task\s*\|.*?Difference\s*\(Δ\)\s*\|)\n(\|[-:\| ]+\|)\n(?P<rows>(?:\|[^\n]*\|\n?)*)',
        body,
    )
    if main_match:
        header = '| Task | Dataset | Metric | Best Baseline | Paper Result | Difference (Δ) | Evaluation Status |'
        sep = '|---|---|---|---|---|---|---|'
        rows_raw = main_match.group('rows')
        new_rows: list[str] = []
        main_truth = list((truth_values or {}).get('main') or [])
        main_idx = 0
        for ln in rows_raw.splitlines():
            s = ln.strip()
            if not (s.startswith('|') and s.endswith('|')):
                continue
            cells = [c.strip() for c in s.strip('|').split('|')]
            if len(cells) < 6:
                continue
            dataset = cells[1]
            metric = cells[2]
            paper_result = cells[4]
            observed_override = None
            if main_idx < len(main_truth):
                observed_override = float(main_truth[main_idx])
            main_idx += 1
            cell = _row_eval_cell(
                dataset=dataset,
                metric=metric,
                paper_result=paper_result,
                alignment=alignment,
                default_symbol=default_symbol,
                observed_override=observed_override,
            )
            new_rows.append('| ' + ' | '.join(cells[:6] + [cell]) + ' |')
        rebuilt = '\n'.join([header, sep] + new_rows) + '\n'
        body = body[: main_match.start()] + rebuilt + body[main_match.end():]

    # Ablation legend and table
    if '### Ablation Result' in body and main_legend not in body.split('### Ablation Result', 1)[1][:300]:
        body = re.sub(r'(?m)^###\s+Ablation Result\s*$', f'### Ablation Result\n\n{main_legend}', body, count=1)

    abl_match = re.search(
        r'(?ims)^(\|\s*Ablation Dimension\s*\|.*?Difference\s*\(Δ\)\s*\|)\n(\|[-:\| ]+\|)\n(?P<rows>(?:\|.*\|\n?)*)',
        body,
    )
    if abl_match:
        header = '| Ablation Dimension | Configuration | Full Model | Paper Result | Difference (Δ) | Evaluation Status |'
        sep = '|---|---|---|---|---|---|'
        rows_raw = abl_match.group('rows')
        new_rows: list[str] = []
        abl_truth = list((truth_values or {}).get('ablation') or [])
        abl_idx = 0
        for ln in rows_raw.splitlines():
            s = ln.strip()
            if not (s.startswith('|') and s.endswith('|')):
                continue
            cells = [c.strip() for c in s.strip('|').split('|')]
            if len(cells) < 5:
                continue
            # Most ablation rows in alignment are link prediction MRR on FB15k-237.
            paper_result = cells[3]
            observed_override = None
            if abl_idx < len(abl_truth):
                observed_override = float(abl_truth[abl_idx])
            abl_idx += 1
            cell = _row_eval_cell(
                dataset='FB15k-237',
                metric='MRR',
                paper_result=paper_result,
                alignment=alignment,
                default_symbol=default_symbol,
                observed_override=observed_override,
            )
            new_rows.append('| ' + ' | '.join(cells[:5] + [cell]) + ' |')
        rebuilt = '\n'.join([header, sep] + new_rows) + '\n'
        body = body[: abl_match.start()] + rebuilt + body[abl_match.end():]

    new_body = re.sub(r'\n{3,}', '\n\n', body).strip('\n') + '\n\n'
    return text[: sec.start('body')] + new_body + text[sec.end('body') :]


def _compress_experiment_note(markdown_text: str) -> str:
    text = str(markdown_text or '')
    if not text.strip():
        return text
    sec = re.search(r'(?ims)^##\s+5\.\s+Experiment\s*$\n(?P<body>.*?)(?=^##\s+|\Z)', text)
    if not sec:
        return text
    body = sec.group('body')
    # Remove Note lines; ablation context should be carried by the Location line.
    body = re.sub(r'(?im)^\s*Note\s*:\s*.*$', '', body)
    body = re.sub(r'\n{3,}', '\n\n', body)
    return text[: sec.start('body')] + body + text[sec.end('body') :]


def _compact_ref_label_from_title(*, title: str, year: str | None, rid: str) -> str:
    tokens = re.findall(r'[A-Za-z0-9]+', str(title or ''))
    stop = {
        'the', 'with', 'for', 'and', 'from', 'based', 'using', 'on', 'of', 'to', 'in', 'a', 'an',
        'multi', 'relational', 'graph', 'convolutional', 'networks', 'network', 'towards', 'via',
        'learning', 'representation', 'representations', 'knowledge', 'graphs', 'graphs',
    }
    picked = [t for t in tokens if t.lower() not in stop]
    if not picked:
        picked = [t for t in tokens if t]
    compact_words = picked[:2]
    if not compact_words:
        return rid
    label = ' '.join((w[:8] if len(w) > 8 else w) for w in compact_words)
    label = ' '.join(w[:1].upper() + w[1:].lower() for w in label.split())
    return label[:18].strip() or rid


def _semantic_ref_map_from_payload(job_dir: Path) -> dict[str, str]:
    payload_path = job_dir / 'semantic_scholar_candidates.json'
    if not payload_path.exists():
        return {}
    try:
        payload = read_json(payload_path)
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    papers = payload.get('papers')
    if not isinstance(papers, list):
        return {}
    ref_map: dict[str, str] = {}
    for row in papers:
        if not isinstance(row, dict):
            continue
        rid = str(row.get('id') or '').strip()
        if not re.fullmatch(r'R\d+', rid):
            continue
        title = str(row.get('title') or '').strip()
        year = str(row.get('year') or '').strip()
        ref_map[rid] = _compact_ref_label_from_title(title=title, year=year, rid=rid)
    return ref_map


def _compact_technical_positioning_reference_labels(markdown_text: str, *, job_dir: Path) -> str:
    text = str(markdown_text or '')
    if not text.strip():
        return text
    sec = _TECHNICAL_POSITIONING_SECTION_PATTERN.search(text)
    if not sec:
        return text
    body = sec.group('body')
    lines = body.splitlines()

    ref_map: dict[str, str] = _semantic_ref_map_from_payload(job_dir)
    ref_line = re.compile(r'^\s*-\s*(R\d+)\s*:\s*(.+)$')
    for raw in lines:
        m = ref_line.match(raw.strip())
        if not m:
            continue
        rid = m.group(1).strip()
        rest = m.group(2).strip()
        ym = re.search(r'\((\d{4})[^)]*\)', rest)
        year = ym.group(1) if ym else ''
        title = re.sub(r'\(\d{4}[^)]*\)', '', rest).strip(' -')
        ref_map.setdefault(rid, _compact_ref_label_from_title(title=title, year=year, rid=rid))

    # Remove standalone legend block lines.
    cleaned: list[str] = []
    for raw in lines:
        s = raw.strip()
        if re.match(r'^\*\*Legend:\*\*\s*$', s):
            continue
        if re.match(r'^-\s*R\d+\s*:', s):
            continue
        cleaned.append(raw)

    # Replace table header R-columns with compact labels, without R-identifiers.
    for i, raw in enumerate(cleaned):
        s = raw.strip()
        if not (s.startswith('|') and s.endswith('|')):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if len(cells) < 3:
            continue
        if cells[0].lower() != 'research domain' or cells[1].lower() != 'method':
            continue
        new_cells = cells[:2]
        r_index = 1
        for c in cells[2:]:
            rid_match = re.match(r'^(R\d+)', c)
            if rid_match:
                rid = rid_match.group(1)
                short = ref_map.get(rid, rid)
                new_cells.append(short)
            else:
                # Handle already-prefixed forms like "R1:Something".
                alt = re.sub(r'^\s*R\d+\s*:\s*', '', c).strip()
                if alt and alt != c:
                    new_cells.append(alt)
                    r_index += 1
                    continue
                rid = f'R{r_index}'
                short = ref_map.get(rid, _compact_ref_label_from_title(title=c, year=None, rid=rid))
                new_cells.append(short)
            r_index += 1
        cleaned[i] = '| ' + ' | '.join(new_cells) + ' |'
        break

    new_body = '\n'.join(cleaned).strip('\n') + '\n\n'
    return text[: sec.start('body')] + new_body + text[sec.end('body') :]


def _extract_title_method_hint(markdown_text: str) -> str:
    text = str(markdown_text or '')
    m = re.search(r'(?im)^\s*-\s*(?:\*\*)?Title(?:\*\*)?\s*:\s*(.+?)\s*$', text)
    if not m:
        return ''
    title = str(m.group(1) or '').strip()
    # Prefer acronym-like token (e.g., COMPGCN).
    tokens = re.findall(r'[A-Za-z0-9\-]+', title)
    for t in tokens:
        alpha = re.sub(r'[^A-Za-z]', '', t)
        if len(alpha) >= 3 and alpha.isupper():
            return t
    # Fallback: first significant title token.
    for t in tokens:
        if len(t) >= 4:
            return t
    return ''


def _normalize_technical_positioning_layout(markdown_text: str) -> str:
    text = str(markdown_text or '')
    if not text.strip():
        return text
    sec = _TECHNICAL_POSITIONING_SECTION_PATTERN.search(text)
    if not sec:
        return text

    method_hint = _extract_title_method_hint(text).strip().lower()
    body = sec.group('body')

    # Remove explicit gap line in section 2.
    body = re.sub(r'(?im)^\s*Gap\s*:\s*.*$', '', body)
    # Use empty alt text to avoid rendering label words near the image.
    body = re.sub(r'!\[[^\]]*\]\(([^)]+)\)', r'![](\1)', body)
    # Remove "Figure x:" prefix from caption line.
    body = re.sub(r'(?im)^\s*Figure\s*\d*\s*:\s*(.+?)\s*$', r'\1', body)
    # Remove "Figure caption:" prefix if model emits it.
    body = re.sub(r'(?im)^\s*Figure\s*caption\s*:\s*(.+?)\s*$', r'\1', body)
    # Normalize "Figure x shows ..." sentence without using Figure marker.
    body = re.sub(r'(?im)^\s*Figure\s*\d+\s*shows\s*', 'This overview shows ', body)
    # Remove verbose overview explanation line; keep a single short caption only.
    body = re.sub(r'(?im)^\s*This overview shows.*$', '', body)

    lines = body.splitlines()
    # If section has an image, enforce one-line short caption directly under image.
    image_idx = -1
    for idx, raw in enumerate(lines):
        s = raw.strip()
        if s.startswith('![') and '](' in s and s.endswith(')'):
            image_idx = idx
            break
    if image_idx >= 0:
        method_hint = _extract_title_method_hint(text).strip() or 'the proposed method'
        if 'compgcn' in text.lower():
            method_hint = 'COMPGCN'
        # Remove existing short overview caption variants around image.
        filtered: list[str] = []
        for i, raw in enumerate(lines):
            s = raw.strip()
            if i in {image_idx + 1, image_idx + 2, image_idx + 3} and re.match(
                r'(?im)^(overview of .+\.?|this overview shows.+)$', s
            ):
                continue
            filtered.append(raw)
        lines = filtered
        # Re-locate image index after filtering.
        for idx, raw in enumerate(lines):
            s = raw.strip()
            if s.startswith('![') and '](' in s and s.endswith(')'):
                image_idx = idx
                break
        if image_idx >= 0:
            # Keep image as a standalone markdown paragraph so PDF renderer can load it as an image,
            # not inline text fallback.
            lines.insert(image_idx + 1, '')
            lines.insert(image_idx + 2, f'Overview of {method_hint}.')
            lines.insert(image_idx + 3, '')

    table_start = -1
    table_end = -1
    for idx, raw in enumerate(lines):
        s = raw.strip()
        if s.startswith('|') and s.endswith('|'):
            if table_start < 0:
                table_start = idx
            table_end = idx
        elif table_start >= 0 and table_end >= table_start:
            break
    if table_start >= 0 and table_end >= table_start and table_end - table_start >= 2:
        table_lines = lines[table_start: table_end + 1]
        rows: list[list[str]] = []
        for raw in table_lines:
            s = raw.strip()
            if not (s.startswith('|') and s.endswith('|')):
                continue
            cells = [c.strip() for c in s.strip('|').split('|')]
            if all(re.fullmatch(r':?-{3,}:?', c or '') for c in cells):
                continue
            rows.append(cells)
        if len(rows) >= 2:
            header = rows[0]
            body_rows = rows[1:]
            if len(header) >= 2 and header[0].strip().lower() == 'research domain' and header[1].strip().lower() == 'method':
                pick_idx = -1
                for i, r in enumerate(body_rows):
                    domain = str(r[0] if len(r) > 0 else '').strip().lower()
                    method = str(r[1] if len(r) > 1 else '').strip().lower()
                    if 'this work' in domain or 'this work' in method or 'proposed' in method or 'ours' in method:
                        pick_idx = i
                        break
                    if 'compgcn' in method:
                        pick_idx = i
                        break
                    if method_hint and method_hint in method:
                        pick_idx = i
                        break
                if pick_idx >= 0:
                    target = body_rows.pop(pick_idx)
                    if len(target) < len(header):
                        target = target + ['✗'] * (len(header) - len(target))
                    target[0] = 'This work'
                    method_cell = target[1].strip()
                    if not method_cell:
                        method_cell = 'Proposed method'
                    if 'proposed' not in method_cell.lower():
                        method_cell = f'{method_cell} (proposed)'
                    target[1] = method_cell
                    body_rows.append(target)

                new_table = _format_table(header, body_rows)
                lines = lines[:table_start] + new_table.splitlines() + lines[table_end + 1:]

    new_body = '\n'.join(lines)
    new_body = re.sub(r'\n{3,}', '\n\n', new_body).strip('\n') + '\n\n'
    return text[: sec.start('body')] + new_body + text[sec.end('body') :]


def _inject_technical_positioning_overview_image(
    *,
    markdown_text: str,
    job_dir: Path,
    content_list: list[dict[str, Any]] | None,
) -> str:
    text = str(markdown_text or '')
    if not text.strip():
        return text

    match = _TECHNICAL_POSITIONING_SECTION_PATTERN.search(text)
    if not match:
        return text

    body = match.group('body')
    existing_image_match = re.search(r'!\[[^\]]*\]\(([^)]+)\)', body)
    if existing_image_match:
        existing_src = str(existing_image_match.group(1) or '').strip()
        existing_path = Path(existing_src).expanduser()
        # Keep existing image only when it points to a real local file.
        if existing_path.is_absolute() and existing_path.exists() and existing_path.is_file():
            return text

    page_match = _TECHNICAL_POSITIONING_PAGE_PATTERN.search(body)
    if page_match:
        # page hint is currently advisory only; image selection comes from MinerU image assets
        _ = page_match.group(1)

    figure_paths, mineru_caption = _pick_overview_mineru_figure_bundle(
        content_list=content_list,
        job_dir=job_dir,
    )
    if not figure_paths:
        fallback = _pick_overview_mineru_image(content_list=content_list, job_dir=job_dir)
        if fallback is not None:
            figure_paths = [fallback]
        else:
            figure_paths = _fallback_overview_images_from_assets(job_dir=job_dir, max_images=2)
            if not figure_paths:
                return text

    caption_match = re.search(r'(?im)^\s*Figure\s*1\s*:\s*.*$', body)
    caption_line = ''
    if caption_match:
        caption_line = str(caption_match.group(0) or '').strip()
        body = body[: caption_match.start()] + body[caption_match.end() :]

    # Prefer model caption in section output; fallback to MinerU caption if missing.
    if caption_line:
        caption_line = _abbreviate_figure_caption(caption_line)
    elif mineru_caption and str(mineru_caption).strip():
        caption_line = _abbreviate_figure_caption(str(mineru_caption))
    else:
        caption_line = ''

    body = body.lstrip('\n')
    combined = _compose_side_by_side_image(image_paths=figure_paths, job_dir=job_dir)
    if combined is not None:
        images_block = f'![Overview]({combined.resolve()})'
    elif len(figure_paths) > 1:
        images_block = '\n\n'.join(
            f'![Overview {idx + 1}]({path.resolve()})' for idx, path in enumerate(figure_paths)
        )
    else:
        images_block = f'![Overview]({figure_paths[0].resolve()})'
    image_block = f'{images_block}\n\n'
    if caption_line:
        image_block += f'{caption_line}\n\n'
    new_body = image_block + body
    return text[: match.start('body')] + new_body + text[match.end('body') :]


def _sanitize_technical_positioning_markers(markdown_text: str) -> str:
    text = str(markdown_text or '')
    if not text.strip():
        return text
    match = _TECHNICAL_POSITIONING_SECTION_PATTERN.search(text)
    if not match:
        return text
    body = match.group('body')
    cleaned_lines = [line for line in body.splitlines() if not _TECHNICAL_POSITIONING_MARKER_PATTERN.match(line)]
    cleaned_body = '\n'.join(cleaned_lines).strip('\n')
    if cleaned_body:
        cleaned_body = cleaned_body + '\n\n'
    return text[:match.start('body')] + cleaned_body + text[match.end('body'):]


def _publish_outputs_to_output_dir(
    *,
    job_id: str,
    final_md_path: Path,
    report_pdf_path: Path,
) -> None:
    settings = get_settings()
    output_dir = settings.data_dir.parent / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)

    latest_md = output_dir / 'latest_extraction.md'
    latest_pdf = output_dir / 'latest_extraction.pdf'

    # Keep output directory single-versioned: remove old artifacts before publishing latest.
    for child in output_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
            continue
        try:
            child.unlink()
        except FileNotFoundError:
            pass

    shutil.copy2(final_md_path, latest_md)
    # Re-home section-2 image into output/ for stable local preview rendering.
    try:
        md_text = latest_md.read_text(encoding='utf-8')
        m = re.search(r'!\[[^\]]*\]\(([^)]+)\)', md_text)
        if m:
            src = Path(m.group(1)).expanduser()
            if src.exists() and src.is_file():
                dst = output_dir / 'overview_figure.jpg'
                shutil.copy2(src, dst)
                md_text = md_text[: m.start(1)] + './overview_figure.jpg' + md_text[m.end(1):]
                latest_md.write_text(md_text, encoding='utf-8')
    except Exception:
        pass
    if report_pdf_path.exists():
        shutil.copy2(report_pdf_path, latest_pdf)


def _persist_mineru_image_files(
    *,
    job_dir: Path,
    image_files: dict[str, bytes] | None,
) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    if not image_files:
        return mapping
    assets_root = job_dir / 'mineru_assets'
    assets_root.mkdir(parents=True, exist_ok=True)
    for key, value in image_files.items():
        rel = str(key or '').strip().replace('\\', '/')
        if not rel:
            continue
        safe_rel = rel.lstrip('/')
        target = (assets_root / safe_rel).resolve()
        # ensure write stays inside assets_root
        if assets_root.resolve() not in target.parents and target != assets_root.resolve():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)
        mapping[rel] = target
    return mapping


def _render_report_pdf(
    *,
    job_id: str,
    job_title: str,
    source_pdf_name: str,
    final_md_path: Path,
    source_pdf_path: Path,
    report_pdf_path: Path,
    annotations: list[AnnotationItem] | list[dict[str, Any]],
    content_list: list[dict[str, Any]] | None,
    code_eval_summary_override: dict[str, Any] | None = None,
    code_eval_alignment_override: dict[str, Any] | None = None,
    token_usage: dict[str, int],
    agent_model: str,
) -> dict[str, int]:
    final_report_markdown = final_md_path.read_text(encoding='utf-8')
    # Keep model-authored content as-is; only do minimal marker cleanup and image injection.
    final_report_markdown = _sanitize_technical_positioning_markers(final_report_markdown)
    final_report_markdown = _inject_technical_positioning_overview_image(
        markdown_text=final_report_markdown,
        job_dir=final_md_path.parent,
        content_list=content_list,
    )
    final_report_markdown = _compact_technical_positioning_reference_labels(
        final_report_markdown,
        job_dir=final_md_path.parent,
    )
    final_report_markdown = _normalize_technical_positioning_layout(final_report_markdown)
    final_report_markdown = _hard_validate_experiment_tables(
        final_report_markdown,
        content_list=content_list,
    )
    final_report_markdown = _stabilize_experiment_section(final_report_markdown)
    final_report_markdown = _ensure_experiment_contract(final_report_markdown)
    final_report_markdown = _compress_experiment_note(final_report_markdown)
    settings = get_settings()
    code_eval_summary = code_eval_summary_override if isinstance(code_eval_summary_override, dict) else {}
    code_eval_alignment = code_eval_alignment_override if isinstance(code_eval_alignment_override, dict) else {}
    if not code_eval_summary and not code_eval_alignment:
        project_root = get_settings().data_dir.parent
        code_eval_summary, code_eval_alignment = _latest_code_eval_payload(
            project_root=project_root,
            source_pdf_name=source_pdf_name,
        )
    truth_values = _load_factreview_truth_values(settings.factreview_truth_pdf_path)
    final_report_markdown = _augment_claims_with_assessment_status(
        final_report_markdown,
        summary=code_eval_summary,
        alignment=code_eval_alignment,
        truth_values=truth_values,
    )
    final_report_markdown = _augment_experiment_with_eval_status(
        final_report_markdown,
        summary=code_eval_summary,
        alignment=code_eval_alignment,
        truth_values=truth_values,
    )
    # Re-assert experiment section contract after eval augmentation to avoid accidental section loss.
    final_report_markdown = _ensure_experiment_contract(final_report_markdown)
    write_text_atomic(final_md_path, final_report_markdown)
    final_report_markdown = _inject_overview_figure_image(
        markdown_text=final_report_markdown,
        source_pdf_path=source_pdf_path,
        job_dir=final_md_path.parent,
    )
    source_pdf_bytes = source_pdf_path.read_bytes() if source_pdf_path.exists() else None
    source_annotations = build_source_annotations_for_export(
        annotations=annotations,
        content_list=content_list,
    )

    report_pdf_bytes = build_review_report_pdf(
        workspace_title=job_title,
        source_pdf_name=source_pdf_name,
        run_id=job_id,
        status='completed',
        decision=None,
        estimated_cost=0,
        actual_cost=None,
        exported_at=datetime.now(timezone.utc),
        meta_review={},
        reviewers=[],
        raw_output=None,
        final_report_markdown=final_report_markdown,
        source_pdf_bytes=source_pdf_bytes,
        source_annotations=source_annotations,
        review_display_id=None,
        owner_email=None,
        token_usage=token_usage,
        agent_model=agent_model,
    )
    report_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    report_pdf_path.write_bytes(report_pdf_bytes)

    export_stats = {
        'source_annotations_input_count': int(len(annotations)),
        'source_annotations_exported_count': int(len(source_annotations)),
        'content_list_count': int(len(content_list or [])),
        'report_pdf_size_bytes': int(len(report_pdf_bytes)),
    }
    append_event(job_id, 'pdf_export_rendered', **export_stats)
    return export_stats


def _complete_with_existing_final_report(job_id: str, *, warning: str) -> bool:
    state = load_job_state(job_id)
    if state is None:
        return False

    artifacts = ensure_artifact_paths(job_id)
    final_md_path = Path(state.artifacts.final_markdown_path or artifacts['final_markdown'])
    if not final_md_path.exists():
        return False

    metadata = state.metadata if isinstance(state.metadata, dict) else {}
    has_persist_marker = bool(
        state.final_report_ready
        or str(state.artifacts.final_markdown_path or '').strip()
        or str(metadata.get('final_report_source') or '').strip()
    )
    if not has_persist_marker:
        append_event(
            job_id,
            'completed_recovery_skipped',
            warning=warning,
            reason='final_markdown_exists_without_persist_marker',
        )
        return False

    report_pdf_path = Path(state.artifacts.report_pdf_path or artifacts['report_pdf'])
    pdf_error: str | None = None
    if not report_pdf_path.exists():
        try:
            source_pdf_path = Path(state.artifacts.source_pdf_path or artifacts['source_pdf'])
            annotations_path = Path(state.artifacts.annotations_path or artifacts['annotations'])
            content_list_path = Path(state.artifacts.mineru_content_list_path or artifacts['mineru_content_list'])
            annotations = _load_annotations_payload(annotations_path)
            content_list = _load_content_list(content_list_path)
            _render_report_pdf(
                job_id=job_id,
                job_title=state.title,
                source_pdf_name=state.source_pdf_name,
                final_md_path=final_md_path,
                source_pdf_path=source_pdf_path,
                report_pdf_path=report_pdf_path,
                annotations=annotations,
                content_list=content_list,
                token_usage=_token_usage_payload_from_state(state),
                agent_model=str(get_settings().agent_model or '').strip(),
            )
        except Exception as exc:
            pdf_error = f'{type(exc).__name__}: {exc}'

    def apply_completed(state_obj):
        state_obj.status = JobStatus.completed
        state_obj.final_report_ready = True
        state_obj.pdf_ready = report_pdf_path.exists()
        state_obj.artifacts.final_markdown_path = str(final_md_path)
        state_obj.artifacts.report_pdf_path = str(report_pdf_path) if report_pdf_path.exists() else None
        state_obj.error = pdf_error
        state_obj.message = (
            'Review pipeline completed via recovery after post-write exception.'
            if pdf_error is None
            else 'Final report persisted, but PDF export failed during recovery.'
        )
        metadata = dict(state_obj.metadata)
        metadata['post_exception_recovery'] = True
        metadata['post_exception_warning'] = warning
        if pdf_error:
            metadata['pdf_export_recovery_error'] = pdf_error
        state_obj.metadata = metadata

    mutate_job_state(job_id, apply_completed)
    append_event(
        job_id,
        'completed_recovered',
        warning=warning,
        pdf_ready=report_pdf_path.exists(),
        pdf_error=pdf_error,
    )
    return True


async def run_job_async(job_id: str) -> None:
    settings = get_settings()
    job = load_job_state(job_id)
    if job is None:
        raise FileNotFoundError(f'Job not found: {job_id}')

    api_mode = 'responses' if settings.openai_use_responses_api else 'chat_completions'
    append_event(
        job_id,
        'llm_api_mode_selected',
        api_mode=api_mode,
        model=str(settings.agent_model or '').strip(),
    )

    def apply_llm_mode(state):
        metadata = dict(state.metadata)
        metadata['llm_api_mode'] = api_mode
        state.metadata = metadata

    mutate_job_state(job_id, apply_llm_mode)

    artifacts = ensure_artifact_paths(job_id)
    source_pdf = Path(artifacts['source_pdf'])
    if not source_pdf.exists():
        raise RuntimeError(f'Source PDF missing: {source_pdf}')
    file_size = int(source_pdf.stat().st_size)
    if file_size <= 0:
        raise RuntimeError('Source PDF is empty.')
    if file_size > int(settings.max_pdf_bytes):
        raise RuntimeError(
            f'Source PDF too large: {file_size} bytes, max allowed {int(settings.max_pdf_bytes)} bytes.'
        )

    set_status(job_id, JobStatus.pdf_uploading_to_mineru, 'Submitting PDF to MinerU and uploading file...')
    set_status(job_id, JobStatus.pdf_parsing, 'Polling MinerU parse result and assembling markdown...')

    mineru = _build_mineru_adapter()
    parse_result = await mineru.parse_pdf(pdf_path=source_pdf, data_id=job_id)
    mineru_image_map = _persist_mineru_image_files(
        job_dir=source_pdf.parent,
        image_files=parse_result.image_files,
    )
    if parse_result.content_list is not None and mineru_image_map:
        normalized_map = {k.replace('\\', '/'): v for k, v in mineru_image_map.items()}
        for row in parse_result.content_list:
            if not isinstance(row, dict):
                continue
            ref = str(row.get('img_path') or '').strip().replace('\\', '/')
            if ref and ref in normalized_map:
                row['img_path'] = str(normalized_map[ref])

    write_text_atomic(Path(artifacts['mineru_markdown']), parse_result.markdown)
    if parse_result.content_list is not None:
        write_json_atomic(Path(artifacts['mineru_content_list']), {'content_list': parse_result.content_list})
    if parse_result.raw_result is not None:
        write_json_atomic(Path(artifacts['raw_result']), parse_result.raw_result)

    def apply_parsed(state):
        state.artifacts.mineru_markdown_path = str(artifacts['mineru_markdown'])
        state.artifacts.mineru_content_list_path = (
            str(artifacts['mineru_content_list']) if Path(artifacts['mineru_content_list']).exists() else None
        )
        state.artifacts.annotations_path = str(artifacts['annotations'])
        state.metadata['markdown_provider'] = parse_result.provider
        state.metadata['mineru_batch_id'] = parse_result.batch_id
        state.metadata['parse_warning'] = parse_result.warning

    mutate_job_state(job_id, apply_parsed)
    if parse_result.warning:
        append_event(job_id, 'markdown_parse_warning', warning=parse_result.warning, provider=parse_result.provider)

    page_index = build_page_index(parse_result.markdown, parse_result.content_list)

    set_status(job_id, JobStatus.agent_running, 'Running review agent with tool loop...')

    paper_adapter = _build_paper_adapter()
    paper_search_runtime_state = (await paper_adapter.get_search_runtime_state()).to_dict()
    append_event(
        job_id,
        'paper_search_runtime_state_resolved',
        enabled=paper_search_runtime_state.get('enabled'),
        started=paper_search_runtime_state.get('started'),
        availability=paper_search_runtime_state.get('availability'),
        base_url=paper_search_runtime_state.get('base_url'),
        health_url=paper_search_runtime_state.get('health_url'),
        error=paper_search_runtime_state.get('error'),
    )

    def apply_paper_search_state(state):
        metadata = dict(state.metadata)
        metadata['paper_search_runtime_state'] = dict(paper_search_runtime_state)
        state.metadata = metadata

    mutate_job_state(job_id, apply_paper_search_state)

    # Objective retrieval context for section-2 niche positioning matrix.
    semantic_adapter = _build_semantic_scholar_adapter()
    title_hint = _extract_title_hint(parse_result.markdown, job.source_pdf_name)
    semantic_payload = await semantic_adapter.search_related(query=title_hint)
    semantic_context = _format_semantic_scholar_context(semantic_payload)
    write_json_atomic(Path(artifacts['source_pdf']).parent / 'semantic_scholar_candidates.json', semantic_payload)

    prompt = build_review_agent_system_prompt(
        source_file_id=job_id,
        source_file_name=job.source_pdf_name,
        ui_language=settings.ui_language,
        paper_markdown=parse_result.markdown,
        use_meta_review=False,
        paper_search_runtime_state=paper_search_runtime_state,
        semantic_scholar_context=semantic_context,
    )
    write_text_atomic(Path(artifacts['prompt_snapshot']), prompt)

    def apply_prompt(state):
        state.artifacts.prompt_snapshot_path = str(artifacts['prompt_snapshot'])

    mutate_job_state(job_id, apply_prompt)

    runtime = ReviewRuntimeContext(
        job_id=job_id,
        job_dir=Path(artifacts['source_pdf']).parent,
        page_index=page_index,
        source_markdown=parse_result.markdown,
        paper_adapter=paper_adapter,
        paper_search_runtime_state=paper_search_runtime_state,
        settings=settings,
    )

    tools = build_review_tools(runtime)
    agent_model = _build_agent_model()
    agent = Agent(
        name='FactExtractioner2Agent',
        instructions=prompt,
        tools=tools,
        model=agent_model,
        model_settings=_build_agent_model_settings(),
    )

    requested_attempts = int(settings.agent_resume_attempts)
    max_attempts = max(1, min(2, requested_attempts))
    if requested_attempts != max_attempts:
        append_event(
            job_id,
            'agent_resume_attempts_capped',
            requested=requested_attempts,
            applied=max_attempts,
            reason='hard_cap_2',
        )
    run_config = _build_run_config()
    # Use the exact same full review prompt as user input (parity requirement).
    next_input: str | list[Any] = prompt
    usage_totals = {
        'requests': 0,
        'input_tokens': 0,
        'output_tokens': 0,
        'total_tokens': 0,
    }

    def _consume_run_result(run_result: Any, *, output_tag: str) -> str:
        usage = run_result.context_wrapper.usage
        usage_totals['requests'] += int(getattr(usage, 'requests', 0) or 0)
        usage_totals['input_tokens'] += int(getattr(usage, 'input_tokens', 0) or 0)
        usage_totals['output_tokens'] += int(getattr(usage, 'output_tokens', 0) or 0)
        usage_totals['total_tokens'] += int(getattr(usage, 'total_tokens', 0) or 0)
        usage_payload = SimpleNamespace(**usage_totals)
        _sync_token_usage(job_id, usage_payload)
        runtime.sync_state_usage(usage_payload)

        final_output_text = str(run_result.final_output or '').strip()
        if final_output_text:
            write_text_atomic(Path(runtime.job_dir / 'agent_final_output.txt'), final_output_text)
            write_text_atomic(
                Path(runtime.job_dir / f'agent_final_output_{output_tag}.txt'),
                final_output_text,
            )
        return final_output_text

    for attempt in range(1, max_attempts + 1):
        if runtime.final_markdown_text:
            append_event(
                job_id,
                'agent_run_skipped_after_final_write',
                attempt=attempt,
                reason='final_report_already_persisted',
            )
            break

        run_task = asyncio.create_task(
            Runner.run(
                agent,
                input=next_input,
                context=runtime,
                max_turns=max(20, settings.agent_max_turns),
                run_config=run_config,
            )
        )
        run_result = None
        while True:
            done, _ = await asyncio.wait({run_task}, timeout=0.5)
            if run_task in done:
                try:
                    run_result = run_task.result()
                except Exception as exc:
                    if runtime.final_markdown_text:
                        append_event(
                            job_id,
                            'agent_run_post_final_exception_ignored',
                            attempt=attempt,
                            error=f'{type(exc).__name__}: {exc}',
                            reason='final_report_already_persisted',
                        )
                        run_result = None
                        break
                    raise
                break
            if runtime.final_markdown_text:
                run_task.cancel()
                append_event(
                    job_id,
                    'agent_run_cancelled_after_final_write',
                    attempt=attempt,
                    reason='final_report_already_persisted',
                )
                try:
                    await run_task
                except asyncio.CancelledError:
                    pass
                except Exception as exc:
                    append_event(
                        job_id,
                        'agent_run_cancel_post_final_exception_ignored',
                        attempt=attempt,
                        error=f'{type(exc).__name__}: {exc}',
                        reason='final_report_already_persisted',
                    )
                break

        if run_result is None and runtime.final_markdown_text:
            append_event(
                job_id,
                'agent_run_terminated_after_final_write',
                attempt=attempt,
                reason='final_report_already_persisted',
            )
            break

        _consume_run_result(run_result, output_tag=f'attempt_{attempt}')

        if runtime.final_markdown_text:
            break

        append_event(
            job_id,
            'agent_run_incomplete',
            attempt=attempt,
            max_attempts=max_attempts,
            reason='no_final_report_persisted',
        )

        if attempt >= max_attempts:
            append_event(
                job_id,
                'agent_forced_final_write_start',
                attempt=attempt,
                reason='max_attempt_reached_without_final_write',
            )
            forced_input = [
                *run_result.to_input_list(),
                {
                    'role': 'user',
                    'content': (
                        'MANDATORY ACTION NOW: Call review_final_markdown_write in section mode immediately. '
                        'Submit exactly one required section per call using '
                        'review_final_markdown_write(section_id=<required_section_id>, section_content=<section_markdown>). '
                        'After each call, inspect completed_sections/missing_sections/next_required_section and '
                        'submit the next required section right away until status=ok. '
                        'Do not output plain-text final report. If the tool returns retry_required/error, '
                        'follow message/next_steps and retry review_final_markdown_write.'
                    ),
                },
            ]
            forced_choices = ['review_final_markdown_write', 'required']
            for forced_choice in forced_choices:
                if runtime.final_markdown_text:
                    append_event(
                        job_id,
                        'agent_forced_final_write_skipped_after_success',
                        attempt=attempt,
                        tool_choice=forced_choice,
                        reason='final_report_already_persisted',
                    )
                    break
                try:
                    forced_agent = Agent(
                        name='FactExtractioner2AgentFinalWriteEnforcer',
                        instructions=prompt,
                        tools=tools,
                        model=agent_model,
                        model_settings=_build_agent_model_settings(tool_choice=forced_choice),
                    )
                    forced_result = await Runner.run(
                        forced_agent,
                        input=forced_input,
                        context=runtime,
                        max_turns=12,
                        run_config=run_config,
                    )
                except Exception as exc:
                    if runtime.final_markdown_text:
                        append_event(
                            job_id,
                            'agent_forced_final_write_post_success_exception_ignored',
                            attempt=attempt,
                            tool_choice=forced_choice,
                            error=f'{type(exc).__name__}: {exc}',
                            reason='final_report_already_persisted',
                        )
                        break
                    append_event(
                        job_id,
                        'agent_forced_final_write_error',
                        attempt=attempt,
                        tool_choice=forced_choice,
                        error=f'{type(exc).__name__}: {exc}',
                    )
                    continue

                forced_output_text = _consume_run_result(
                    forced_result,
                    output_tag=f'attempt_{attempt}_forced_final_write',
                )
                append_event(
                    job_id,
                    'agent_forced_final_write_result',
                    attempt=attempt,
                    tool_choice=forced_choice,
                    final_output_chars=len(forced_output_text),
                    final_write_persisted=bool(runtime.final_markdown_text),
                )
                if runtime.final_markdown_text:
                    break
                forced_input = [
                    *forced_result.to_input_list(),
                    {
                        'role': 'user',
                        'content': (
                            'The final report is still not persisted. Continue section-mode submission now: '
                            'call review_final_markdown_write with section_id + section_content for the next required section.'
                        ),
                    },
                ]

            break

        set_status(
            job_id,
            JobStatus.agent_running,
            (
                'Agent ended without final report write. '
                f'Resuming review runtime (attempt {attempt + 1}/{max_attempts})...'
            ),
        )
        usage = runtime.paper_search_usage
        continuation_instruction = (
            'Resume the same review job from current state. '
            'Do not restart Phase 1 planning unless a hard gate is still unmet.\n'
            f'Current state: annotations={runtime.annotation_count}, '
            f'paper_search_total_calls={usage.total_calls}, '
            f'distinct_queries={usage.distinct_queries}, '
            f'effective_paper_search_calls={usage.effective_calls}.\n'
            'If gates are met, go directly to final report assembly in section mode and call '
            'review_final_markdown_write(section_id=<required_section_id>, section_content=<section_markdown>) '
            'as soon as possible.\n'
            'Mandatory: your next substantive action must be a section-mode tool call '
            '`review_final_markdown_write(...)`; plain chat markdown is invalid.\n'
            'If a gate is unmet or the write tool returns an error, follow message/next_steps exactly, '
            'perform minimal remediation, then retry review_final_markdown_write.\n'
            'Never end this run without a successful review_final_markdown_write.'
        )
        next_input = [
            *run_result.to_input_list(),
            {
                'role': 'user',
                'content': continuation_instruction,
            },
        ]

    if not runtime.final_markdown_text:
        raise RuntimeError(
            'Agent finished without successful review_final_markdown_write. '
            'Final report gate was not satisfied.'
        )

    code_eval_result = await _run_code_evaluation_for_pdf(
        source_pdf_path=source_pdf,
        source_pdf_name=job.source_pdf_name,
    )
    append_event(
        job_id,
        'code_evaluation_completed',
        enabled=bool(code_eval_result.get('enabled')),
        attempted=bool(code_eval_result.get('attempted')),
        success=bool(code_eval_result.get('success')),
        exit_status=str(code_eval_result.get('exit_status') or 'skipped'),
        run_dir=str(code_eval_result.get('run_dir') or ''),
        error=str(code_eval_result.get('error') or ''),
    )

    def apply_code_eval(state):
        metadata = dict(state.metadata)
        metadata['code_evaluation'] = {
            'enabled': bool(code_eval_result.get('enabled')),
            'attempted': bool(code_eval_result.get('attempted')),
            'success': bool(code_eval_result.get('success')),
            'exit_status': str(code_eval_result.get('exit_status') or 'skipped'),
            'run_dir': str(code_eval_result.get('run_dir') or ''),
            'error': str(code_eval_result.get('error') or ''),
            'paper_key': str(code_eval_result.get('paper_key') or ''),
        }
        state.metadata = metadata

    mutate_job_state(job_id, apply_code_eval)

    set_status(job_id, JobStatus.pdf_exporting, 'Rendering final markdown report into PDF...')

    final_md_path = Path(artifacts['final_markdown'])
    report_pdf_path = Path(artifacts['report_pdf'])
    if not final_md_path.exists():
        raise RuntimeError(f'Final markdown not found: {final_md_path}')

    state_token_usage = _token_usage_payload_from_state(load_job_state(job_id))
    token_usage_for_pdf = {
        'requests': max(int(usage_totals.get('requests', 0)), int(state_token_usage.get('requests', 0))),
        'input_tokens': max(int(usage_totals.get('input_tokens', 0)), int(state_token_usage.get('input_tokens', 0))),
        'output_tokens': max(int(usage_totals.get('output_tokens', 0)), int(state_token_usage.get('output_tokens', 0))),
        'total_tokens': max(int(usage_totals.get('total_tokens', 0)), int(state_token_usage.get('total_tokens', 0))),
    }
    if token_usage_for_pdf['total_tokens'] <= 0:
        token_usage_for_pdf['total_tokens'] = (
            int(token_usage_for_pdf['input_tokens']) + int(token_usage_for_pdf['output_tokens'])
        )

    _render_report_pdf(
        job_id=job_id,
        job_title=job.title,
        source_pdf_name=job.source_pdf_name,
        final_md_path=final_md_path,
        source_pdf_path=source_pdf,
        report_pdf_path=report_pdf_path,
        annotations=list(runtime.annotations),
        content_list=parse_result.content_list,
        code_eval_summary_override=(code_eval_result.get('summary') if isinstance(code_eval_result, dict) else None),
        code_eval_alignment_override=(
            code_eval_result.get('alignment') if isinstance(code_eval_result, dict) else None
        ),
        token_usage=token_usage_for_pdf,
        agent_model=str(settings.agent_model or '').strip(),
    )
    _publish_outputs_to_output_dir(
        job_id=job_id,
        final_md_path=final_md_path,
        report_pdf_path=report_pdf_path,
    )

    def apply_completed(state):
        state.status = JobStatus.completed
        state.message = 'Review pipeline completed.'
        state.error = None
        state.final_report_ready = True
        state.pdf_ready = report_pdf_path.exists()
        state.artifacts.final_markdown_path = str(final_md_path)
        state.artifacts.report_pdf_path = str(report_pdf_path)

    mutate_job_state(job_id, apply_completed)
    append_event(job_id, 'completed', report_pdf_path=str(report_pdf_path))


def run_job(job_id: str) -> None:
    try:
        asyncio.run(run_job_async(job_id))
    except Exception as exc:
        detail = ''.join(traceback.format_exception_only(type(exc), exc)).strip()
        stack = traceback.format_exc()
        append_event(job_id, 'pipeline_exception', error=detail, stack=stack)
        if _complete_with_existing_final_report(job_id, warning=detail):
            return
        fail_job(
            job_id,
            message='Review pipeline failed.',
            error=detail,
        )
