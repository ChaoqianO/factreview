#!/usr/bin/env python3
"""
批量 PDF 转换主程序 (注册表分发版)
用法: python convert.py -i <FILE|DIR> -c <converter> [--output-dir DIR] [-o]
"""
import argparse
import sys
from pathlib import Path
from typing import Callable, Dict


def _load_science_parse_runner() -> Callable:
    from converters.science_parse import ScienceParseConverter

    return ScienceParseConverter.run_batch_mode


def _load_grobid_runner() -> Callable:
    from converters.grobid import GrobidConverter

    return GrobidConverter.run_batch_mode


def _load_nougat_runner() -> Callable:
    from converters.nougat_ocr import NougatOCRConverter

    return NougatOCRConverter.run_batch_mode


def _load_llama_runner() -> Callable:
    from converters.llama_index import LlamaIndexConverter

    return LlamaIndexConverter.run_batch_mode


def _converter_registry() -> Dict[str, Callable]:
    return {
        "science-parse": _load_science_parse_runner,
        "grobid": _load_grobid_runner,
        "nougat-ocr": _load_nougat_runner,
        "llama-index": _load_llama_runner,
    }


def _parse_args() -> argparse.Namespace:
    registry = _converter_registry()
    parser = argparse.ArgumentParser(description="批量 PDF 转换工具")
    parser.add_argument("-i", "--input", default="input_pdfs", help="输入路径 (PDF 文件或目录)")
    parser.add_argument(
        "-c",
        "--converter",
        default="science-parse",
        choices=sorted(registry.keys()),
        help="转换器类型",
    )
    parser.add_argument("-o", "--overwrite", action="store_true", help="覆盖已有输出")
    parser.add_argument("--output-dir", default=None, help="自定义输出目录")

    # 模块专用参数
    parser.add_argument("--science-parse-jar", default="libs/science-parse-cli.jar")
    parser.add_argument("--grobid-url", default="http://localhost:8070")
    parser.add_argument("--timeout", type=int, default=0, help="超时时间(秒)，0 表示不限时")
    return parser.parse_args()


def _resolve_output_dir(converter: str, output_dir: str | None) -> Path:
    if output_dir:
        return Path(output_dir)
    return Path(f"converted_{converter.replace('-', '_')}")


def main() -> int:
    args = _parse_args()
    registry = _converter_registry()

    input_root = Path(args.input)
    if not input_root.exists():
        print(f"❌ 输入路径不存在: {input_root}")
        return 1

    output_root = _resolve_output_dir(args.converter, args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"    PDF 批量转换 | 模式: {args.converter}")
    print(f"    输入路径: {input_root}")
    print(f"    输出路径: {output_root}")
    print("=" * 60)

    try:
        runner = registry[args.converter]()
        if args.converter == "science-parse":
            runner(
                input_path=input_root,
                output_path=output_root,
                jar_path=args.science_parse_jar,
            )
        elif args.converter == "grobid":
            runner(
                input_root=input_root,
                output_root=output_root,
                grobid_url=args.grobid_url,
                timeout=args.timeout,
                overwrite=args.overwrite,
            )
        elif args.converter == "nougat-ocr":
            runner(
                input_root=input_root,
                output_root=output_root,
                timeout=args.timeout,
                overwrite=args.overwrite,
            )
        else:
            runner(
                input_root=input_root,
                output_root=output_root,
                overwrite=args.overwrite,
            )
    except ImportError as exc:
        print(f"❌ 依赖未安装或模块不可用: {exc}")
        return 2
    except Exception as exc:
        print(f"❌ 执行失败: {exc}")
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
