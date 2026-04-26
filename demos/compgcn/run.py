from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent
ROOT = DEMO_DIR.parents[1]
DEMO_PDF_PATH = DEMO_DIR / "paper.pdf"


def _looks_like_pdf(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        return path.read_bytes()[:5] == b"%PDF-"
    except Exception:
        return False


def _resolve_compgcn_pdf(override: str = "") -> str:
    token = str(override or "").strip()
    if token:
        return token
    if _looks_like_pdf(DEMO_PDF_PATH):
        return str(DEMO_PDF_PATH.resolve())
    raise RuntimeError(
        "Bundled CompGCN PDF is missing or invalid. "
        f"Run `git lfs pull` or manually place the PDF at {DEMO_PDF_PATH}."
    )


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser("compgcn_demo")
    parser.add_argument("--paper-pdf", default="", help="Optional path or URL override for the paper PDF.")
    parser.add_argument("--paper-key", default="compgcn")
    parser.add_argument("--run-root", default="runs")
    parser.add_argument(
        "--teaser-mode",
        choices=("auto", "prompt", "api"),
        default="auto",
        help="Auto mode uses Gemini when a key is configured and falls back to prompt-only otherwise.",
    )
    parser.add_argument("--run-execution", action="store_true", help="Opt into code execution for the demo.")
    parser.add_argument("--llm-provider", default="", help="Optional LLM provider override.")
    parser.add_argument("--llm-model", default="", help="Optional LLM model override.")
    parser.add_argument("--mineru-api-token", default="", help="Optional MinerU token override.")
    parser.add_argument("--gemini-api-key", default="", help="Optional Gemini key override.")
    return parser.parse_known_args()


def main() -> None:
    args, passthrough = parse_args()
    pdf_input = _resolve_compgcn_pdf(args.paper_pdf)

    command = [
        sys.executable,
        str(ROOT / "scripts" / "execute_review_pipeline.py"),
        pdf_input,
        "--paper-key",
        args.paper_key,
        "--run-root",
        args.run_root,
        "--teaser-mode",
        args.teaser_mode,
    ]
    if args.run_execution:
        command.append("--run-execution")
    for flag_name, value in (
        ("--llm-provider", args.llm_provider),
        ("--llm-model", args.llm_model),
        ("--mineru-api-token", args.mineru_api_token),
        ("--gemini-api-key", args.gemini_api_key),
    ):
        if str(value or "").strip():
            command.extend([flag_name, str(value).strip()])
    command.extend(passthrough)

    print(f"Running CompGCN demo with PDF: {pdf_input}", flush=True)
    result = subprocess.run(command, cwd=ROOT)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
