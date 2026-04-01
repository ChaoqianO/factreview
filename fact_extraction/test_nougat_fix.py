# test_nougat_fix.py
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append('.')

from converters.nougat_ocr import NougatOCRConverter

# 创建转换器实例
converter = NougatOCRConverter()
print(f"转换器: {converter.name}")
print(f"设备: {converter.device}")
print(f"超时: {converter.timeout}")

# 测试转换
test_pdf = Path("/home/dukehang/pdf_workspace/input_pdfs/high/2501.11316v1.pdf")
if test_pdf.exists():
    print(f"\n测试文件: {test_pdf}")
    print("开始转换...")
    result = converter.convert_single(test_pdf)
    if len(result) > 0 and not result[0].startswith("错误"):
        print(f"✅ 转换成功!")
        print(f"字符数: {len(result[0])}")
        print(f"前500字符:")
        print(result[0][:500])
    else:
        print(f"❌ 转换失败: {result[0] if result else '无结果'}")
else:
    print(f"测试文件不存在: {test_pdf}")
    print("使用其他PDF测试...")
    # 查找其他PDF
    pdf_dir = Path("/home/dukehang/pdf_workspace/input_pdfs/high/")
    if pdf_dir.exists():
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if pdf_files:
            test_pdf = pdf_files[0]
            print(f"使用: {test_pdf}")
            result = converter.convert_single(test_pdf)
            print(f"结果: {'成功' if len(result) > 0 else '失败'}")
