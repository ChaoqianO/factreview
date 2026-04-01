#!/usr/bin/env python3
"""
批量PDF转Markdown - 支持high/low子文件夹
保存为 convert.py

使用方法：
1. python convert.py                    # 默认不覆盖
2. python convert.py -o                 # 覆盖已有文件
3. python convert.py --overwrite        # 覆盖已有文件
4. python convert.py 自定义文件夹路径 -o  # 指定输入文件夹并覆盖
"""

import sys
from pathlib import Path
import datetime
import json

# ============ 新增：参数解析 ============
def parse_arguments():
    """解析命令行参数"""
    input_folder = "input_pdfs"  # 默认输入文件夹
    overwrite = False            # 默认不覆盖
    
    args = sys.argv[1:]  # 跳过脚本名
    
    i = 0
    while i < len(args):
        if args[i] in ["-o", "--overwrite"]:
            overwrite = True
            i += 1
        elif not args[i].startswith("-"):
            # 如果不是以-开头，就认为是输入文件夹路径
            input_folder = args[i]
            i += 1
        else:
            print(f"⚠️  未知参数: {args[i]}")
            i += 1
    
    return input_folder, overwrite

# ============ 导入PDFMarkerReader ============
try:
    from llama_index.readers.pdf_marker import PDFMarkerReader
    print("✅ PDFMarkerReader 导入成功")
except ImportError as e:
    print(f"❌ 无法导入 PDFMarkerReader: {e}")
    print("请先安装: pip install llama-index-readers-pdf-marker")
    print("激活虚拟环境: source ~/llama_env/bin/activate")
    sys.exit(1)

# ============ 核心功能函数 ============
def get_valid_pdfs(folder_path, output_dir, overwrite=False):
    """
    获取有效的PDF文件，排除干扰项
    返回: PDF文件路径列表
    """
    valid_pdfs = []
    folder = Path(folder_path)
    
    if not folder.exists() or not folder.is_dir():
        return valid_pdfs
    
    for item in folder.iterdir():
        # 只处理普通文件
        if not item.is_file():
            continue
            
        # 检查扩展名（不区分大小写）
        if item.suffix.lower() != '.pdf':
            continue
            
        # 检查文件名中是否包含 Zone.Identifier（不区分大小写）
        if 'zone.identifier' in item.name.lower():
            print(f"  跳过 Zone.Identifier 文件: {item.name}")
            continue
            
        # 检查文件大小是否过小（可能是损坏或空文件）
        file_size = item.stat().st_size
        if file_size < 1024:  # 小于1KB
            print(f"  跳过过小文件: {item.name} ({file_size} 字节)")
            continue
        
        # ============ 新增：检查是否已存在且不覆盖 ============
        if not overwrite:
            md_filename = item.stem + ".md"
            md_path = output_dir / md_filename
            if md_path.exists():
                print(f"  跳过已存在文件: {item.name} (输出文件 {md_filename} 已存在)")
                continue
        # ====================================================
            
        # 通过所有检查，添加到有效列表
        valid_pdfs.append(item)
    
    return valid_pdfs

def process_folder(pdf_files, output_dir, reader, result_dict, level_name, overwrite=False):
    """处理一个文件夹的PDF文件"""
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] {level_name}: {pdf_file.name}")
        
        try:
            # 读取PDF
            documents = reader.load_data(pdf_file)
            
            # 生成输出文件名（保留原文件名）
            md_filename = pdf_file.stem + ".md"
            md_path = output_dir / md_filename
            
            # ============ 新增：覆盖前的提示 ============
            if overwrite and md_path.exists():
                print(f"    ⚠️  覆盖已存在的文件: {md_filename}")
            # ===========================================
            
            # 获取当前时间
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 保存Markdown
            with open(md_path, "w", encoding="utf-8") as f:
                # 添加文件头信息
                f.write(f"# {pdf_file.name}\n")
                f.write(f"**原始路径**: {pdf_file.absolute()}\n")
                f.write(f"**级别**: {level_name}\n")
                f.write(f"**转换时间**: {current_time}\n")
                f.write(f"**文档块数**: {len(documents)}\n")
                f.write("-" * 40 + "\n\n")
                
                # 写入内容
                for j, doc in enumerate(documents):
                    if len(documents) > 1:
                        f.write(f"## 第{j+1}部分\n\n")
                    f.write(doc.text)
                    if j < len(documents) - 1:
                        f.write("\n\n---\n\n")
            
            # 统计信息
            file_size_kb = pdf_file.stat().st_size / 1024
            char_count = sum(len(doc.text) for doc in documents)
            
            print(f"    ✅ 成功")
            print(f"       大小: {file_size_kb:.1f}KB → {char_count:,}字符")
            print(f"       分块: {len(documents)}个")
            
            result_dict["success"] += 1
            
        except Exception as e:
            error_msg = str(e)
            print(f"    ❌ 失败: {error_msg[:80]}...")
            result_dict["failed"].append((level_name, pdf_file.name, error_msg))

