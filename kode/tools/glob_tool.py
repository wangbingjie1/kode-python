"""File pattern matching tool."""

from pathlib import Path
from typing import Optional, Type

from pydantic import BaseModel, Field

from .base import KodeTool


class GlobInput(BaseModel):
    """Input for GlobTool."""

    pattern: str = Field(description="Glob pattern to match files (e.g., **/*.py, src/**/*.ts)")
    path: Optional[str] = Field(
        default=None, description="Directory to search (default: current directory)"
    )


class GlobTool(KodeTool):
    """
    Find files by pattern matching.

    Equivalent to TypeScript's Glob tool in src/tools/GlobTool/
    """

    name: str = "Glob"
    description: str = """Find files by pattern (e.g., **/*.py). Returns paths sorted by modification time."""
    args_schema: Type[BaseModel] = GlobInput
    requires_permission: bool = False

    def _run(self, pattern: str, path: Optional[str] = None) -> str:
        """Find files matching glob pattern."""
        try:
            search_path = Path(path) if path else Path.cwd()

            if not search_path.exists():
                return f"Error: Path does not exist: {search_path}"

            # Find matching files
            matches = list(search_path.glob(pattern))

            if not matches:
                return f"No files found matching pattern: {pattern}"

            # Sort by modification time (most recent first)
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Format results with file size
            results = []
            for p in matches:
                if p.is_file():
                    file_size = p.stat().st_size

                    # Format size appropriately
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"

                    # Indicate large files with warning emoji
                    warning = " ⚠️" if file_size > 50_000 else ""

                    relative_path = str(p.relative_to(search_path))
                    results.append(f"{relative_path} ({size_str}){warning}")

            if not results:
                return f"No files found matching pattern: {pattern}"

            # Add summary header
            total_size = sum(p.stat().st_size for p in matches if p.is_file())
            total_size_kb = total_size / 1024
            header = f"Found {len(results)} file(s), total size: {total_size_kb:.1f} KB\n"
            header += "⚠️ = Large file (>50KB), consider using Grep for targeted search\n\n"

            return header + "\n".join(results)

        except Exception as e:
            return f"Error finding files: {str(e)}"