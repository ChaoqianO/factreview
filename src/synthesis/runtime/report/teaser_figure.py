from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


_SECTION_RE = re.compile(r"(?ims)^##\s+(?P<title>\d+\.\s+.+?)\s*$\n(?P<body>.*?)(?=^##\s+|\Z)")
_BULLET_FIELD_RE = re.compile(r"^\s*[-*•]\s*(?P<key>[A-Za-z][A-Za-z\s]+?)\s*:\s*(?P<value>.+?)\s*$")
_MARKDOWN_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)")
_LOCATION_RE = re.compile(r"(?im)^\s*Location\s*:\s*(?P<value>.+?)\s*$")
_LABEL_BLOCK_RE = re.compile(
    r"(?ims)^\s*(?P<label>Main Result|Ablation Result|Strengths|Weaknesses)\s*:?\s*$"
    r"(?P<body>.*?)(?=^\s*(?:Main Result|Ablation Result|Strengths|Weaknesses)\s*:?\s*$|\Z)"
)


@dataclass(frozen=True)
class TableBlock:
    headers: list[str]
    rows: list[list[str]]


@dataclass(frozen=True)
class TeaserFigurePayload:
    title: str
    task: str
    status_legend: list[str]
    technical_positioning_caption: str
    technical_positioning_image: str
    technical_positioning_table: TableBlock | None
    claims_table: TableBlock | None
    selected_claim_rows: list[dict[str, str]]
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    experiment_main_location: str
    experiment_main_table: TableBlock | None
    experiment_ablation_location: str
    experiment_ablation_table: TableBlock | None


@dataclass(frozen=True)
class TeaserFigureGenerationResult:
    status: str
    prompt: str
    prompt_path: str
    image_path: str
    response_path: str
    model: str
    message: str
    used_gemini_api: bool
    source_markdown_path: str


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_sections(markdown_text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    for match in _SECTION_RE.finditer(markdown_text or ""):
        title = str(match.group("title") or "").strip()
        body = str(match.group("body") or "").strip()
        sections[title] = body
    return sections


def _parse_markdown_table(block: str) -> TableBlock | None:
    lines = [ln.rstrip() for ln in (block or "").splitlines()]
    table_lines = [ln for ln in lines if ln.strip().startswith("|") and ln.strip().endswith("|")]
    if len(table_lines) < 2:
        return None

    headers = [cell.strip() for cell in table_lines[0].strip().strip("|").split("|")]
    rows: list[list[str]] = []
    for line in table_lines[1:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells):
            continue
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        rows.append(cells[: len(headers)])
    return TableBlock(headers=headers, rows=rows)


def _table_to_markdown(table: TableBlock | None) -> str:
    if table is None:
        return "Not found in manuscript"
    head = "| " + " | ".join(table.headers) + " |"
    sep = "| " + " | ".join(["---"] * len(table.headers)) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in table.rows)
    return "\n".join([head, sep, body]).strip()


def _extract_first_table(text: str) -> TableBlock | None:
    blocks: list[str] = []
    current: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            current.append(line)
            continue
        if current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    for block in blocks:
        table = _parse_markdown_table(block)
        if table is not None:
            return table
    return None


def _extract_metadata(body: str) -> tuple[str, str]:
    title = ""
    task = ""
    for line in (body or "").splitlines():
        match = _BULLET_FIELD_RE.match(line.strip())
        if not match:
            continue
        key = str(match.group("key") or "").strip().lower()
        value = str(match.group("value") or "").strip()
        if key == "title":
            title = value
        elif key == "task":
            task = value
    return title, task


def _extract_status_legend(text: str) -> list[str]:
    match = re.search(r"(?ims)\(Status legend:\s*(?P<body>.*?)\)", text or "")
    if not match:
        return []
    body = re.sub(r"\s+", " ", str(match.group("body") or "")).strip()
    parts = [part.strip(" .") for part in re.split(r"[,;]", body) if part.strip()]
    return parts


