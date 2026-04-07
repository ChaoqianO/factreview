# converters/__init__.py
from .llama_index import LlamaIndexConverter
from .base import BasePDFConverter

# 尝试导入 Grobid，如果失败则提供友好提示
try:
    import requests  # Grobid 依赖 requests
    GROBID_AVAILABLE = True
    from .grobid import GrobidConverter
except ImportError:
    GROBID_AVAILABLE = False
    GrobidConverter = None

# 尝试导入 Nougat-OCR，如果失败则提供友好提示
try:
    import torch  # Nougat-OCR 依赖 torch
    NOUGAT_AVAILABLE = True
    from .nougat_ocr import NougatOCRConverter
except ImportError:
    NOUGAT_AVAILABLE = False
    NougatOCRConverter = None

class ConverterFactory:
    # 基础转换器
    CONVERTERS = {
        "llama-index": LlamaIndexConverter,
    }
    
    # 如果 Grobid 可用则添加
    if GROBID_AVAILABLE and GrobidConverter is not None:
        CONVERTERS["grobid"] = GrobidConverter
    
    # 如果 Nougat-OCR 可用则添加
    if NOUGAT_AVAILABLE and NougatOCRConverter is not None:
        CONVERTERS["nougat-ocr"] = NougatOCRConverter  # 新增

    # Science-Parse 转换器（依赖 requests，始终可用）
    try:
        from .science_parse import ScienceParseConverter
        CONVERTERS["science-parse"] = ScienceParseConverter
        SCIENCE_PARSE_AVAILABLE = True
    except Exception:
        SCIENCE_PARSE_AVAILABLE = False
    
    @classmethod
    def get_available_converters(cls):
        """获取所有可用的转换器（包括需要安装的）"""
        converters = list(cls.CONVERTERS.keys())
        if not GROBID_AVAILABLE:
            converters.append("grobid (需安装: pip install requests)")
        if not NOUGAT_AVAILABLE:  # 新增：Nougat提示
            converters.append("nougat-ocr (需安装: pip install nougat-ocr torch)")
        if not SCIENCE_PARSE_AVAILABLE:
            converters.append("science-parse (需安装: pip install requests)")
        return converters
    
    @classmethod
    def create_converter(cls, converter_name: str, **kwargs):
        converter_name = converter_name.lower()
        
        # 特殊处理：grobid 但依赖未安装
        if converter_name == "grobid" and not GROBID_AVAILABLE:
            print("❌ Grobid 转换器需要额外依赖")
            print("💡 请安装: pip install requests")
            print("💡 并启动 Grobid 服务: docker run -d -p 8070:8070 lfoppiano/grobid:0.8.0")
            raise ImportError("Grobid 转换器依赖未满足")
        
        # 特殊处理：nougat-ocr 但依赖未安装（新增）
        if converter_name == "nougat-ocr" and not NOUGAT_AVAILABLE:
            print("❌ Nougat-OCR 转换器需要额外依赖")
            print("💡 请安装: pip install nougat-ocr torch")
            print("💡 访问 https://pytorch.org/ 获取适合你系统的PyTorch安装命令")
            raise ImportError("Nougat-OCR 转换器依赖未满足")
        
        if converter_name not in cls.CONVERTERS:
            available = cls.get_available_converters()
            raise ValueError(f"未知转换器: '{converter_name}'，可用: {', '.join(available)}")
        
        return cls.CONVERTERS[converter_name](**kwargs)

def create_converter(converter_name: str, **kwargs):
    return ConverterFactory.create_converter(converter_name, **kwargs)