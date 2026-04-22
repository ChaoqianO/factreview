from __future__ import annotations

import base64
from pathlib import Path

from synthesis.runtime.report.teaser_figure import (
    _extract_inline_image_bytes,
    build_teaser_figure_prompt_from_latest_extraction,
    generate_teaser_figure,
)


SAMPLE_MARKDOWN = """## 1. Metadata
- Title: Demo Paper
- Task: Node classification

## 2. Technical Positioning
Figure 1. Model comparison overview.
![overview](figures/overview.png)

| Model | Setting |
| --- | --- |
| Ours | Full |

## 3. Claims
(Status legend: Supported, Inconclusive, In conflict)

| Claim | Evidence | Status |
| --- | --- | --- |
| Claim A | Evidence A | Supported |
| Claim B | Evidence B | Inconclusive |
| Claim C | Evidence C | In conflict |

## 4. Summary
This paper proposes a practical method.
Strengths:
- Clear empirical gains
Weaknesses:
- Limited ablations

## 5. Experiment
### Main Result
Location: Table 1

| Dataset | Score |
| --- | --- |
| Cora | 85.0 |

### Ablation Result
Location: Table 2

| Variant | Score |
| --- | --- |
| w/o X | 82.1 |
"""


def test_build_teaser_prompt_from_latest_extraction(tmp_path: Path) -> None:
    latest_md = tmp_path / "latest_extraction.md"
    latest_md.write_text(SAMPLE_MARKDOWN, encoding="utf-8")

    prompt = build_teaser_figure_prompt_from_latest_extraction(latest_md)

    assert "Title: Demo Paper" in prompt
    assert "Task: Node classification" in prompt
    assert "Claim: Claim A" in prompt
    assert "Main result location: Table 1" in prompt


def test_generate_teaser_figure_without_gemini_key_writes_prompt(tmp_path: Path, monkeypatch) -> None:
    latest_md = tmp_path / "latest_extraction.md"
    latest_md.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = generate_teaser_figure(latest_md, output_dir=tmp_path / "artifacts")

    assert result.status == "prompt_only"
    assert result.used_gemini_api is False
    assert Path(result.prompt_path).exists()
    assert "Gemini web app" in result.message


def test_extract_inline_image_bytes_finds_nested_base64() -> None:
    raw = b"fake-png-bytes"
    payload = {
        "predictions": [
            {
                "nested": {
                    "bytesBase64Encoded": base64.b64encode(raw).decode("ascii"),
                }
            }
        ]
    }

    assert _extract_inline_image_bytes(payload) == raw
