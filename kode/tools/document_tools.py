"""
文档处理工具 - 支持读取和解析多种文档格式

支持格式:
- PDF (.pdf)
- Word (.docx)
- Excel (.xlsx, .xls)
- CSV (.csv)
- 纯文本 (.txt, .md, .log)
"""

from pathlib import Path
from typing import Type, Optional, Dict, Any, List
from pydantic import BaseModel, Field

from .base import KodeTool


class DocumentReadInput(BaseModel):
    """文档读取工具输入参数"""

    file_path: str = Field(
        ...,
        description="文档文件路径（支持 PDF、Word、Excel、CSV、TXT 等格式）"
    )
    max_pages: Optional[int] = Field(
        None,
        description="最大页数限制（仅 PDF 有效）"
    )
    max_rows: Optional[int] = Field(
        1000,
        description="Excel/CSV 最大行数限制"
    )


class DocumentReadTool(KodeTool):
    """
    文档读取工具

    读取并解析各种格式的文档，返回文本内容。
    支持格式: PDF, DOCX, XLSX, CSV, TXT, MD
    """

    name: str = "DocumentRead"
    description: str = """读取文档文件并返回文本内容。

支持格式:
- PDF (.pdf) - 提取文本和表格
- Word (.docx) - 提取段落和表格
- Excel (.xlsx, .xls) - 提取所有 sheet 数据
- CSV (.csv) - 解析表格数据
- 纯文本 (.txt, .md) - 直接读取

示例:
- 读取 PDF: DocumentRead(file_path="./report.pdf")
- 读取 Excel: DocumentRead(file_path="./data.xlsx", max_rows=500)
"""
    args_schema: Type[BaseModel] = DocumentReadInput
    requires_permission: bool = False

    def _run(
        self,
        file_path: str,
        max_pages: Optional[int] = None,
        max_rows: Optional[int] = 1000
    ) -> str:
        """执行文档读取"""
        path = Path(file_path)

        if not path.exists():
            return f"错误: 文件不存在 - {file_path}"

        suffix = path.suffix.lower()

        try:
            if suffix == '.pdf':
                return self._parse_pdf(path, max_pages)
            elif suffix == '.docx':
                return self._parse_docx(path)
            elif suffix in ['.xlsx', '.xls']:
                return self._parse_excel(path, max_rows)
            elif suffix == '.csv':
                return self._parse_csv(path, max_rows)
            elif suffix in ['.txt', '.md', '.log', '.json', '.xml', '.html']:
                return self._parse_text(path)
            else:
                return f"错误: 不支持的文档格式 - {suffix}"
        except Exception as e:
            return f"错误: 解析文档失败 - {str(e)}"

    def _parse_pdf(self, path: Path, max_pages: Optional[int] = None) -> str:
        """解析 PDF 文档"""
        try:
            import pdfplumber
        except ImportError:
            return "错误: 需要安装 pdfplumber (pip install pdfplumber)"

        text_parts = []

        with pdfplumber.open(path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = pdf.pages[:max_pages] if max_pages else pdf.pages

            text_parts.append(f"📄 PDF 文档: {path.name}")
            text_parts.append(f"总页数: {total_pages}")
            if max_pages and max_pages < total_pages:
                text_parts.append(f"已读取前 {max_pages} 页")
            text_parts.append("-" * 50)

            for i, page in enumerate(pages_to_process, 1):
                text_parts.append(f"\n--- 第 {i} 页 ---\n")

                # 提取文本
                text = page.extract_text()
                if text:
                    text_parts.append(text)

                # 提取表格
                tables = page.extract_tables()
                for j, table in enumerate(tables, 1):
                    if table:
                        text_parts.append(f"\n[表格 {j}]")
                        for row in table:
                            text_parts.append(" | ".join(str(cell or "") for cell in row))

        return "\n".join(text_parts)

    def _parse_docx(self, path: Path) -> str:
        """解析 Word 文档"""
        try:
            from docx import Document
        except ImportError:
            return "错误: 需要安装 python-docx (pip install python-docx)"

        doc = Document(path)
        text_parts = []

        text_parts.append(f"📝 Word 文档: {path.name}")
        text_parts.append("-" * 50)

        # 处理段落
        for para in doc.paragraphs:
            if para.text.strip():
                if para.style and para.style.name.startswith('Heading'):
                    level = int(para.style.name[-1]) if para.style.name[-1].isdigit() else 1
                    text_parts.append(f"\n{'#' * level} {para.text}\n")
                else:
                    text_parts.append(para.text)

        # 处理表格
        for i, table in enumerate(doc.tables, 1):
            text_parts.append(f"\n[表格 {i}]")
            for row in table.rows:
                cells = [cell.text for cell in row.cells]
                text_parts.append(" | ".join(cells))

        return "\n".join(text_parts)

    def _parse_excel(self, path: Path, max_rows: int = 1000) -> str:
        """解析 Excel 文档"""
        try:
            import pandas as pd
        except ImportError:
            return "错误: 需要安装 pandas 和 openpyxl (pip install pandas openpyxl)"

        text_parts = []
        excel_file = pd.ExcelFile(path)

        text_parts.append(f"📊 Excel 文档: {path.name}")
        text_parts.append(f"Sheet 数量: {len(excel_file.sheet_names)}")
        text_parts.append("-" * 50)

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)

            text_parts.append(f"\n--- Sheet: {sheet_name} ---")
            text_parts.append(f"行数: {len(df)}, 列数: {len(df.columns)}")
            text_parts.append(f"列名: {', '.join(df.columns.astype(str))}")

            # 数据类型摘要
            text_parts.append("\n列类型:")
            for col in df.columns:
                text_parts.append(f"  - {col}: {df[col].dtype}")

            # 数据预览
            preview_rows = min(max_rows, len(df))
            text_parts.append(f"\n数据预览 (前 {preview_rows} 行):\n")
            text_parts.append(df.head(preview_rows).to_string())

        return "\n".join(text_parts)

    def _parse_csv(self, path: Path, max_rows: int = 1000) -> str:
        """解析 CSV 文件"""
        try:
            import pandas as pd
        except ImportError:
            return "错误: 需要安装 pandas (pip install pandas)"

        # 尝试不同编码
        df = None
        used_encoding = None
        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
            try:
                df = pd.read_csv(path, encoding=encoding)
                used_encoding = encoding
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            return "错误: 无法识别文件编码"

        text_parts = [
            f"📋 CSV 文件: {path.name}",
            f"编码: {used_encoding}",
            f"行数: {len(df)}, 列数: {len(df.columns)}",
            f"列名: {', '.join(df.columns.astype(str))}",
            "-" * 50,
        ]

        # 列类型
        text_parts.append("\n列类型:")
        for col in df.columns:
            text_parts.append(f"  - {col}: {df[col].dtype}")

        # 数据预览
        preview_rows = min(max_rows, len(df))
        text_parts.append(f"\n数据预览 (前 {preview_rows} 行):\n")
        text_parts.append(df.head(preview_rows).to_string())

        return "\n".join(text_parts)

    def _parse_text(self, path: Path) -> str:
        """解析纯文本文件"""
        # 尝试不同编码
        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
            try:
                text = path.read_text(encoding=encoding)
                lines = text.splitlines()

                header = [
                    f"📄 文本文件: {path.name}",
                    f"编码: {encoding}",
                    f"行数: {len(lines)}",
                    f"字符数: {len(text)}",
                    "-" * 50,
                    ""
                ]
                return "\n".join(header) + text
            except UnicodeDecodeError:
                continue

        return "错误: 无法识别文件编码"

    async def _arun(
        self,
        file_path: str,
        max_pages: Optional[int] = None,
        max_rows: Optional[int] = 1000
    ) -> str:
        """异步执行"""
        return self._run(file_path, max_pages, max_rows)


