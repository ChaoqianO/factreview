from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from synthesis.runtime.report.teaser_figure import generate_teaser_figure


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("generate_teaser_figure")
    parser.add_argument(
        "--latest-extraction",
        default=str((ROOT / "output" / "latest_extraction.md").resolve()),
        help="Path to latest_extraction markdown.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Optional output directory for prompt/image artifacts.",
    )
    parser.add_argument(
        "--gemini-model",
        default="",
        help="Optional Gemini/Imagen model override. Defaults to GEMINI_IMAGE_MODEL, GEMINI_MODEL, then imagen-4.0-generate-001.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="Gemini API request timeout in seconds.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _load_env_file(ROOT / ".env")
    result = generate_teaser_figure(
        args.latest_extraction,
        output_dir=args.output_dir or None,
        gemini_model=args.gemini_model or None,
        timeout_seconds=args.timeout_seconds,
    )

    payload = {
        "status": result.status,
        "message": result.message,
        "used_gemini_api": result.used_gemini_api,
        "model": result.model,
        "source_markdown_path": result.source_markdown_path,
        "prompt_path": result.prompt_path,
        "image_path": result.image_path,
        "response_path": result.response_path,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if result.status == "prompt_only":
        print("")
        print("Gemini web fallback:")
        print("1. Open https://gemini.google.com/")
        print("2. Start an image-generation chat.")
        print(f"3. Paste the prompt from: {result.prompt_path}")


if __name__ == "__main__":
    main()
