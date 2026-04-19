"""LlamaIndex converter: full-stack wrapper with batch logic."""

from pathlib import Path

from ._backend_base import BasePDFConverter


class LlamaIndexConverter(BasePDFConverter):
    def __init__(self, **kwargs):
        super().__init__()
        self.name = "LlamaIndex PDFMarkerReader"
        try:
            from llama_index.readers.pdf_marker import PDFMarkerReader

            self.reader = PDFMarkerReader()
        except ImportError as e:
            raise ImportError(
                f"Cannot import PDFMarkerReader: {e}\nTry: pip install llama-index llama-index-readers-pdf-marker"
            ) from e

    @staticmethod
    def run_batch_mode(input_root: Path, output_root: Path, overwrite: bool):
        """LlamaIndex batch-processing logic."""
        print("\nInitializing LlamaIndex converter...")

        try:
            converter = LlamaIndexConverter()
        except ImportError as e:
            print(f"Init failed: {e}")
            return

        pdfs = BasePDFConverter.discover_pdfs(input_root)
        if not pdfs:
            print("No valid PDF files found")
            return

        print(f"Discovered {len(pdfs)} file(s)")
        print("Starting processing...")

        success = 0
        failed = []

        for i, pdf in enumerate(pdfs, 1):
            try:
                out_file = BasePDFConverter.build_output_path(
                    input_root=input_root,
                    output_root=output_root,
                    pdf_path=pdf,
                    extension=".md",
                )

                if out_file.exists() and not overwrite:
                    print(f"[{i}/{len(pdfs)}] skip: {pdf.name}")
                    success += 1
                    continue

                print(f"[{i}/{len(pdfs)}] processing: {pdf.name}", end="... ", flush=True)

                results = converter.convert_single(pdf)

                BasePDFConverter.write_text_list(out_file, results, separator="\n\n---\n\n")
                print("OK")
                success += 1

            except Exception as e:
                print(f"\nFAILED: {str(e)[:100]}")
                failed.append(pdf.name)

        BasePDFConverter.summarize_batch(
            total=len(pdfs),
            success=success,
            failed=failed,
            title="LlamaIndex processing",
        )

    def convert_single(self, pdf_path: Path) -> list[str]:
        documents = self.reader.load_data(pdf_path)
        return [doc.text for doc in documents]

    def get_info(self) -> dict:
        return {"name": self.name}
