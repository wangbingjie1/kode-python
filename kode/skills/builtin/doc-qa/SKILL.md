---
name: doc-qa
description: 文档问答助手 - 读取 PDF、Word、Excel、TXT、Markdown 等文档并基于内容回答问题。支持多文档联合问答和知识库构建。
license: MIT
user-invocable: true
---

# 文档问答指南

## 概述

文档问答 (Doc-QA) 是一个智能文档理解和问答系统，支持读取多种格式的文档并基于内容回答用户问题。

## 支持的文档格式

| 格式 | 扩展名 | 解析库 |
|------|--------|--------|
| PDF | .pdf | pdfplumber, pypdf |
| Word | .docx | python-docx |
| Excel | .xlsx, .xls | openpyxl, pandas |
| 纯文本 | .txt | 内置 |
| Markdown | .md | 内置 |
| CSV | .csv | pandas |

## 使用方法

### 1. 单文档问答

```python
# 用户提供文档路径，AI 自动读取并回答问题
# 示例：用户说 "帮我分析这份报告 /path/to/report.pdf"
```

### 2. 多文档联合问答

```python
# 用户提供多个文档，AI 综合多个文档内容回答
# 示例：用户说 "对比这两份合同 /contract1.pdf 和 /contract2.pdf"
```

## 工作流程

### Step 1: 文档解析

根据文档格式选择合适的解析方法：

```python
from pathlib import Path

def parse_document(file_path: str) -> str:
    """解析文档并返回文本内容"""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == '.pdf':
        return parse_pdf(path)
    elif suffix == '.docx':
        return parse_docx(path)
    elif suffix in ['.xlsx', '.xls']:
        return parse_excel(path)
    elif suffix in ['.txt', '.md']:
        return path.read_text(encoding='utf-8')
    elif suffix == '.csv':
        return parse_csv(path)
    else:
        raise ValueError(f"不支持的文档格式: {suffix}")
```

### Step 2: PDF 解析

```python
import pdfplumber

def parse_pdf(path: Path) -> str:
    """解析 PDF 文档"""
    text_parts = []

    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            # 提取文本
            text = page.extract_text()
            if text:
                text_parts.append(f"--- 第 {i} 页 ---\n{text}")

            # 提取表格
            tables = page.extract_tables()
            for j, table in enumerate(tables, 1):
                if table:
                    text_parts.append(f"\n[表格 {j}]\n")
                    for row in table:
                        text_parts.append(" | ".join(str(cell or "") for cell in row))

    return "\n".join(text_parts)
```

### Step 3: Word 文档解析

```python
from docx import Document

def parse_docx(path: Path) -> str:
    """解析 Word 文档"""
    doc = Document(path)
    text_parts = []

    for para in doc.paragraphs:
        if para.text.strip():
            # 处理标题样式
            if para.style.name.startswith('Heading'):
                level = int(para.style.name[-1]) if para.style.name[-1].isdigit() else 1
                text_parts.append(f"\n{'#' * level} {para.text}\n")
            else:
                text_parts.append(para.text)

    # 处理表格
    for table in doc.tables:
        text_parts.append("\n[表格]\n")
        for row in table.rows:
            cells = [cell.text for cell in row.cells]
            text_parts.append(" | ".join(cells))

    return "\n".join(text_parts)
```

### Step 4: Excel 解析

```python
import pandas as pd

def parse_excel(path: Path) -> str:
    """解析 Excel 文档"""
    text_parts = []

    # 读取所有 sheet
    excel_file = pd.ExcelFile(path)

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        text_parts.append(f"\n--- Sheet: {sheet_name} ---\n")
        text_parts.append(f"行数: {len(df)}, 列数: {len(df.columns)}\n")
        text_parts.append("列名: " + ", ".join(df.columns.astype(str)))
        text_parts.append("\n数据预览:\n")
        text_parts.append(df.head(20).to_string())

    return "\n".join(text_parts)
```

### Step 5: CSV 解析

```python
def parse_csv(path: Path) -> str:
    """解析 CSV 文件"""
    df = pd.read_csv(path)

    text_parts = [
        f"CSV 文件: {path.name}",
        f"行数: {len(df)}, 列数: {len(df.columns)}",
        f"列名: {', '.join(df.columns.astype(str))}",
        "\n数据预览:\n",
        df.head(50).to_string()
    ]

    return "\n".join(text_parts)
```

## 问答策略

### 策略 1: 直接上下文问答

对于小文档（< 50KB），直接将全文作为上下文：

```python
def answer_with_full_context(document_text: str, question: str) -> str:
    """使用全文上下文回答问题"""
    prompt = f"""基于以下文档内容回答问题。

文档内容:
{document_text}

问题: {question}

请基于文档内容给出准确、详细的回答。如果文档中没有相关信息，请明确说明。
"""
    return prompt
```

### 策略 2: 分块检索问答 (RAG)

对于大文档（> 50KB），使用分块检索：

```python
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """将文本分块"""
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks

def search_relevant_chunks(chunks: list, query: str, top_k: int = 5) -> list:
    """搜索最相关的文本块（简单关键词匹配）"""
    # 简单实现：基于关键词匹配
    query_words = set(query.lower().split())

    scored_chunks = []
    for i, chunk in enumerate(chunks):
        chunk_words = set(chunk.lower().split())
        score = len(query_words & chunk_words)
        scored_chunks.append((score, i, chunk))

    # 按分数排序
    scored_chunks.sort(reverse=True)

    return [chunk for _, _, chunk in scored_chunks[:top_k]]
```

## 最佳实践

1. **文件路径处理**
   - 支持绝对路径和相对路径
   - 自动处理 Windows/Linux 路径差异
   - 验证文件存在性后再解析

2. **大文档处理**
   - 超过 100 页的 PDF 分批处理
   - Excel 超过 10000 行时只预览头尾
   - 自动检测文档编码

3. **错误处理**
   - 加密 PDF 提示用户提供密码
   - 损坏文件给出明确错误信息
   - 编码问题自动尝试多种编码

4. **问答质量**
   - 引用原文时标注页码/位置
   - 不确定时明确说明
   - 提供相关段落供用户验证

## 依赖安装

```bash
# PDF 解析
pip install pdfplumber pypdf

# Word 解析
pip install python-docx

# Excel 解析
pip install openpyxl pandas
```

## 使用示例

```
用户: /doc-qa 帮我分析这份财务报告 ./reports/Q3_2024.pdf

AI: 好的，让我读取并分析这份财务报告...
    [读取 PDF 文件]
    [提取文本和表格]

    这份 Q3 2024 财务报告共 15 页，主要内容包括：
    1. 营收概况：Q3 总营收 1.2 亿元，同比增长 15%
    2. 成本分析：...
    3. 利润情况：...

    您想了解哪个方面的详细信息？
```

## 注意事项

- 敏感文档请确保数据安全
- 大文件处理可能需要较长时间
- 扫描版 PDF 可能需要 OCR 处理
