from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

class BasePDFConverter(ABC):
    """PDF转换器基类"""

    @abstractmethod
    def __init__(self, **kwargs):
        self.name = "Base Converter"

    @abstractmethod
    def convert_single(self, pdf_path: Path) -> List[str]:
        """转换单个PDF文件"""
        pass

    @staticmethod
    def discover_pdfs(input_root: Path) -> List[Path]:
        """扫描输入路径并返回 PDF 列表。"""
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
        """根据输入目录结构构造输出路径。"""
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
    def write_text_list(output_file: Path, chunks: List[str], separator: str = "\n") -> None:
        """将文本块写入目标文件。"""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as file_obj:
            file_obj.write(separator.join(chunks))

    @staticmethod
    def summarize_batch(total: int, success: int, failed: List[str], title: str) -> None:
        print(f"\n{'=' * 40}")
        print(f"{title} 完成! 成功: {success}/{total}")
        if failed:
            print(f"失败列表: {failed}")

    def get_info(self) -> dict:
        return {"name": self.name}
