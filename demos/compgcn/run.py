from __future__ import annotations

import argparse
import subprocess
import sys
import urllib.request
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent
ROOT = DEMO_DIR.parents[1]
COMPGCN_PDF_URL = "https://arxiv.org/pdf/1911.03082.pdf"
DEMO_PDF_PATH = DEMO_DIR / "paper.pdf"
COMPGCN_DOWNLOAD_PATH = ROOT / ".cache" / "compgcn.pdf"


def _looks_like_pdf(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        return path.read_bytes()[:5] == b"%PDF-"
    except Exception:
        return False


def _resolve_compgcn_pdf() -> Path:
    for candidate in (DEMO_PDF_PATH, COMPGCN_DOWNLOAD_PATH):
        if _looks_like_pdf(candidate):
            return candidate.resolve()

    COMPGCN_DOWNLOAD_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading CompGCN paper PDF from {COMPGCN_PDF_URL}", flush=True)
    try:
        with urllib.request.urlopen(COMPGCN_PDF_URL, timeout=60) as response:
            COMPGCN_DOWNLOAD_PATH.write_bytes(response.read())
    except Exception as exc:
        raise RuntimeError(
            "Could not download the CompGCN PDF. "
            "Run `git lfs pull` if you use the bundled demo PDF, or manually place "
            f"the PDF at {DEMO_PDF_PATH}."
        ) from exc

    if not _looks_like_pdf(COMPGCN_DOWNLOAD_PATH):
        raise RuntimeError(f"Downloaded file is not a valid PDF: {COMPGCN_DOWNLOAD_PATH}")
    return COMPGCN_DOWNLOAD_PATH.resolve()


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser("compgcn_demo")
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
    pdf_path = _resolve_compgcn_pdf()

    command = [
        sys.executable,
        str(ROOT / "scripts" / "execute_review_pipeline.py"),
        str(pdf_path),
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

    print(f"Running CompGCN demo with PDF: {pdf_path}", flush=True)
    result = subprocess.run(command, cwd=ROOT)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
