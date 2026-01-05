#!/usr/bin/env python3
"""
文档解析脚本 - 支持多种格式的文档解析

使用方法:
    python parse_document.py <file_path> [--output json|text] [--max-pages N]

支持格式:
    - PDF (.pdf)
    - Word (.docx)
    - Excel (.xlsx, .xls)
    - CSV (.csv)
    - 纯文本 (.txt, .md, .log)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


def parse_pdf(path: Path, max_pages: Optional[int] = None) -> Dict[str, Any]:
    """解析 PDF 文档"""
    try:
        import pdfplumber
    except ImportError:
        return {"error": "需要安装 pdfplumber: pip install pdfplumber"}

    result = {
        "format": "pdf",
        "file_name": path.name,
        "pages": [],
        "tables": [],
        "total_pages": 0,
        "text": ""
    }

    text_parts = []

    try:
        with pdfplumber.open(path) as pdf:
            result["total_pages"] = len(pdf.pages)
            pages_to_process = pdf.pages[:max_pages] if max_pages else pdf.pages

            for i, page in enumerate(pages_to_process, 1):
                page_data = {"page_num": i, "text": "", "tables": []}

                # 提取文本
                text = page.extract_text()
                if text:
                    page_data["text"] = text
                    text_parts.append(f"--- 第 {i} 页 ---\n{text}")

                # 提取表格
                tables = page.extract_tables()
                for j, table in enumerate(tables, 1):
                    if table:
                        table_data = {
                            "table_num": j,
                            "rows": table
                        }
                        page_data["tables"].append(table_data)

                        # 添加到文本表示
                        table_text = f"\n[表格 {j}]\n"
                        for row in table:
                            table_text += " | ".join(str(cell or "") for cell in row) + "\n"
                        text_parts.append(table_text)

                result["pages"].append(page_data)

            result["text"] = "\n".join(text_parts)

    except Exception as e:
        result["error"] = str(e)

    return result


def parse_docx(path: Path) -> Dict[str, Any]:
    """解析 Word 文档"""
    try:
        from docx import Document
    except ImportError:
        return {"error": "需要安装 python-docx: pip install python-docx"}

    result = {
        "format": "docx",
        "file_name": path.name,
        "paragraphs": [],
        "tables": [],
        "text": ""
    }

    text_parts = []

    try:
        doc = Document(path)

        # 处理段落
        for para in doc.paragraphs:
            if para.text.strip():
                para_data = {
                    "text": para.text,
                    "style": para.style.name if para.style else "Normal"
                }
                result["paragraphs"].append(para_data)

                # 处理标题样式
                if para.style and para.style.name.startswith('Heading'):
                    level = int(para.style.name[-1]) if para.style.name[-1].isdigit() else 1
                    text_parts.append(f"\n{'#' * level} {para.text}\n")
                else:
                    text_parts.append(para.text)

        # 处理表格
        for i, table in enumerate(doc.tables, 1):
            table_data = {
                "table_num": i,
                "rows": []
            }
            text_parts.append(f"\n[表格 {i}]\n")

            for row in table.rows:
                cells = [cell.text for cell in row.cells]
                table_data["rows"].append(cells)
                text_parts.append(" | ".join(cells))

            result["tables"].append(table_data)

        result["text"] = "\n".join(text_parts)

    except Exception as e:
        result["error"] = str(e)

    return result


def parse_excel(path: Path, max_rows: int = 1000) -> Dict[str, Any]:
    """解析 Excel 文档"""
    try:
        import pandas as pd
    except ImportError:
        return {"error": "需要安装 pandas 和 openpyxl: pip install pandas openpyxl"}

    result = {
        "format": "excel",
        "file_name": path.name,
        "sheets": [],
        "text": ""
    }

    text_parts = []

    try:
        excel_file = pd.ExcelFile(path)

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)

            sheet_data = {
                "name": sheet_name,
                "rows": len(df),
                "columns": list(df.columns.astype(str)),
                "preview": df.head(50).to_dict('records')
            }
            result["sheets"].append(sheet_data)

            # 文本表示
            text_parts.append(f"\n--- Sheet: {sheet_name} ---")
            text_parts.append(f"行数: {len(df)}, 列数: {len(df.columns)}")
            text_parts.append(f"列名: {', '.join(df.columns.astype(str))}")
            text_parts.append("\n数据预览:\n")

            # 限制行数
            preview_df = df.head(max_rows)
            text_parts.append(preview_df.to_string())

        result["text"] = "\n".join(text_parts)

    except Exception as e:
        result["error"] = str(e)

    return result


def parse_csv(path: Path, max_rows: int = 1000) -> Dict[str, Any]:
    """解析 CSV 文件"""
    try:
        import pandas as pd
    except ImportError:
        return {"error": "需要安装 pandas: pip install pandas"}

    result = {
        "format": "csv",
        "file_name": path.name,
        "text": ""
    }

    try:
        # 尝试不同编码
        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
            try:
                df = pd.read_csv(path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            return {"error": "无法识别文件编码"}

        result["rows"] = len(df)
        result["columns"] = list(df.columns.astype(str))
        result["preview"] = df.head(50).to_dict('records')

        # 文本表示
        text_parts = [
            f"CSV 文件: {path.name}",
            f"行数: {len(df)}, 列数: {len(df.columns)}",
            f"列名: {', '.join(df.columns.astype(str))}",
            "\n数据预览:\n",
            df.head(max_rows).to_string()
        ]
        result["text"] = "\n".join(text_parts)

    except Exception as e:
        result["error"] = str(e)

    return result


def parse_text(path: Path) -> Dict[str, Any]:
    """解析纯文本文件"""
    result = {
        "format": "text",
        "file_name": path.name,
        "text": ""
    }

    # 尝试不同编码
    for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
        try:
            text = path.read_text(encoding=encoding)
            result["text"] = text
            result["encoding"] = encoding
            result["lines"] = len(text.splitlines())
            result["chars"] = len(text)
            return result
        except UnicodeDecodeError:
            continue

    result["error"] = "无法识别文件编码"
    return result


def parse_document(file_path: str, max_pages: Optional[int] = None) -> Dict[str, Any]:
    """
    解析文档的主函数

    Args:
        file_path: 文档路径
        max_pages: 最大页数限制（仅 PDF）

    Returns:
        解析结果字典
    """
    path = Path(file_path)

    if not path.exists():
        return {"error": f"文件不存在: {file_path}"}

    suffix = path.suffix.lower()

    if suffix == '.pdf':
        return parse_pdf(path, max_pages)
    elif suffix == '.docx':
        return parse_docx(path)
    elif suffix in ['.xlsx', '.xls']:
        return parse_excel(path)
    elif suffix == '.csv':
        return parse_csv(path)
    elif suffix in ['.txt', '.md', '.log', '.json', '.xml', '.html']:
        return parse_text(path)
    else:
        return {"error": f"不支持的文档格式: {suffix}"}


def main():
    parser = argparse.ArgumentParser(description='文档解析工具')
    parser.add_argument('file_path', help='文档路径')
    parser.add_argument('--output', choices=['json', 'text'], default='text',
                        help='输出格式 (默认: text)')
    parser.add_argument('--max-pages', type=int, default=None,
                        help='最大页数限制 (仅 PDF)')

    args = parser.parse_args()

    result = parse_document(args.file_path, args.max_pages)

    if args.output == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if 'error' in result:
            print(f"错误: {result['error']}", file=sys.stderr)
            sys.exit(1)
        else:
            print(result.get('text', ''))


if __name__ == '__main__':
    main()
