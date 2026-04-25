from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.runtime_shared.env import load_env_file
from synthesis.runtime.report.teaser_figure import _env_true, generate_teaser_figure


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
        "--gemini-api-key",
        default="",
        help="Optional Gemini API key override. Prefer GEMINI_API_KEY in .env/env for routine use.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="Gemini API request timeout in seconds.",
    )
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Write and return the Gemini prompt without calling the image API, even if a key is configured.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env_file(ROOT / ".env")
    generate_image = False if bool(args.prompt_only) else _env_true("TEASER_USE_GEMINI", default=True)
    result = generate_teaser_figure(
        args.latest_extraction,
        output_dir=args.output_dir or None,
        gemini_api_key=args.gemini_api_key or None,
        gemini_model=args.gemini_model or None,
        timeout_seconds=args.timeout_seconds,
        generate_image=generate_image,
    )

    payload = {
        "status": result.status,
        "message": result.message,
        "clipboard_copied": result.clipboard_copied,
        "used_gemini_api": result.used_gemini_api,
        "model": result.model,
        "source_markdown_path": result.source_markdown_path,
        "prompt_path": result.prompt_path,
        "prompt": result.prompt,
        "image_path": result.image_path,
        "response_path": result.response_path,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if result.status == "prompt_only":
        print("")
        print("Gemini web fallback:")
        print("1. Open https://gemini.google.com/")
        print("2. Start an image-generation chat.")
        if result.clipboard_copied:
            print("3. Paste the prompt from your clipboard.")
        else:
            print(f"3. Paste the prompt from the JSON above or from: {result.prompt_path}")


if __name__ == "__main__":
    main()
