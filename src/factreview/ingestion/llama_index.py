"""
LlamaIndex 转换器 - 全栈封装版 (含批量逻辑)
"""
from .base import BasePDFConverter
from pathlib import Path
from typing import List

class LlamaIndexConverter(BasePDFConverter):
    def __init__(self, **kwargs):
        super().__init__()
        self.name = "LlamaIndex PDFMarkerReader"
        try:
            from llama_index.readers.pdf_marker import PDFMarkerReader
            self.reader = PDFMarkerReader()
        except ImportError as e:
            raise ImportError(f"无法导入 PDFMarkerReader: {e}\n请尝试: pip install llama-index llama-index-readers-pdf-marker")

    @staticmethod
    def run_batch_mode(input_root: Path, output_root: Path, overwrite: bool):
        """
        LlamaIndex 专用批量处理逻辑
        """
        print(f"\n🧠 初始化 LlamaIndex 转换器...")

        # 1. 初始化实例
        try:
            converter = LlamaIndexConverter()
        except ImportError as e:
            print(f"❌ 初始化失败: {e}")
            return

        # 2. 扫描文件
        pdfs = BasePDFConverter.discover_pdfs(input_root)
        if not pdfs:
            print("❌ 未找到有效 PDF 文件")
            return

        print(f"📊 扫描到 {len(pdfs)} 个文件")
        print(f"🚀 开始逐个处理...")

        success = 0
        failed = []

        # 3. 循环处理
        for i, pdf in enumerate(pdfs, 1):
            try:
                out_file = BasePDFConverter.build_output_path(
                    input_root=input_root,
                    output_root=output_root,
                    pdf_path=pdf,
                    extension=".md",
                )

                # 跳过检查
                if out_file.exists() and not overwrite:
                    print(f"[{i}/{len(pdfs)}] ⏩ 跳过: {pdf.name}")
                    success += 1
                    continue

                print(f"[{i}/{len(pdfs)}] ⏳ 处理: {pdf.name}", end="... ", flush=True)

                # 执行转换
                results = converter.convert_single(pdf)

                # 写入结果
                BasePDFConverter.write_text_list(out_file, results, separator="\n\n---\n\n")
                print(f"✅")
                success += 1

            except Exception as e:
                print(f"\n❌ 失败: {str(e)[:100]}")
                failed.append(pdf.name)

        BasePDFConverter.summarize_batch(
            total=len(pdfs),
            success=success,
            failed=failed,
            title="LlamaIndex 处理",
        )
    
    def convert_single(self, pdf_path: Path) -> List[str]:
        # LlamaIndex 的 convert_single 是同步调用
        documents = self.reader.load_data(pdf_path)
        return [doc.text for doc in documents]

    def get_info(self) -> dict:
        return {"name": self.name}
