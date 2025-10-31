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
    description: str = """Fast file pattern matching tool.
- Supports glob patterns like "**/*.js" or "src/**/*.ts"
- Returns matching file paths sorted by modification time
- Use this when you need to find files by name patterns
- Works with any codebase size
- DO NOT use 'find' command via Bash - use this tool instead"""
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

            # Format results
            results = [str(p.relative_to(search_path)) for p in matches if p.is_file()]

            if not results:
                return f"No files found matching pattern: {pattern}"

            return "\n".join(results)

        except Exception as e:
            return f"Error finding files: {str(e)}"