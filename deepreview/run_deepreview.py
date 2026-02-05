import argparse
import sys
import os
import json
import time
import subprocess
import shutil
import tempfile
import glob

# 将当前目录添加到 Python 路径，确保能找到 module 包
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

def extract_text_from_pdf(pdf_path):
    """
    使用 MinerU (magic-pdf) 将 PDF 转换为 Markdown 纯文本。
    """
    print(f"[Info] 正在使用 MinerU (magic-pdf) 解析 PDF: {pdf_path}")

    # 1. 检查 magic-pdf 是否可用
    if shutil.which("magic-pdf") is None:
        print("[Error] 未找到 'magic-pdf' 命令。")
        print("请确保已安装 MinerU 并配置好环境: pip install magic-pdf[full]")
        print("参考: https://github.com/opendatalab/MinerU")
        sys.exit(1)

    # 2. 创建临时目录存放解析结果
    # 使用 tempfile 生成一个临时文件夹，用完后会自动清理（如果是 with 语句管理，但在 Windows 上 subprocess 可能锁文件，所以小心）
    # 这里我们手动创建，如果不使用 context manager，需要自己清理，或者依赖系统清理
    # 为简单起见，使用 TemporaryDirectory
    
    try:
        with tempfile.TemporaryDirectory() as temp_out_dir:
            print(f"[Info] 正在执行 MinerU 解析 (这可能需要一些时间)...")
            
            # 3. 调用 magic-pdf 命令行
            # 命令格式: magic-pdf -p input.pdf -o output_dir -m auto
            cmd = ["magic-pdf", "-p", pdf_path, "-o", temp_out_dir, "-m", "auto"]
            
            # 使用 shell=False 更安全，但在某些 Windows 环境下调用 .exe 可能需注意
            # 这里的 check=True 会在命令失败时抛出异常
            subprocess.run(cmd, check=True, stdout=None, stderr=None) # 这里让输出直接显示在终端，方便用户看进度

            # 4. 查找生成的 .md 文件
            # MinerU 的输出结构通常是: output_dir/pdf_name/auto/pdf_name.md
            # 我们直接递归搜索 .md 文件
            md_files = glob.glob(os.path.join(temp_out_dir, "**", "*.md"), recursive=True)
            
            if not md_files:
                print("[Error] MinerU 未能生成 .md 文件。请检查上方的 MinerU 报错信息。")
                sys.exit(1)
            
            # 通常只有一个 md 文件
            target_md = md_files[0]
            print(f"[Info] 读取解析结果: {target_md}")
            
            with open(target_md, "r", encoding="utf-8") as f:
                text = f.read()
                
            if not text.strip():
                print("[Warning] 解析得到的 Markdown 为空。")
                sys.exit(1)

            print(f"[Info] 提取文本成功，共 {len(text)} 个字符")
            return text

    except subprocess.CalledProcessError as e:
        print(f"[Error] MinerU 命令行执行失败 (Exit Code: {e.returncode})")
        print("可能原因: 缺少模型文件、配置文件错误或环境问题。")
        sys.exit(1)
    except Exception as e:
        print(f"[Error] 解析过程中发生错误: {e}")
        sys.exit(1)