def create_report(output_main, results):
    """创建转换报告"""
    report_file = output_main / "conversion_report.md"
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# PDF转Markdown批量转换报告\n")
        f.write(f"**生成时间**: {current_time}\n\n")
        
        f.write("## 📊 转换统计\n\n")
        
        # HIGH级别统计
        if results["high"]["total"] > 0:
            high_success = results["high"]["success"]
            high_total = results["high"]["total"]
            f.write("### 🔵 HIGH 级别\n")
            f.write(f"- 总文件数: {high_total}\n")
            f.write(f"- 成功转换: {high_success}\n")
            f.write(f"- 转换失败: {high_total - high_success}\n")
            f.write(f"- 成功率: {high_success/high_total*100:.1f}%\n\n")
        
        # LOW级别统计
        if results["low"]["total"] > 0:
            low_success = results["low"]["success"]
            low_total = results["low"]["total"]
            f.write("### 🟡 LOW 级别\n")
            f.write(f"- 总文件数: {low_total}\n")
            f.write(f"- 成功转换: {low_success}\n")
            f.write(f"- 转换失败: {low_total - low_success}\n")
            f.write(f"- 成功率: {low_success/low_total*100:.1f}%\n\n")
        
        # 总体统计
        total_pdfs = results["high"]["total"] + results["low"]["total"]
        total_success = results["high"]["success"] + results["low"]["success"]
        f.write("### 📈 总体统计\n")
        f.write(f"- 总文件数: {total_pdfs}\n")
        f.write(f"- 成功转换: {total_success}\n")
        f.write(f"- 转换失败: {total_pdfs - total_success}\n")
        if total_pdfs > 0:
            f.write(f"- 成功率: {total_success/total_pdfs*100:.1f}%\n\n")
        
        # 文件列表
        f.write("## 📁 输出文件列表\n\n")
        
        # HIGH级别文件
        high_dir = output_main / "high_converted"
        if high_dir.exists():
            f.write("### HIGH 级别输出文件\n")
            md_files = list(high_dir.glob("*.md"))
            for md_file in sorted(md_files):
                size_kb = md_file.stat().st_size / 1024
                f.write(f"- `{md_file.name}` ({size_kb:.1f} KB)\n")
            f.write("\n")
        
        # LOW级别文件
        low_dir = output_main / "low_converted"
        if low_dir.exists():
            f.write("LOW 级别输出文件\n")
            md_files = list(low_dir.glob("*.md"))
            for md_file in sorted(md_files):
                size_kb = md_file.stat().st_size / 1024
                f.write(f"- `{md_file.name}` ({size_kb:.1f} KB)\n")
        
        # 失败文件
        all_failed = results["high"]["failed"] + results["low"]["failed"]
        if all_failed:
            f.write("\n## ❌ 失败文件列表\n\n")
            for level, file_name, error in all_failed:
                f.write(f"### {level} - {file_name}\n")
                f.write(f"错误: `{error}`\n\n")
    
    print(f"\n📋 详细报告已生成: {report_file}")

