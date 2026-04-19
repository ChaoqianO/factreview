from abc import ABC, abstractmethod
from pathlib import Path


class BasePDFConverter(ABC):
    """Base class for PDF converters."""

    @abstractmethod
    def __init__(self, **kwargs):
        self.name = "Base Converter"

    @abstractmethod
    def convert_single(self, pdf_path: Path) -> list[str]:
        """Convert a single PDF file."""
        pass

    @staticmethod
    def discover_pdfs(input_root: Path) -> list[Path]:
        """Scan the input path and return a list of PDFs."""
        if input_root.is_file() and input_root.suffix.lower() == ".pdf":
            return [input_root]
        if input_root.is_dir():
            return sorted(input_root.rglob("*.pdf"))
        return []

    @staticmethod
    def build_output_path(
        input_root: Path,
        output_root: Path,
        pdf_path: Path,
        extension: str,
    ) -> Path:
        """Build an output path that mirrors the input directory structure."""
        if not extension.startswith("."):
            extension = f".{extension}"
        if input_root.is_dir():
            try:
                rel_dir = pdf_path.parent.relative_to(input_root)
            except ValueError:
                rel_dir = Path(pdf_path.parent.name)
        else:
            rel_dir = Path()
        dest_dir = output_root / rel_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        return dest_dir / f"{pdf_path.stem}{extension}"

    @staticmethod
    def write_text_list(output_file: Path, chunks: list[str], separator: str = "\n") -> None:
        """Write text chunks to the target file."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as file_obj:
            file_obj.write(separator.join(chunks))

    @staticmethod
    def summarize_batch(total: int, success: int, failed: list[str], title: str) -> None:
        print(f"\n{'=' * 40}")
        print(f"{title} done! success: {success}/{total}")
        if failed:
            print(f"Failed list: {failed}")

    def get_info(self) -> dict:
        return {"name": self.name}
