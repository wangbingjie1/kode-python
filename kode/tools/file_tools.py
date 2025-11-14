"""File operation tools."""

import os
from pathlib import Path
from typing import Any, Optional, Type

from pydantic import BaseModel, Field

from .base import KodeTool


class FileReadInput(BaseModel):
    """Input for FileReadTool."""

    file_path: str = Field(description="Absolute path to the file to read")
    offset: Optional[int] = Field(
        default=None, description="Line number to start reading from (0-indexed)"
    )
    limit: Optional[int] = Field(
        default=None, description="Number of lines to read (default: all)"
    )
    force: bool = Field(
        default=False, description="Force read large files without warning (default: False)"
    )


class FileReadTool(KodeTool):
    """
    Read file contents from the filesystem.

    Equivalent to TypeScript's Read tool in src/tools/ReadTool/
    """

    name: str = "FileRead"
    description: str = """Reads a file from the local filesystem.
- The file_path parameter must be an absolute path
- By default, reads up to 2000 lines from the beginning
- Can specify offset and limit for large files
- Lines longer than 2000 characters will be truncated
- Results returned with line numbers (cat -n format)"""
    args_schema: Type[BaseModel] = FileReadInput
    requires_permission: bool = False  # Reading is generally safe

    def _run(
        self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None, force: bool = False
    ) -> str:
        """Read file contents."""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"Error: File not found: {file_path}"

            if not path.is_file():
                return f"Error: Not a file: {file_path}"

            # Check file size and warn if large (unless using pagination or force)
            file_size = path.stat().st_size
            size_threshold = 50_0000  # 50KB threshold

            if file_size > size_threshold and offset is None and not force:
                estimated_tokens = file_size // 4  # Rough estimate: 1 token ≈ 4 chars
                size_kb = file_size / 1024

                return f"""⚠️ 大文件警告（上下文管理）

文件信息:
- 路径: {file_path}
- 大小: {size_kb:.1f} KB
- 估算 tokens: ~{estimated_tokens:,}

建议的高效工作流:

1️⃣ 使用 Grep 精确定位目标代码（带行号）:
   Grep(
       pattern="你要找的关键词或函数名",
       path="{file_path}",
       output_mode="content"
   )
   → 会返回: {path.name}:行号:匹配的代码

2️⃣ 根据行号精确读取（节省 90%+ tokens）:
   FileRead(
       file_path="{file_path}",
       offset=行号-10,
       limit=50
   )

如果确实需要读取整个文件:
   FileRead(file_path="{file_path}", force=True)

💡 提示: 使用 Grep → FileRead(分页) 工作流可以节省 90%+ 的上下文消耗!
"""

            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            # Apply offset and limit
            start = offset or 0
            end = start + limit if limit else len(lines)
            selected_lines = lines[start:end]

            # Format with line numbers (1-indexed)
            result = []
            for i, line in enumerate(selected_lines, start=start + 1):
                # Truncate long lines
                if len(line) > 2000:
                    line = line[:2000] + "...[truncated]\n"
                result.append(f"{i:6d}\t{line.rstrip()}")

            return "\n".join(result)

        except Exception as e:
            return f"Error reading file: {str(e)}"


class FileWriteInput(BaseModel):
    """Input for FileWriteTool."""

    file_path: str = Field(description="Absolute path to the file to write")
    content: str = Field(description="Content to write to the file")


class FileWriteTool(KodeTool):
    """
    Write content to a file.

    Equivalent to TypeScript's Write tool in src/tools/WriteTool/
    """

    name: str = "FileWrite"
    description: str = """Writes a file to the local filesystem.
- Overwrites existing files
- Creates parent directories if needed
- Should prefer editing existing files over writing new ones
- The file_path must be an absolute path"""
    args_schema: Type[BaseModel] = FileWriteInput
    requires_permission: bool = True

    def _run(self, file_path: str, content: str) -> str:
        """Write content to file."""
        try:
            path = Path(file_path)

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"Successfully wrote {len(content)} characters to {file_path}"

        except Exception as e:
            return f"Error writing file: {str(e)}"


class FileEditInput(BaseModel):
    """Input for FileEditTool."""

    file_path: str = Field(description="Absolute path to the file to edit")
    old_string: str = Field(description="The exact string to replace")
    new_string: str = Field(description="The string to replace it with")
    replace_all: bool = Field(
        default=False, description="Replace all occurrences (default: False, requires unique match)"
    )


class FileEditTool(KodeTool):
    """
    Edit file by replacing exact strings.

    Equivalent to TypeScript's Edit tool in src/tools/EditTool/
    """

    name: str = "FileEdit"
    description: str = """Performs exact string replacements in files.
- Must preserve exact indentation and whitespace
- The edit will FAIL if old_string is not unique (unless replace_all=True)
- Use replace_all for renaming variables/functions across a file
- Always prefer editing over creating new files"""
    args_schema: Type[BaseModel] = FileEditInput
    requires_permission: bool = True

    def _run(
        self, file_path: str, old_string: str, new_string: str, replace_all: bool = False
    ) -> str:
        """Edit file by replacing strings."""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"Error: File not found: {file_path}"

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if old_string exists
            if old_string not in content:
                return f"Error: String not found in file: {old_string[:100]}..."

            # Check uniqueness if not replace_all
            if not replace_all:
                count = content.count(old_string)
                if count > 1:
                    return (
                        f"Error: String appears {count} times in file. "
                        f"Either make it unique or use replace_all=True"
                    )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                count = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                count = 1

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return f"Successfully replaced {count} occurrence(s) in {file_path}"

        except Exception as e:
            return f"Error editing file: {str(e)}"