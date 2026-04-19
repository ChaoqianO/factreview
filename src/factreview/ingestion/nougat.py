"""
Nougat-OCR 转换器 - 全栈封装版 (含批量逻辑)
"""
from ._backend_base import BasePDFConverter
from pathlib import Path
from typing import List
import torch
import tempfile
import time
import os
import shutil
import subprocess as sp

class NougatOCRConverter(BasePDFConverter):
    def __init__(self, **kwargs):
        super().__init__()
        self.name = "Nougat-OCR (Official)"
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        timeout = kwargs.get('timeout', None)
        # 0 表示不限时
        if isinstance(timeout, int) and timeout == 0:
            timeout = None
        self.timeout = timeout

    @staticmethod
    def run_batch_mode(input_root: Path, output_root: Path, timeout: int, overwrite: bool):
        """
        Nougat 专用批量处理逻辑
        """
        print(f"\n🧠 初始化 Nougat 模型 (Device: {'CUDA' if torch.cuda.is_available() else 'CPU'})...")
        
        # 1. 扫描文件
        pdfs = BasePDFConverter.discover_pdfs(input_root)
        if not pdfs:
            print("❌ 未找到有效 PDF 文件")
            return

        # 2. 初始化实例
        converter = NougatOCRConverter(timeout=timeout)

        print(f"📊 扫描到 {len(pdfs)} 个文件")
        print(f"🚀 开始逐个处理 (这是一个慢速大模型，请耐心等待)...")

        success = 0
        failed = []

        # 3. 循环处理
        for i, pdf in enumerate(pdfs, 1):
            try:
                out_file = BasePDFConverter.build_output_path(
                    input_root=input_root,
                    output_root=output_root,
                    pdf_path=pdf,
                    extension=".mmd",
                )

                if out_file.exists() and not overwrite:
                    print(f"[{i}/{len(pdfs)}] ⏩ 跳过: {pdf.name}")
                    success += 1
                    continue

                print(f"[{i}/{len(pdfs)}] ⏳ 正在计算: {pdf.name}")
                
                # 执行转换
                results = converter.convert_single(pdf)

                if results and results[0]:
                    BasePDFConverter.write_text_list(out_file, [results[0]])
                    print(f"    ✅ 保存成功")
                    success += 1
                else:
                    print(f"    ❌ 输出为空")
                    failed.append(pdf.name)

            except Exception as e:
                print(f"\n❌ 失败: {str(e)[:100]}")
                failed.append(pdf.name)

        # 4. 汇总
        BasePDFConverter.summarize_batch(
            total=len(pdfs),
            success=success,
            failed=failed,
            title="Nougat 处理",
        )

    def convert_single(self, pdf_path: Path) -> List[str]:
        temp_dir = Path(tempfile.mkdtemp(prefix="nougat_"))
        try:
            return self._run_nougat(pdf_path, temp_dir) or [""]
        except FileNotFoundError:
            return [f"未找到 nougat 命令，请安装: pip install nougat-ocr"]
        except Exception as e:
            raise Exception(f"执行异常: {str(e)}")
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def _run_nougat(self, pdf_path: Path, temp_dir: Path) -> List[str]:
        # 构造命令
        cmd = [
            'nougat',
            str(pdf_path),
            '--out', str(temp_dir),
            '--markdown',
            '--no-skipping', # 强制处理每一页
            '--batchsize', '1' # 防止显存炸裂
        ]
        
        # 环境变量设置 (缓存路径)
        env = dict(os.environ)
        hf_home = env.get('HF_HOME', os.path.expanduser('~/.cache/huggingface'))
        env['HF_HOME'] = hf_home
        os.makedirs(env['HF_HOME'], exist_ok=True)

        start_time = time.time()
        
        # 使用 Popen 实时获取输出
        process = sp.Popen(
            cmd,
            stdout=sp.PIPE,
            stderr=sp.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )

        last_activity = time.time()
        
        while True:
            # 超时检查
            if self.timeout is not None and (time.time() - start_time > self.timeout):
                process.terminate()
                raise TimeoutError(f"处理超时 ({self.timeout}s)")

            line = process.stdout.readline()
            if line:
                line = line.strip()
                last_activity = time.time()
                # 过滤并打印进度
                if "%" in line or "it/s" in line:
                    print(f"    ⚡ {line}")
                elif "error" in line.lower():
                    print(f"    ⚠️  {line}")

            if process.poll() is not None:
                break
            
            # 长时间无响应提示
            if time.time() - last_activity > 60:
                print(f"    ⏰ 模型正在运算中，请耐心等待...")
                last_activity = time.time()
                
            time.sleep(0.1)

        if process.returncode != 0:
            raise Exception(f"Nougat 进程非正常退出 (Code: {process.returncode})")

        # 读取结果 (支持 .mmd 和 .md)
        for ext in ['.mmd', '.md']:
            expected = temp_dir / f"{pdf_path.stem}{ext}"
            if not expected.exists():
                # Nougat 有时候会用文件名而不是 stem
                expected = temp_dir / f"{pdf_path.name}{ext}"

            if expected.exists() and expected.stat().st_size > 0:
                with open(expected, "r", encoding="utf-8") as f:
                    return [f.read()]

        return None

    def get_info(self) -> dict:
        return {"name": self.name}