class DocumentSearchInput(BaseModel):
    """文档搜索工具输入参数"""

    file_path: str = Field(
        ...,
        description="文档文件路径"
    )
    query: str = Field(
        ...,
        description="搜索关键词或问题"
    )
    top_k: int = Field(
        5,
        description="返回最相关的段落数量"
    )


class DocumentSearchTool(KodeTool):
    """
    文档搜索工具

    在文档中搜索与查询相关的内容。
    使用简单的关键词匹配算法。
    """

    name: str = "DocumentSearch"
    description: str = """在文档中搜索相关内容。

根据关键词在文档中查找最相关的段落，返回匹配结果。

示例:
- 搜索财务数据: DocumentSearch(file_path="./report.pdf", query="营收增长")
- 搜索合同条款: DocumentSearch(file_path="./contract.docx", query="违约责任")
"""
    args_schema: Type[BaseModel] = DocumentSearchInput
    requires_permission: bool = False

    def _run(self, file_path: str, query: str, top_k: int = 5) -> str:
        """执行文档搜索"""
        # 首先读取文档
        read_tool = DocumentReadTool()
        content = read_tool._run(file_path)

        if content.startswith("错误:"):
            return content

        # 分块
        chunks = self._chunk_text(content)

        # 搜索
        results = self._search_chunks(chunks, query, top_k)

        if not results:
            return f"未找到与 '{query}' 相关的内容"

        # 格式化结果
        output = [f"🔍 搜索结果: '{query}'", f"找到 {len(results)} 个相关段落", "-" * 50]

        for i, (score, chunk) in enumerate(results, 1):
            output.append(f"\n📌 结果 {i} (相关度: {score:.2f})")
            output.append(chunk[:500] + "..." if len(chunk) > 500 else chunk)

        return "\n".join(output)

    def _chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """将文本分块"""
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0

        for line in lines:
            line_size = len(line)
            if current_size + line_size > chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def _search_chunks(
        self,
        chunks: List[str],
        query: str,
        top_k: int
    ) -> List[tuple]:
        """搜索最相关的文本块"""
        query_words = set(query.lower().split())

        scored_chunks = []
        for chunk in chunks:
            chunk_lower = chunk.lower()
            # 计算匹配分数
            score = sum(1 for word in query_words if word in chunk_lower)
            if score > 0:
                scored_chunks.append((score, chunk))

        # 按分数排序
        scored_chunks.sort(reverse=True, key=lambda x: x[0])

        return scored_chunks[:top_k]

    async def _arun(self, file_path: str, query: str, top_k: int = 5) -> str:
        """异步执行"""
        return self._run(file_path, query, top_k)