def _extract_technical_positioning(body: str) -> tuple[str, str, TableBlock | None]:
    lines = [line.strip() for line in (body or "").splitlines() if line.strip()]
    caption = ""
    for line in lines:
        if line.lower().startswith("figure "):
            caption = line
    image_match = _MARKDOWN_IMAGE_RE.search(body or "")
    image_src = str(image_match.group("src") or "").strip() if image_match else ""
    table = _extract_first_table(body)
    return caption, image_src, table


def _extract_claims(body: str) -> tuple[TableBlock | None, list[str]]:
    table = _extract_first_table(body)
    status_legend = _extract_status_legend(body)
    return table, status_legend


def _extract_labeled_block(body: str, label: str) -> str:
    patterns = [
        re.compile(
            rf"(?ims)^\s*{re.escape(label)}\s*:\s*(?P<content>.*?)(?=^\s*(?:Strengths|Weaknesses)\s*:|\Z)"
        ),
        re.compile(
            rf"(?ims)^\s*{re.escape(label)}\s*$\n(?P<content>.*?)(?=^\s*(?:Strengths|Weaknesses)\s*$|\Z)"
        ),
    ]
    for pattern in patterns:
        match = pattern.search(body or "")
        if match:
            return str(match.group("content") or "").strip()
    return ""


def _extract_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ", "• ")):
            bullets.append(stripped[2:].strip())
    return bullets


def _extract_summary(body: str) -> tuple[str, list[str], list[str]]:
    strengths_block = _extract_labeled_block(body, "Strengths")
    weaknesses_block = _extract_labeled_block(body, "Weaknesses")

    summary_text = body or ""
    for marker in ("Strengths:", "Weaknesses:", "Strengths", "Weaknesses"):
        idx = summary_text.find(marker)
        if idx >= 0:
            summary_text = summary_text[:idx]
            break
    summary_text = re.sub(r"\n{2,}", "\n\n", summary_text).strip()
    strengths = _extract_bullets(strengths_block)
    weaknesses = _extract_bullets(weaknesses_block)
    return summary_text, strengths, weaknesses


def _extract_experiment_subsection(body: str, label: str) -> tuple[str, TableBlock | None]:
    match = re.search(
        rf"(?ims)^\s*(?:###\s*)?{re.escape(label)}\s*$\n(?P<content>.*?)(?=^\s*(?:###\s*)?(?:Main Result|Ablation Result)\s*$|\Z)",
        body or "",
    )
    if not match:
        return "", None
    content = str(match.group("content") or "").strip()
    location_match = _LOCATION_RE.search(content)
    location = str(location_match.group("value") or "").strip() if location_match else ""
    table = _extract_first_table(content)
    return location, table


def _row_to_dict(table: TableBlock, row: list[str]) -> dict[str, str]:
    normalized = row[: len(table.headers)] + [""] * max(0, len(table.headers) - len(row))
    return {header: re.sub(r"\s+", " ", str(value or "")).strip() or "Not found in manuscript" for header, value in zip(table.headers, normalized)}

