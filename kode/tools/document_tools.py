"""
文档处理工具 - 支持读取和解析多种文档格式

依赖库:
- PDF: pdfplumber
- DOCX: python-docx
- Excel/CSV: pandas + openpyxl
- 编码检测: charset-normalizer

支持格式:
- PDF (.pdf)
- Word (.docx)
- Excel (.xlsx, .xls)
- CSV (.csv)
- 纯文本 (.txt, .md, .log)
"""

from pathlib import Path
from typing import Type, Optional, List, ClassVar
from pydantic import BaseModel, Field

from .base import KodeTool


# 启动时检查必需依赖
def _check_dependencies():
    """检查必需依赖，缺失直接报错"""
    missing = []

    try:
        import pandas
    except ImportError:
        missing.append("pandas")

    try:
        import charset_normalizer
    except ImportError:
        missing.append("charset-normalizer")

    if missing:
        raise ImportError(
            f"文档工具缺少必需依赖: {', '.join(missing)}\n"
            f"请运行: pip install {' '.join(missing)}"
        )


_check_dependencies()


class DocumentReadInput(BaseModel):
    """文档读取工具输入参数"""

    file_path: str = Field(
        ..., description="文档文件路径（支持 PDF、Word、Excel、CSV、TXT 等格式）"
    )
    max_pages: Optional[int] = Field(None, description="最大页数限制（仅 PDF 有效）")
    max_rows: Optional[int] = Field(100, description="Excel/CSV 数据预览最大行数（默认 100 行）")
    max_output_chars: Optional[int] = Field(
        8000, description="输出内容最大字符数（超过则压缩，默认 8000 约 2000 tokens）"
    )


class DocumentReadTool(KodeTool):
    """
    文档读取工具

    - PDF: pdfplumber 提取文本和表格
    - DOCX: python-docx 解析
    - Excel/CSV: pandas 提供数据统计
    """

    name: str = "DocumentRead"
    description: str = """读取文档文件并返回文本内容。

支持格式:
- PDF (.pdf) - pdfplumber 提取文本和表格
- Word (.docx) - python-docx 解析
- Excel (.xlsx, .xls) - pandas 提取所有 sheet 数据和统计信息
- CSV (.csv) - pandas 解析，chardet 检测编码
- 纯文本 (.txt, .md) - chardet 检测编码

示例:
- 读取 PDF: DocumentRead(file_path="./report.pdf")
- 读取 Excel: DocumentRead(file_path="./data.xlsx", max_rows=500)
"""
    args_schema: Type[BaseModel] = DocumentReadInput
    requires_permission: bool = False

    # 压缩阈值常量
    COMPRESS_THRESHOLD: ClassVar[int] = 10000  # 超过此字符数触发压缩

    def _run(
        self,
        file_path: str,
        max_pages: Optional[int] = None,
        max_rows: Optional[int] = 500,
        max_output_chars: Optional[int] = 10000,
    ) -> str:
        """执行文档读取"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            content = self._parse_pdf(path, max_pages)
        elif suffix == ".docx":
            content = self._parse_docx(path)
        elif suffix in [".xlsx", ".xls"]:
            content = self._parse_excel(path, max_rows)
        elif suffix == ".csv":
            content = self._parse_csv(path, max_rows)
        elif suffix in [".txt", ".md", ".log", ".json", ".xml", ".html"]:
            content = self._parse_text(path)
        else:
            raise ValueError(f"不支持的文档格式: {suffix}")

        # 超过阈值则压缩
        threshold = max_output_chars or self.COMPRESS_THRESHOLD
        if len(content) > threshold:
            content = self._compress_content(content, threshold, path.name)

        return content

    def _compress_content(self, content: str, max_chars: int, filename: str) -> str:
        """
        使用 Haiku 模型智能压缩文档内容。

        策略：
        1. 保留文档元信息（文件名、类型、统计）
        2. 用 Haiku 生成结构化摘要
        3. 如果 Haiku 调用失败，回退到规则截断
        """
        import os

        original_len = len(content)

        # 尝试用 Haiku 智能摘要
        try:
            import anthropic

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                # 没有 API key，回退到规则压缩
                return self._fallback_compress(content, max_chars, original_len)

            client = anthropic.Anthropic(api_key=api_key)

            # 构建压缩 prompt
            compress_prompt = f"""请对以下文档内容进行结构化摘要，保留关键信息。

