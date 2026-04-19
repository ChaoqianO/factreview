"""
Grobid 转换器 - 全栈封装版 (含服务检查与批量逻辑)
"""
from ._backend_base import BasePDFConverter
from pathlib import Path
from typing import List
import requests
import time

class GrobidConverter(BasePDFConverter):
    def __init__(self, **kwargs):
        super().__init__()
        self.name = "Grobid XML Converter"
        self.grobid_url = kwargs.get('grobid_url', 'http://localhost:8070').rstrip('/')
        self.timeout = kwargs.get('timeout', 120)
        
        # 初始化时检查服务状态
        if not self._check_service():
            self._print_help()
            # 抛出异常中断流程，避免主程序继续运行
            raise ConnectionError(f"无法连接到 Grobid 服务: {self.grobid_url}")

    def _check_service(self) -> bool:
        """检查 Grobid 服务是否存活"""
        try:
            # 尝试访问 Grobid 的健康检查接口
            resp = requests.get(f"{self.grobid_url}/api/isalive", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def _print_help(self):
        """打印 Docker 启动帮助信息"""
        print("\n" + "!" * 60)
        print("❌ 错误: 无法连接到 Grobid 服务！")
        print("!" * 60)
        print(f"📡 目标地址: {self.grobid_url}")
        print("\n💡 解决方案: 请确保已通过 Docker 启动 Grobid。")
        print("\n👉 启动命令参考:")
        print("   docker run -d --rm --init -p 8070:8070 lfoppiano/grobid:0.8.0")
        print("\n👉 检查容器状态:")
        print("   docker ps | grep grobid")
        print("!" * 60 + "\n")

    def convert_single(self, pdf_path: Path) -> List[str]:
        """调用 Grobid API 获取 TEI XML"""
        try:
            with open(pdf_path, 'rb') as f:
                response = requests.post(
                    f"{self.grobid_url}/api/processFulltextDocument",
                    files={'input': f},
                    data={'consolidateHeader': '1', 'consolidateCitations': '1'},
                    headers={'Accept': 'application/xml'},  
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    content = response.text.strip()
                    if content:
                        return [content]
                    raise Exception("Grobid 返回内容为空")
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
                    
        except requests.exceptions.ConnectionError:
            self._print_help()
            raise Exception("连接断开")
        except Exception as e:
            raise Exception(f"请求失败: {str(e)}")
    
    @staticmethod
    def run_batch_mode(input_root: Path, output_root: Path, grobid_url: str, timeout: int, overwrite: bool):
        """
        Grobid 专用批量处理逻辑
        """
        print(f"\n🌐 初始化 Grobid 连接: {grobid_url}")
        
        try:
            # 初始化会自动检查服务，不通则报错
            converter = GrobidConverter(grobid_url=grobid_url, timeout=timeout)
        except ConnectionError:
            return  # 帮助信息已在 __init__ 中打印，直接返回

        # 扫描文件
        pdfs = BasePDFConverter.discover_pdfs(input_root)
        if not pdfs:
            print("❌ 未找到有效 PDF 文件")
            return

        print(f"📊 扫描到 {len(pdfs)} 个文件")
        print(f"🚀 开始处理序列 (输出格式: .xml)...")

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
                    print(f"[{i}/{len(pdfs)}] ⏩ 跳过: {pdf.name}")
                    success += 1
                    continue

                print(f"[{i}/{len(pdfs)}] ⏳ 上传: {pdf.name}", end="... ", flush=True)
                
                start_t = time.time()
                result_list = converter.convert_single(pdf)
                cost_t = time.time() - start_t

                BasePDFConverter.write_text_list(out_file, result_list)
                print(f"✅ ({cost_t:.1f}s)")
                success += 1

            except Exception as e:
                # 如果是连接断开，已经在 convert_single 打印过帮助了，这里简略
                if "连接断开" not in str(e):
                    print(f"\n❌ 失败: {str(e)[:100]}")
                failed.append(pdf.name)

        BasePDFConverter.summarize_batch(
            total=len(pdfs),
            success=success,
            failed=failed,
            title="Grobid 处理",
        )

    def get_info(self) -> dict:
        return {
            "name": self.name,
            "description": "Grobid 学术PDF解析器 (需 Docker)",
            "output_dir": "converted_grobid/"
        }
