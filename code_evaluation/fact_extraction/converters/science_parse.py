"""
Science-Parse 转换器 (极速批量版)
针对 32GB 内存机器优化的专用版本。
"""
from .base import BasePDFConverter
from pathlib import Path
import subprocess
import os
import sys

class ScienceParseConverter(BasePDFConverter):
    def __init__(self, **kwargs):
        super().__init__()
        self.name = "Science-Parse Batch Engine"
        # 即使在极速模式下，Base类可能还是需要初始化这个实例，所以保留基本属性
        self.jar_path = kwargs.get('science_parse_jar', 'libs/science-parse-cli.jar')

    @staticmethod
    def run_batch_mode(input_path: Path, output_path: Path, jar_path: str):
        """
        执行 Science-Parse 的原生批量模式。
        一次启动 JVM，处理整个目录，速度最快且稳定。
        """
        # 1. 寻找 Java 环境
        java_cmd = 'java'
        candidates = [
            '/usr/lib/jvm/java-8-openjdk-amd64/bin/java', 
            '/usr/lib/jvm/java-1.8.0-openjdk-amd64/bin/java'
        ]
        for c in candidates:
            if os.path.exists(c) and os.access(c, os.X_OK):
                java_cmd = c
                break

        # 检查 Jar 包
        if not Path(jar_path).exists():
            print(f"❌ 错误: 找不到 Science-Parse Jar 包: {jar_path}")
            return

        print(f"\n🚀 激活 [Science-Parse 极速批量模式]")
        print(f"📦 输入: {input_path}")
        print(f"📂 输出: {output_path}")
        print(f"☕ 引擎: {java_cmd}")

        # 2. 构造启动命令 (32GB 内存优化配置)
        # Heap 4G + Direct 16G = 20G Max
        cmd = [
            java_cmd,
            # 加速启动
            '-Djava.security.egd=file:/dev/./urandom',
            '-Xverify:none',
            # 内存配置
            '-Xmx4g', 
            '-XX:MaxDirectMemorySize=16g', 
            # 日志屏蔽
            '-Dorg.slf4j.simpleLogger.defaultLogLevel=error',
            '-Dorg.apache.commons.logging.Log=org.apache.commons.logging.impl.NoOpLog',
            # 执行参数
            '-jar', jar_path,
            '-o', str(output_path),
            str(input_path) 
        ]

        print("⏳ 正在启动处理引擎 (首次启动需加载模型，约5-10秒)...")
        
        try:
            # 3. 执行并监控
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # 将错误流并入输出流，方便统一过滤
                text=True
            )

            # 4. 实时输出进度
            count = 0
            for line in process.stdout:
                line = line.strip()
                if not line: continue
                # 过滤废话日志
                if "DEBUG" in line or "WARN" in line: continue
                
                if "Saved to" in line:
                    count += 1
                    fname = Path(line.split('Saved to')[-1].strip()).name
                    print(f"  [{count}] ✅ 生成: {fname}")
                elif "Processing" in line:
                    print(f"  ⚡ 处理: {line.split('Processing')[-1].strip()}")
                elif "Error" in line:
                    print(f"  ❌ {line}")
            
            process.wait()
            
            if process.returncode == 0:
                print(f"\n🎉 极速处理完成! 结果保存在: {output_path}")
            else:
                print(f"\n⚠️ 处理结束，返回码: {process.returncode}")

        except Exception as e:
            print(f"\n❌ 执行过程中发生严重错误: {e}")

    # ========================================================
    # 废弃接口存根 (防止 Base 类调用报错，虽然在 convert.py 里不会走到这)
    # ========================================================
    def convert_single(self, pdf_path: Path):
        raise NotImplementedError("Science-Parse 现在只支持极速批量模式，请使用 run_batch_mode")

    def get_info(self) -> dict:
        return {"name": self.name}