要求：
1. 保留文档的结构（标题、章节、表格结构）
2. 提取关键数据点和数值
3. 总结主要内容，不要遗漏重要信息
4. 如果有表格，保留列名和关键行的数据
5. 输出控制在 {max_chars // 2} 字符以内

文档内容：
{content[:50000]}
"""  # 限制输入以避免超出 Haiku 上下文

            response = client.messages.create(
                model="claude-haiku-3-5-20241022",
                max_tokens=max_chars // 2,  # 约 max_chars/4 tokens
                messages=[{"role": "user", "content": compress_prompt}],
            )

            summary = response.content[0].text

            # 添加压缩说明头
            compressed = f"""📄 文档: {filename}
⚠️ 内容已压缩 (原始 {original_len:,} 字符 → {len(summary):,} 字符)

{summary}
"""
            return compressed

        except Exception as e:
            # Haiku 调用失败，回退到规则压缩
            import logging

            logging.getLogger(__name__).warning(f"Haiku 压缩失败，回退到规则压缩: {e}")
            return self._fallback_compress(content, max_chars, original_len)

    def _fallback_compress(self, content: str, max_chars: int, original_len: int) -> str:
        """规则压缩：保留头部和尾部"""
        head_size = int(max_chars * 0.6)  # 60% 给头部
        tail_size = int(max_chars * 0.3)  # 30% 给尾部

        head = content[:head_size]
        tail = content[-tail_size:] if tail_size > 0 else ""

        compressed = f"""{head}

... [内容已压缩: 原始 {original_len:,} 字符，已截断中间部分] ...

{tail}"""
        return compressed

    def _parse_pdf(self, path: Path, max_pages: Optional[int] = None) -> str:
        """解析 PDF 文档，使用 pdfplumber 提取文本和表格"""
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("需要安装 pdfplumber: pip install pdfplumber")

        import pandas as pd

        text_parts = []
        table_count = 0

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
                for table in tables:
                    if table and len(table) > 0:
                        table_count += 1
                        text_parts.append(f"\n[表格 {table_count}] (第 {i} 页)")

                        if len(table) > 1:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            text_parts.append(df.to_string(index=False))
                        else:
                            for row in table:
                                text_parts.append(" | ".join(str(cell or "") for cell in row))

        if table_count > 0:
            text_parts.insert(3, f"表格数量: {table_count}")

        return "\n".join(text_parts)

    def _parse_docx(self, path: Path) -> str:
        """解析 Word 文档，使用 python-docx"""
        try:
            from docx import Document
        except ImportError:
            raise ImportError("需要安装 python-docx: pip install python-docx")

        import pandas as pd

        doc = Document(path)
        text_parts = []

        text_parts.append(f"📝 Word 文档: {path.name}")
        text_parts.append("-" * 50)

        # 处理段落
        para_count = 0
        for para in doc.paragraphs:
            if para.text.strip():
                para_count += 1
                if para.style and para.style.name.startswith("Heading"):
                    level = int(para.style.name[-1]) if para.style.name[-1].isdigit() else 1
                    text_parts.append(f"\n{'#' * level} {para.text}\n")
                else:
                    text_parts.append(para.text)

        # 处理表格
        for i, table in enumerate(doc.tables, 1):
            text_parts.append(f"\n[表格 {i}]")
            rows_data = []
            for row in table.rows:
                rows_data.append([cell.text for cell in row.cells])
            if len(rows_data) > 1:
                df = pd.DataFrame(rows_data[1:], columns=rows_data[0])
                text_parts.append(df.to_string(index=False))
            else:
                for row_data in rows_data:
                    text_parts.append(" | ".join(row_data))

        text_parts.insert(2, f"段落数: {para_count}, 表格数: {len(doc.tables)}")

        return "\n".join(text_parts)

    def _parse_excel(self, path: Path, max_rows: int = 1000) -> str:
        """解析 Excel 文档，使用 pandas"""
        import pandas as pd

        try:
            excel_file = pd.ExcelFile(path)
        except Exception as e:
            raise ValueError(f"无法打开 Excel 文件: {e}")

        text_parts = []
        text_parts.append(f"📊 Excel 文档: {path.name}")
        text_parts.append(f"Sheet 数量: {len(excel_file.sheet_names)}")
        text_parts.append("-" * 50)

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)

            text_parts.append(f"\n{'=' * 40}")
            text_parts.append(f"Sheet: {sheet_name}")
            text_parts.append(f"{'=' * 40}")
            text_parts.append(f"行数: {len(df)}, 列数: {len(df.columns)}")

            # 列信息
            text_parts.append("\n📋 列信息:")
            for col in df.columns:
                non_null = df[col].notna().sum()
                null_count = df[col].isna().sum()
                dtype = df[col].dtype
                text_parts.append(f"  - {col}: {dtype} (非空: {non_null}, 空值: {null_count})")

            # 数值列统计
            numeric_cols = df.select_dtypes(include=["number"]).columns
            if len(numeric_cols) > 0:
                text_parts.append("\n📈 数值统计:")
                stats = df[numeric_cols].describe()
                text_parts.append(stats.to_string())

            # 数据预览
            preview_rows = min(max_rows, len(df))
            text_parts.append(f"\n📄 数据预览 (前 {preview_rows} 行):\n")
            text_parts.append(df.head(preview_rows).to_string())

        return "\n".join(text_parts)

    def _parse_csv(self, path: Path, max_rows: int = 1000) -> str:
        """解析 CSV 文件，使用 charset_normalizer 检测编码"""
        import pandas as pd
        from charset_normalizer import from_bytes

        # 检测编码
        with open(path, "rb") as f:
            raw_data = f.read()

        results = from_bytes(raw_data)
        best_match = results.best()

        if not best_match:
            raise ValueError(f"无法检测文件编码: {path.name}")

        encoding = best_match.encoding
        df = pd.read_csv(path, encoding=encoding)

        text_parts = [
            f"📋 CSV 文件: {path.name}",
            f"编码: {encoding}",
            f"行数: {len(df)}, 列数: {len(df.columns)}",
            "-" * 50,
        ]

        # 列信息
        text_parts.append("\n📋 列信息:")
        for col in df.columns:
            non_null = df[col].notna().sum()
            null_count = df[col].isna().sum()
            dtype = df[col].dtype
            text_parts.append(f"  - {col}: {dtype} (非空: {non_null}, 空值: {null_count})")

        # 数值列统计
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            text_parts.append("\n📈 数值统计:")
            stats = df[numeric_cols].describe()
            text_parts.append(stats.to_string())

        # 分类列统计
        cat_cols = df.select_dtypes(include=["object", "category"]).columns
        if len(cat_cols) > 0:
            text_parts.append("\n🏷️ 分类列唯一值:")
            for col in cat_cols:
                unique_count = df[col].nunique()
                text_parts.append(f"  - {col}: {unique_count} 种")
                if unique_count <= 10:
                    top_values = df[col].value_counts().head(5)
                    for val, count in top_values.items():
                        text_parts.append(f"      {val}: {count}")

        # 数据预览
        preview_rows = min(max_rows, len(df))
        text_parts.append(f"\n📄 数据预览 (前 {preview_rows} 行):\n")
        text_parts.append(df.head(preview_rows).to_string())

        return "\n".join(text_parts)

    def _parse_text(self, path: Path) -> str:
        """解析纯文本文件，使用 charset_normalizer 检测编码"""
        from charset_normalizer import from_bytes

        with open(path, "rb") as f:
            raw_data = f.read()

        results = from_bytes(raw_data)
        best_match = results.best()

        if not best_match:
            raise ValueError(f"无法检测文件编码: {path.name}")

        encoding = best_match.encoding
        text = str(best_match)
        lines = text.splitlines()

        header = [
            f"📄 文本文件: {path.name}",
            f"编码: {encoding}",
            f"行数: {len(lines)}",
            f"字符数: {len(text)}",
            "-" * 50,
            "",
        ]
        return "\n".join(header) + text

    async def _arun(
        self,
        file_path: str,
        max_pages: Optional[int] = None,
        max_rows: Optional[int] = 100,
        max_output_chars: Optional[int] = 8000,
    ) -> str:
        """异步执行"""
        return self._run(file_path, max_pages, max_rows, max_output_chars)


class DocumentSearchInput(BaseModel):
    """文档搜索工具输入参数"""

    file_path: str = Field(..., description="文档文件路径")
    query: str = Field(..., description="搜索关键词或问题")
    top_k: int = Field(5, description="返回最相关的段落数量")


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
        lines = text.split("\n")
        chunks = []
        current_chunk = []
        current_size = 0

        for line in lines:
            line_size = len(line)
            if current_size + line_size > chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    def _search_chunks(self, chunks: List[str], query: str, top_k: int) -> List[tuple]:
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
