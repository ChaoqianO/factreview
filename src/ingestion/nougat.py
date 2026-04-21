"""Nougat-OCR converter: full-stack wrapper with batch logic."""

import os
import shutil
import subprocess as sp
import tempfile
import time
from pathlib import Path

import torch

from ._backend_base import BasePDFConverter


class NougatOCRConverter(BasePDFConverter):
    def __init__(self, **kwargs):
        super().__init__()
        self.name = "Nougat-OCR (Official)"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        timeout = kwargs.get("timeout")
        if isinstance(timeout, int) and timeout == 0:
            timeout = None
        self.timeout = timeout

    @staticmethod
    def run_batch_mode(input_root: Path, output_root: Path, timeout: int, overwrite: bool):
        """Nougat batch-processing logic."""
        print(f"\nInitializing Nougat model (Device: {'CUDA' if torch.cuda.is_available() else 'CPU'})...")

        pdfs = BasePDFConverter.discover_pdfs(input_root)
        if not pdfs:
            print("No valid PDF files found")
            return

        converter = NougatOCRConverter(timeout=timeout)

        print(f"Discovered {len(pdfs)} file(s)")
        print("Starting processing (large, slow model; please be patient)...")

        success = 0
        failed = []

        for i, pdf in enumerate(pdfs, 1):
            try:
                out_file = BasePDFConverter.build_output_path(
                    input_root=input_root,
                    output_root=output_root,
                    pdf_path=pdf,
                    extension=".mmd",
                )

                if out_file.exists() and not overwrite:
                    print(f"[{i}/{len(pdfs)}] skip: {pdf.name}")
                    success += 1
                    continue

                print(f"[{i}/{len(pdfs)}] processing: {pdf.name}")

                results = converter.convert_single(pdf)

                if results and results[0]:
                    BasePDFConverter.write_text_list(out_file, [results[0]])
                    print("    saved")
                    success += 1
                else:
                    print("    empty output")
                    failed.append(pdf.name)

            except Exception as e:
                print(f"\nFAILED: {str(e)[:100]}")
                failed.append(pdf.name)

        BasePDFConverter.summarize_batch(
            total=len(pdfs),
            success=success,
            failed=failed,
            title="Nougat processing",
        )

    def convert_single(self, pdf_path: Path) -> list[str]:
        temp_dir = Path(tempfile.mkdtemp(prefix="nougat_"))
        try:
            return self._run_nougat(pdf_path, temp_dir) or [""]
        except FileNotFoundError:
            return ["nougat command not found; install via: pip install nougat-ocr"]
        except Exception as e:
            raise Exception(f"execution error: {e!s}") from e
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def _run_nougat(self, pdf_path: Path, temp_dir: Path) -> list[str]:
        cmd = [
            "nougat",
            str(pdf_path),
            "--out",
            str(temp_dir),
            "--markdown",
            "--no-skipping",
            "--batchsize",
            "1",
        ]

        env = dict(os.environ)
        hf_home = env.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
        env["HF_HOME"] = hf_home
        os.makedirs(env["HF_HOME"], exist_ok=True)

        start_time = time.time()

        process = sp.Popen(
            cmd,
            stdout=sp.PIPE,
            stderr=sp.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        last_activity = time.time()

        while True:
            if self.timeout is not None and (time.time() - start_time > self.timeout):
                process.terminate()
                raise TimeoutError(f"processing timeout ({self.timeout}s)")

            line = process.stdout.readline()
            if line:
                line = line.strip()
                last_activity = time.time()
                if "%" in line or "it/s" in line or "error" in line.lower():
                    print(f"    {line}")

            if process.poll() is not None:
                break

            if time.time() - last_activity > 60:
                print("    model still running, please wait...")
                last_activity = time.time()

            time.sleep(0.1)

        if process.returncode != 0:
            raise Exception(f"Nougat process exited abnormally (code: {process.returncode})")

        for ext in [".mmd", ".md"]:
            expected = temp_dir / f"{pdf_path.stem}{ext}"
            if not expected.exists():
                expected = temp_dir / f"{pdf_path.name}{ext}"

            if expected.exists() and expected.stat().st_size > 0:
                with open(expected, encoding="utf-8") as f:
                    return [f.read()]

        return None

    def get_info(self) -> dict:
        return {"name": self.name}
