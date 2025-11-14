"""Code search tool using grep/ripgrep patterns."""

import re
import subprocess
from pathlib import Path
from typing import Optional, Type

from pydantic import BaseModel, Field

from .base import KodeTool


class GrepInput(BaseModel):
    """Input for GrepTool."""

    pattern: str = Field(description="Regular expression pattern to search for")
    path: Optional[str] = Field(
        default=None, description="File or directory to search (default: current directory)"
    )
    glob: Optional[str] = Field(default=None, description="Glob pattern to filter files (e.g. *.py)")
    case_insensitive: bool = Field(default=False, description="Case insensitive search")
    output_mode: str = Field(
        default="files_with_matches",
        description="Output mode: content, files_with_matches, or count",
    )
    context_lines: Optional[int] = Field(
        default=None, description="Number of context lines to show (requires content mode)"
    )
    show_line_numbers: bool = Field(
        default=True, description="Show line numbers (content mode only)"
    )
    multiline: bool = Field(
        default=False, description="Enable multiline matching where . matches newlines"
    )


class GrepTool(KodeTool):
    """
    Search for patterns in code using regex.

    Equivalent to TypeScript's Grep tool in src/tools/GrepTool/
    """

    name: str = "Grep"
    description: str = """Search code with regex patterns. Supports glob filtering and multiline matching."""
    args_schema: Type[BaseModel] = GrepInput
    requires_permission: bool = False

    def _run(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        case_insensitive: bool = False,
        output_mode: str = "files_with_matches",
        context_lines: Optional[int] = None,
        show_line_numbers: bool = True,
        multiline: bool = False,
    ) -> str:
        """Search for pattern in files."""
        try:
            # Try to use ripgrep if available, fall back to grep
            return self._search_with_ripgrep(
                pattern,
                path or ".",
                glob,
                case_insensitive,
                output_mode,
                context_lines,
                show_line_numbers,
                multiline,
            )
        except FileNotFoundError:
            # Ripgrep not available, use Python implementation
            return self._search_with_python(
                pattern, path or ".", glob, case_insensitive, output_mode
            )
        except Exception as e:
            return f"Error searching: {str(e)}"

    def _search_with_ripgrep(
        self,
        pattern: str,
        path: str,
        glob: Optional[str],
        case_insensitive: bool,
        output_mode: str,
        context_lines: Optional[int],
        show_line_numbers: bool,
        multiline: bool,
    ) -> str:
        """Search using ripgrep command."""
        cmd = ["rg"]

        # Add flags based on options
        if case_insensitive:
            cmd.append("-i")

        if multiline:
            cmd.extend(["-U", "--multiline-dotall"])

        if output_mode == "files_with_matches":
            cmd.append("-l")
        elif output_mode == "count":
            cmd.append("-c")
        else:  # content
            if show_line_numbers:
                cmd.append("-n")
            if context_lines:
                cmd.extend(["-C", str(context_lines)])

        if glob:
            cmd.extend(["--glob", glob])

        cmd.extend([pattern, path])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return result.stdout or "No matches found"
        elif result.returncode == 1:
            return "No matches found"
        else:
            return f"Error: {result.stderr}"

    def _search_with_python(
        self,
        pattern: str,
        path: str,
        glob: Optional[str],
        case_insensitive: bool,
        output_mode: str,
    ) -> str:
        """Fallback Python implementation of grep."""
        flags = re.IGNORECASE if case_insensitive else 0
        regex = re.compile(pattern, flags)

        path_obj = Path(path)
        if path_obj.is_file():
            files = [path_obj]
        else:
            # Get matching files
            if glob:
                files = list(path_obj.rglob(glob))
            else:
                files = [f for f in path_obj.rglob("*") if f.is_file()]

        results = []
        for file in files:
            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if output_mode == "files_with_matches":
                    if regex.search(content):
                        results.append(str(file))
                elif output_mode == "count":
                    count = len(regex.findall(content))
                    if count > 0:
                        results.append(f"{file}:{count}")
                else:  # content
                    for i, line in enumerate(content.splitlines(), 1):
                        if regex.search(line):
                            results.append(f"{file}:{i}:{line}")
            except Exception:
                continue

        return "\n".join(results) if results else "No matches found"