def process_single_pdf(pdf_path, reviewer, output_dir):
    """
    处理单个 PDF 的完整流程：提取 -> 评审 -> 保存
    """
    print(f"\n{'='*50}")
    print(f"[Processing] 开始处理文件: {pdf_path}")
    print(f"{'='*50}")

    # 1. 准备数据
    try:
        paper_text = extract_text_from_pdf(pdf_path)
    except Exception as e:
        print(f"[Error] 提取文本失败，跳过此文件: {e}")
        return

    # 2. 执行评审
    print("[Info] 开始评审 (这可能需要几分钟)...")
    start_time = time.time()
    try:
        result = reviewer(paper_text)
    except Exception as e:
        print(f"[Error] 评审过程出错: {e}")
        return
    end_time = time.time()
    print(f"[Info] 评审完成，耗时 {end_time - start_time:.2f} 秒")

    # 3. 保存结果
    filename = os.path.basename(pdf_path)
    base_name = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{base_name}_review.json")
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"[Success] 结果已保存至: {output_path}")
    except Exception as e:
        print(f"[Error] 保存文件失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="DeepReview 论文评审启动工具")
    
    # 输入数据参数 (设置默认值为 'pdf' 文件夹)
    parser.add_argument("pdf_path", nargs="?", default="pdf", 
                        help="输入数据的路径 (PDF文件或包含PDF的文件夹)。默认值为 'pdf' 文件夹。")
    
    # 模型配置参数
    parser.add_argument("--mode", default="standard", choices=["standard", "best", "fast"], 
                        help="评审模式: standard(标准), best(深度/联网), fast(快速)")
    parser.add_argument("--model_size", default="14B", choices=["7B", "14B"], 
                        help="模型参数量 (默认 14B, 显存不够可试 7B)")
    parser.add_argument("--gpu_util", type=float, default=0.9, 
                        help="GPU 显存占用上限 (0.0 - 1.0)")
    parser.add_argument("--output_dir", default=".", 
                        help="结果输出目录 (默认为当前目录)")

    args = parser.parse_args()

    # 1. 确定要处理的文件列表
    target_files = []
    
    # 如果路径不存在，尝试在当前目录下查找（兼容用户输入文件名的情况）
    if not os.path.exists(args.pdf_path):
        current_dir_path = os.path.join(current_dir, args.pdf_path)
        default_dir_path = os.path.join(current_dir, "pdf", args.pdf_path)
        
        if os.path.exists(current_dir_path):
            args.pdf_path = current_dir_path
        elif os.path.exists(default_dir_path):
            args.pdf_path = default_dir_path
        else:
            print(f"[Error] 输入路径不存在: {args.pdf_path}")
            print(f"       (尝试查找了 {current_dir_path} 和 {default_dir_path})")
            sys.exit(1)

    # 判断是文件还是目录
    if os.path.isfile(args.pdf_path):
        target_files.append(args.pdf_path)
    elif os.path.isdir(args.pdf_path):
        print(f"[Info] 输入为目录，正在查找目录下的 .pdf 文件: {args.pdf_path}")
        found_files = glob.glob(os.path.join(args.pdf_path, "*.pdf"))
        found_files.sort()
        target_files.extend(found_files)
    
    if not target_files:
        print(f"[Error] 在路径下未找到任何 PDF 文件: {args.pdf_path}")
        sys.exit(1)

    print(f"[Info] 共找到 {len(target_files)} 个 PDF 文件准备处理。")

    # 2. 导入 DeepReview (只导入一次)
    try:
        print("[Info] 正在加载 DeepReview 模块...")
        from module.deepreview import DeepReview
    except ImportError as e:
        import traceback
        traceback.print_exc()
        print(f"[Error] 导入失败: {e}")
        print("请确保已安装必要的依赖: pip install vllm transformers pypdf requests")
        sys.exit(1)

    # 3. 初始化模型 (只初始化一次)
    print(f"[Info] 初始化模型 (Size: {args.model_size}, Mode: {args.mode})...")
    try:
        reviewer = DeepReview(
            mode=args.mode,
            model_size=args.model_size,
            gpu_memory_utilization=args.gpu_util
        )
    except Exception as e:
        print(f"[Error] 模型初始化失败: {e}")
        sys.exit(1)

    # 4. 批量执行评审
    for i, pdf_file in enumerate(target_files):
        print(f"\n>> 进度: {i+1}/{len(target_files)}")
        process_single_pdf(pdf_file, reviewer, args.output_dir)

    print(f"\n[Done] 所有任务执行完毕。")

if __name__ == "__main__":
    main()