def _select_claim_rows(table: TableBlock | None, limit: int = 3) -> list[dict[str, str]]:
    if table is None:
        return []
    claim_idx = next((idx for idx, header in enumerate(table.headers) if "claim" in header.lower()), -1)
    evidence_idx = next((idx for idx, header in enumerate(table.headers) if "evidence" in header.lower()), -1)
    status_idx = next((idx for idx, header in enumerate(table.headers) if "status" in header.lower()), -1)
    selected: list[dict[str, str]] = []
    for row in table.rows:
        claim_text = row[claim_idx].strip() if claim_idx >= 0 and claim_idx < len(row) else ""
        evidence_text = row[evidence_idx].strip() if evidence_idx >= 0 and evidence_idx < len(row) else ""
        status_text = row[status_idx].strip() if status_idx >= 0 and status_idx < len(row) else ""
        if not any([claim_text, evidence_text, status_text]):
            continue
        selected.append(
            {
                "Claim": claim_text or "Not found in manuscript",
                "Evidence": evidence_text or "Not found in manuscript",
                "Status": status_text or "Not found in manuscript",
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _format_selected_claims(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "1. Not found in manuscript"
    return "\n".join(
        f"{idx}. Claim: {row.get('Claim', 'Not found in manuscript')}; "
        f"Evidence: {row.get('Evidence', 'Not found in manuscript')}; "
        f"Status: {row.get('Status', 'Not found in manuscript')}"
        for idx, row in enumerate(rows, start=1)
    )


def extract_teaser_figure_payload(markdown_text: str) -> TeaserFigurePayload:
    sections = _extract_sections(markdown_text)
    metadata = sections.get("1. Metadata", "")
    technical = sections.get("2. Technical Positioning", "")
    claims = sections.get("3. Claims", "")
    summary = sections.get("4. Summary", "")
    experiment = sections.get("5. Experiment", "")

    title, task = _extract_metadata(metadata)
    tp_caption, tp_image, tp_table = _extract_technical_positioning(technical)
    claims_table, claims_status = _extract_claims(claims)
    summary_text, strengths, weaknesses = _extract_summary(summary)
    main_location, main_table = _extract_experiment_subsection(experiment, "Main Result")
    ablation_location, ablation_table = _extract_experiment_subsection(experiment, "Ablation Result")
    selected_claim_rows = _select_claim_rows(claims_table, limit=3)

    return TeaserFigurePayload(
        title=title or "Not found in manuscript",
        task=task or "Not found in manuscript",
        status_legend=claims_status,
        technical_positioning_caption=tp_caption or "Not found in manuscript",
        technical_positioning_image=tp_image or "Not found in manuscript",
        technical_positioning_table=tp_table,
        claims_table=claims_table,
        selected_claim_rows=selected_claim_rows,
        summary=summary_text or "Not found in manuscript",
        strengths=strengths,
        weaknesses=weaknesses,
        experiment_main_location=main_location or "Not found in manuscript",
        experiment_main_table=main_table,
        experiment_ablation_location=ablation_location or "Not found in manuscript",
        experiment_ablation_table=ablation_table,
    )


def extract_teaser_figure_payload_from_latest_extraction(latest_extraction_path: str | Path) -> TeaserFigurePayload:
    path = Path(latest_extraction_path)
    return extract_teaser_figure_payload(_read_text(path))


def build_teaser_figure_prompt(payload: TeaserFigurePayload) -> str:
    status_text = "; ".join(payload.status_legend) if payload.status_legend else "Not found in manuscript"
    strengths_text = "\n".join(f"- {item}" for item in payload.strengths) if payload.strengths else "- Not found in manuscript"
    weaknesses_text = "\n".join(f"- {item}" for item in payload.weaknesses) if payload.weaknesses else "- Not found in manuscript"
    selected_claims_text = _format_selected_claims(payload.selected_claim_rows)

    return (
        "Create a single polished teaser figure for an ML paper review summary.\n"
        "The output should read like a presentation-quality overview graphic, not a raw markdown rendering.\n"
        "Use the extracted report content below as authoritative content to place into the figure.\n"
        "Preserve factual wording, numeric values, and status labels from the source.\n"
        "Treat the following layout/style instructions as fixed constraints derived from the reference teaser_figure.pptx.\n"
        "Keep colors unchanged and keep the relative positions of all modules unchanged; only adjust module width/height "
        "slightly based on content length.\n"
        "All text should use Times New Roman.\n"
        "There is no strict text-length limit inside each module; automatically adjust font sizes, line breaks, spacing, "
        "and box sizes for the most visually balanced result.\n"
        "Do not invent any extra claims, metrics, or statuses.\n"
        "\n"
        "[Fixed Layout Instructions]\n"
        "- Keep the overall teaser layout structure and relative module positions consistent with the reference design.\n"
        "- The top-right area contains status badges; preserve their relative placement and badge style.\n"
        "- All status badges use rounded-rectangle backgrounds.\n"
        "- The lower row includes Improvement and Reduction badges; preserve their relative placement.\n"
        "- The right-side summary panel keeps Strengths above Weaknesses, with the specified bottom background colors.\n"
        "- Claim rows should be laid out adaptively based on content, with no fixed per-line text limit.\n"
        "\n"
        "[Fixed Badge Styles]\n"
        "- Supported: text color RGB(88,144,78); left icon is a check mark with RGB(0,150,100); rounded-rectangle "
        "background RGB(172,215,142).\n"
        "- Paper-supported: text color RGB(46,84,161); left icon is a boxed check mark where the box color is "
        "RGB(65,105,225) and the internal check mark is white; rounded-rectangle background RGB(182,199,234).\n"
        "- Partially supported/Inconclusive: text color RGB(182,140,2); left icon is a warning symbol whose border color "
        "is RGB(184,134,11) and internal exclamation mark is white; rounded-rectangle background RGB(254,230,149).\n"
        "- In conflict: text color RGB(200,29,49); left icon is an X with RGB(139,0,0); rounded-rectangle background "
        "RGB(239,148,158).\n"
        "- Improvement: text color RGB(86,133,44); rounded-rectangle background RGB(117,189,66).\n"
        "- Reduction: text color RGB(133,19,44); rounded-rectangle background RGB(229,76,94).\n"
        "\n"
        "[Fixed Content Rules]\n"
        "- The task label area at the top-right has no text-length restriction.\n"
        "- The claims section should show exactly 3 claim rows, and they must be dynamically extracted from the report's claims table using the Claim, Evidence, and Status information.\n"
        "- Each claim row has no fixed text-length requirement; wrap and resize based on content for the cleanest layout.\n"
        "- The technical positioning module must directly use the extracted figure/image reference and table content.\n"
        "- The experiment module must directly use the extracted main-result and ablation tables below.\n"
        "- For the Strengths section, use bottom background color RGB(200,229,179).\n"
        "- For the Weaknesses section, use bottom background color RGB(245,183,191).\n"
        "\n"
        "[Rendering Guidance]\n"
        "- Make the figure as aesthetically balanced as possible.\n"
        "- Use adaptive typography, spacing, and box scaling automatically, but do not alter the fixed colors or the "
        "relative placement of modules.\n"
        "- Use clear visual hierarchy, concise labels, table-like alignment where needed, and publication-style spacing.\n"
        "- This is a dynamic pipeline: for each run, first extract the teaser-display fields from the provided latest_extraction markdown, then compose the final teaser figure prompt from those extracted fields and the fixed style constraints above.\n"
        "- Only inject content that is meant to be displayed in the teaser figure; do not add extra extracted fields that are not part of the visible teaser modules.\n"
        "\n"
        "[Report Content]\n"
        f"Title: {payload.title}\n"
        f"Task: {payload.task}\n"
        f"Status legend: {status_text}\n"
        "\n"
        "[Technical Positioning]\n"
        f"Caption: {payload.technical_positioning_caption}\n"
        f"Image reference: {payload.technical_positioning_image}\n"
        "Table:\n"
        f"{_table_to_markdown(payload.technical_positioning_table)}\n"
        "\n"
        "[Claims]\n"
        "Selected 3 claim rows for direct layout use:\n"
        f"{selected_claims_text}\n"
        "\n"
        "Full claims table:\n"
        f"{_table_to_markdown(payload.claims_table)}\n"
        "\n"
        "[Summary]\n"
        f"{payload.summary}\n"
        "Strengths:\n"
        f"{strengths_text}\n"
        "Weaknesses:\n"
        f"{weaknesses_text}\n"
        "\n"
        "[Experiments]\n"
        f"Main result location: {payload.experiment_main_location}\n"
        "Main result table:\n"
        f"{_table_to_markdown(payload.experiment_main_table)}\n"
        "\n"
        f"Ablation result location: {payload.experiment_ablation_location}\n"
        "Ablation result table:\n"
        f"{_table_to_markdown(payload.experiment_ablation_table)}\n"
    )


def build_teaser_figure_prompt_from_latest_extraction(latest_extraction_path: str | Path) -> str:
    payload = extract_teaser_figure_payload_from_latest_extraction(latest_extraction_path)
    return build_teaser_figure_prompt(payload)


def _default_teaser_output_dir(latest_extraction_path: Path) -> Path:
    parent = latest_extraction_path.parent.resolve()
    if parent.name == "output":
        return parent / "teaser_figure"
    return parent / "teaser_figure"


def _coerce_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_inline_image_bytes(node: Any) -> bytes | None:
    if isinstance(node, dict):
        for key in ("imageBytes", "bytesBase64Encoded", "image_bytes", "bytes_base64_encoded"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                try:
                    return base64.b64decode(value)
                except Exception:
                    continue
        for value in node.values():
            decoded = _extract_inline_image_bytes(value)
            if decoded is not None:
                return decoded
        return None
    if isinstance(node, list):
        for item in node:
            decoded = _extract_inline_image_bytes(item)
            if decoded is not None:
                return decoded
    return None


def _call_gemini_image_api(*, prompt: str, api_key: str, model: str, timeout_seconds: int) -> dict[str, Any]:
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict"
    response = requests.post(
        endpoint,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1},
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Gemini image API returned a non-object JSON payload.")
    return payload


def generate_teaser_figure(
    latest_extraction_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    gemini_api_key: str | None = None,
    gemini_model: str | None = None,
    timeout_seconds: int = 120,
) -> TeaserFigureGenerationResult:
    latest_path = _coerce_path(latest_extraction_path).resolve()
    prompt = build_teaser_figure_prompt_from_latest_extraction(latest_path)
    final_output_dir = (
        _coerce_path(output_dir).resolve()
        if output_dir is not None
        else _default_teaser_output_dir(latest_path)
    )
    final_output_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = final_output_dir / "teaser_figure_prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")

    api_key = str(gemini_api_key or os.getenv("GEMINI_API_KEY") or "").strip()
    model = str(
        gemini_model
        or os.getenv("GEMINI_IMAGE_MODEL")
        or os.getenv("GEMINI_MODEL")
        or "imagen-4.0-generate-001"
    ).strip()
    response_path = final_output_dir / "teaser_figure_gemini_response.json"
    image_path = final_output_dir / "teaser_figure.png"

    if not api_key:
        return TeaserFigureGenerationResult(
            status="prompt_only",
            prompt=prompt,
            prompt_path=str(prompt_path),
            image_path="",
            response_path="",
            model=model,
            message=(
                "GEMINI_API_KEY not found. Prompt was written to disk. "
                "You can paste it into the Gemini web app to generate the teaser figure manually."
            ),
            used_gemini_api=False,
            source_markdown_path=str(latest_path),
        )

    payload = _call_gemini_image_api(
        prompt=prompt,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
    )
    _write_json(response_path, payload)

    image_bytes = _extract_inline_image_bytes(payload)
    if image_bytes is None:
        raise RuntimeError(
            "Gemini returned successfully, but no image bytes were found in the response payload."
        )
    image_path.write_bytes(image_bytes)

    return TeaserFigureGenerationResult(
        status="generated",
        prompt=prompt,
        prompt_path=str(prompt_path),
        image_path=str(image_path),
        response_path=str(response_path),
        model=model,
        message="Teaser figure image generated via Gemini API.",
        used_gemini_api=True,
        source_markdown_path=str(latest_path),
    )


def payload_to_dict(payload: TeaserFigurePayload) -> dict[str, Any]:
    return {
        "title": payload.title,
        "task": payload.task,
        "status_legend": payload.status_legend,
        "technical_positioning_caption": payload.technical_positioning_caption,
        "technical_positioning_image": payload.technical_positioning_image,
        "technical_positioning_table": None
        if payload.technical_positioning_table is None
        else {
            "headers": payload.technical_positioning_table.headers,
            "rows": payload.technical_positioning_table.rows,
        },
        "claims_table": None
        if payload.claims_table is None
        else {
            "headers": payload.claims_table.headers,
            "rows": payload.claims_table.rows,
        },
        "selected_claim_rows": payload.selected_claim_rows,
        "summary": payload.summary,
        "strengths": payload.strengths,
        "weaknesses": payload.weaknesses,
        "experiment_main_location": payload.experiment_main_location,
        "experiment_main_table": None
        if payload.experiment_main_table is None
        else {
            "headers": payload.experiment_main_table.headers,
            "rows": payload.experiment_main_table.rows,
        },
        "experiment_ablation_location": payload.experiment_ablation_location,
        "experiment_ablation_table": None
        if payload.experiment_ablation_table is None
        else {
            "headers": payload.experiment_ablation_table.headers,
            "rows": payload.experiment_ablation_table.rows,
        },
    }
