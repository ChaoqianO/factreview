"""Grobid converter: full-stack wrapper with service check and batch logic."""

import time
from pathlib import Path

import requests

from ._backend_base import BasePDFConverter


class GrobidConverter(BasePDFConverter):
    def __init__(self, **kwargs):
        super().__init__()
        self.name = "Grobid XML Converter"
        self.grobid_url = kwargs.get("grobid_url", "http://localhost:8070").rstrip("/")
        self.timeout = kwargs.get("timeout", 120)

        if not self._check_service():
            self._print_help()
            raise ConnectionError(f"Cannot connect to Grobid service: {self.grobid_url}")

    def _check_service(self) -> bool:
        """Check whether the Grobid service is alive."""
        try:
            resp = requests.get(f"{self.grobid_url}/api/isalive", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def _print_help(self):
        """Print Docker startup help information."""
        print("\n" + "!" * 60)
        print("ERROR: Cannot connect to Grobid service!")
        print("!" * 60)
        print(f"Target: {self.grobid_url}")
        print("\nFix: make sure Grobid is running via Docker.")
        print("\nStart command:")
        print("   docker run -d --rm --init -p 8070:8070 lfoppiano/grobid:0.8.0")
        print("\nCheck container status:")
        print("   docker ps | grep grobid")
        print("!" * 60 + "\n")

    def convert_single(self, pdf_path: Path) -> list[str]:
        """Call the Grobid API to retrieve TEI XML."""
        try:
            with open(pdf_path, "rb") as f:
                response = requests.post(
                    f"{self.grobid_url}/api/processFulltextDocument",
                    files={"input": f},
                    data={"consolidateHeader": "1", "consolidateCitations": "1"},
                    headers={"Accept": "application/xml"},
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    content = response.text.strip()
                    if content:
                        return [content]
                    raise Exception("Grobid returned empty content")
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

        except requests.exceptions.ConnectionError as err:
            self._print_help()
            raise Exception("connection dropped") from err
        except Exception as e:
            raise Exception(f"request failed: {e!s}") from e

    @staticmethod
    def run_batch_mode(input_root: Path, output_root: Path, grobid_url: str, timeout: int, overwrite: bool):
        """Grobid batch-processing logic."""
        print(f"\nInitializing Grobid connection: {grobid_url}")

        try:
            converter = GrobidConverter(grobid_url=grobid_url, timeout=timeout)
        except ConnectionError:
            return

        pdfs = BasePDFConverter.discover_pdfs(input_root)
        if not pdfs:
            print("No valid PDF files found")
            return

        print(f"Discovered {len(pdfs)} file(s)")
        print("Starting processing (output format: .xml)...")

        success = 0
        failed = []

        for i, pdf in enumerate(pdfs, 1):
            try:
                out_file = BasePDFConverter.build_output_path(
                    input_root=input_root,
                    output_root=output_root,
                    pdf_path=pdf,
                    extension=".xml",
                )

                if out_file.exists() and not overwrite:
                    print(f"[{i}/{len(pdfs)}] skip: {pdf.name}")
                    success += 1
                    continue

                print(f"[{i}/{len(pdfs)}] uploading: {pdf.name}", end="... ", flush=True)

                start_t = time.time()
                result_list = converter.convert_single(pdf)
                cost_t = time.time() - start_t

                BasePDFConverter.write_text_list(out_file, result_list)
                print(f"OK ({cost_t:.1f}s)")
                success += 1

            except Exception as e:
                if "connection dropped" not in str(e):
                    print(f"\nFAILED: {str(e)[:100]}")
                failed.append(pdf.name)

        BasePDFConverter.summarize_batch(
            total=len(pdfs),
            success=success,
            failed=failed,
            title="Grobid processing",
        )

    def get_info(self) -> dict:
        return {
            "name": self.name,
            "description": "Grobid academic PDF parser (requires Docker)",
            "output_dir": "converted_grobid/",
        }