# ============ 主程序 ============
def main():
    """主函数"""
    # ============ 修改：解析参数 ============
    input_folder, overwrite = parse_arguments()
    
    print("=" * 60)
    print("    批量PDF转Markdown工具 (支持high/low子文件夹)")
    if overwrite:
        print("    ⚠️  模式: 覆盖已存在文件")
    else:
        print("    ✅ 模式: 跳过已存在文件")
    print("=" * 60)
    
    input_path = Path(input_folder)
    
    if not input_path.exists():
        print(f"\n❌ 错误：找不到文件夹 '{input_folder}'")
        print(f"请确保目录结构如下：")
        print(f"  {input_folder}/")
        print(f"  ├── high/         # 放high级别的PDF")
        print(f"  └── low/          # 放low级别的PDF")
        return
    
    # 2. 检查high/low子文件夹
    high_folder = input_path / "high"
    low_folder = input_path / "low"
    
    # 创建子文件夹如果不存在
    high_folder.mkdir(exist_ok=True)
    low_folder.mkdir(exist_ok=True)
    
    # 3. 创建输出文件夹结构
    output_main = Path("converted_markdown")
    output_high = output_main / "high_converted"
    output_low = output_main / "low_converted"
    
    # 创建所有输出目录
    output_main.mkdir(exist_ok=True)
    output_high.mkdir(exist_ok=True)
    output_low.mkdir(exist_ok=True)
    
    print(f"\n📂 输出文件夹结构：")
    print(f"  {output_main.absolute()}/")
    print(f"  ├── high_converted/")
    print(f"  └── low_converted/")
    
    # 4. 使用健壮的函数查找PDF文件 (传入overwrite参数)
    print(f"\n🔍 正在扫描PDF文件...")
    high_pdfs = get_valid_pdfs(high_folder, output_high, overwrite)
    low_pdfs = get_valid_pdfs(low_folder, output_low, overwrite)
    
    # 调试输出：显示找到的文件详情
    print(f"  扫描结果:")
    print(f"    high文件夹: {len(list(high_folder.iterdir()))} 个文件 -> {len(high_pdfs)} 个有效PDF")
    print(f"    low文件夹: {len(list(low_folder.iterdir()))} 个文件 -> {len(low_pdfs)} 个有效PDF")
    
    total_pdfs = len(high_pdfs) + len(low_pdfs)
    
    if total_pdfs == 0:
        print(f"\n❌ 在high和low文件夹中都没有找到有效的PDF文件")
        print(f"请将PDF文件放入：")
        print(f"  - {high_folder.absolute()}/")
        print(f"  - {low_folder.absolute()}/")
        return
    
    print(f"\n📁 输入主文件夹：{input_path.absolute()}")
    print(f"├── high/ : {len(high_pdfs)}个PDF文件")
    print(f"└── low/  : {len(low_pdfs)}个PDF文件")
    print(f"📄 总计：{total_pdfs}个PDF文件")
    
    # 5. 初始化转换器
    print("\n🔄 初始化PDFMarkerReader...")
    try:
        reader = PDFMarkerReader()
        print("✅ PDFMarkerReader 初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return
    
    # 6. 批量转换（分别处理high和low，传入overwrite参数）
    print("\n开始批量转换...")
    print("-" * 60)
    
    results = {
        "high": {"success": 0, "failed": [], "total": len(high_pdfs)},
        "low": {"success": 0, "failed": [], "total": len(low_pdfs)}
    }
    
    # 处理high文件夹
    if high_pdfs:
        print(f"\n🔵 处理 HIGH 级别文件 ({len(high_pdfs)}个):")
        print("-" * 40)
        process_folder(high_pdfs, output_high, reader, results["high"], "HIGH", overwrite)
    
    # 处理low文件夹
    if low_pdfs:
        print(f"\n🟡 处理 LOW 级别文件 ({len(low_pdfs)}个):")
        print("-" * 40)
        process_folder(low_pdfs, output_low, reader, results["low"], "LOW", overwrite)
    
    # 7. 显示结果
    print("\n" + "=" * 60)
    print("转换完成！")
    print("=" * 60)
    
    # HIGH级别结果
    if results["high"]["total"] > 0:
        high_success = results["high"]["success"]
        high_total = results["high"]["total"]
        print(f"\n🔵 HIGH 级别:")
        print(f"   ✅ 成功: {high_success}/{high_total}")
        print(f"   📂 输出到: {output_high.absolute()}")
    
    # LOW级别结果
    if results["low"]["total"] > 0:
        low_success = results["low"]["success"]
        low_total = results["low"]["total"]
        print(f"\n🟡 LOW 级别:")
        print(f"   ✅ 成功: {low_success}/{low_total}")
        print(f"   📂 输出到: {output_low.absolute()}")
    
    # 总体统计
    total_success = results["high"]["success"] + results["low"]["success"]
    print(f"\n📊 总体统计:")
    print(f"   📄 总文件数: {total_pdfs}")
    print(f"   ✅ 成功转换: {total_success}")
    print(f"   ❌ 转换失败: {total_pdfs - total_success}")
    if total_pdfs > 0:
        print(f"   📈 成功率: {total_success/total_pdfs*100:.1f}%")
    
    # 8. 显示失败文件
    all_failed = results["high"]["failed"] + results["low"]["failed"]
    if all_failed:
        print(f"\n❌ 失败的文件 ({len(all_failed)}个):")
        for level, file_name, error in all_failed:
            print(f"   • [{level}] {file_name}")
            if error:
                print(f"     错误: {error[:80]}...")
    
    # 9. 生成详细报告
    create_report(output_main, results)

# ============ 程序入口 ============
if __name__ == "__main__":
    # 运行主程序
    main()