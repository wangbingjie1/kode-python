"""Bash command execution tool."""

import subprocess
from typing import Optional, Type

from pydantic import BaseModel, Field

from .base import KodeTool


class BashInput(BaseModel):
    """Input for BashTool."""

    command: str = Field(description="The bash command to execute")
    timeout: Optional[int] = Field(
        default=120, description="Timeout in seconds (default: 120, max: 600)"
    )
    cwd: Optional[str] = Field(
        default=None, description="Working directory for command execution"
    )


class BashTool(KodeTool):
    """
    Execute bash commands in a shell.

    Equivalent to TypeScript's Bash tool in src/tools/BashTool/
    """

    name: str = "Bash"
    description: str = """Executes bash commands with optional timeout.
- Use for terminal operations like git, npm, docker, etc.
- DO NOT use for file operations - use FileRead/FileWrite/FileEdit instead
- Commands timeout after 120s by default (max 600s)
- Supports working directory specification
- Quote paths with spaces using double quotes
- Use && to chain dependent commands, ; for independent commands
- Avoid using cd; prefer absolute paths instead
- NEVER use interactive commands (like git rebase -i)"""
    args_schema: Type[BaseModel] = BashInput
    requires_permission: bool = True

    def _run(self, command: str, timeout: Optional[int] = 120, cwd: Optional[str] = None) -> str:
        """Execute bash command."""
        try:
            # Validate timeout
            if timeout and timeout > 600:
                timeout = 600

            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )

            # Format output
            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout)
            if result.stderr:
                output_parts.append(f"STDERR:\n{result.stderr}")

            if result.returncode != 0:
                output_parts.append(f"\nCommand exited with code {result.returncode}")

            return "\n".join(output_parts) if output_parts else "Command completed successfully"

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"