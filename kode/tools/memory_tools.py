"""Persistent memory tools for conversation context."""

import json
from pathlib import Path
from typing import Optional, Type

from pydantic import BaseModel, Field

from .base import KodeTool


class MemoryReadInput(BaseModel):
    """Input for MemoryReadTool."""

    key: Optional[str] = Field(
        default=None, description="Memory key to read (omit to read all memories)"
    )


class MemoryWriteInput(BaseModel):
    """Input for MemoryWriteTool."""

    key: str = Field(description="Memory key")
    value: str = Field(description="Memory value to store")


class MemoryReadTool(KodeTool):
    """
    Read from persistent memory storage.

    Equivalent to TypeScript's MemoryReadTool
    """

    name: str = "MemoryRead"
    description: str = """Read from persistent memory storage.
- Can read all memories or specific key
- Useful for retrieving context across sessions"""
    args_schema: Type[BaseModel] = MemoryReadInput
    requires_permission: bool = False

    def _get_memory_path(self) -> Path:
        """Get the memory file path."""
        return Path.cwd() / ".kode" / "memory.json"

    def _run(self, key: Optional[str] = None) -> str:
        """Read memory."""
        try:
            memory_path = self._get_memory_path()

            if not memory_path.exists():
                return "No memories found"

            with open(memory_path, "r", encoding="utf-8") as f:
                memories = json.load(f)

            if key:
                if key in memories:
                    return memories[key]
                else:
                    return f"No memory found for key: {key}"
            else:
                return json.dumps(memories, indent=2)

        except Exception as e:
            return f"Error reading memory: {str(e)}"


class MemoryWriteTool(KodeTool):
    """
    Write to persistent memory storage.

    Equivalent to TypeScript's MemoryWriteTool
    """

    name: str = "MemoryWrite"
    description: str = """Write to persistent memory storage.
- Store information that should persist across sessions
- Useful for remembering user preferences, important facts, etc."""
    args_schema: Type[BaseModel] = MemoryWriteInput
    requires_permission: bool = False

    def _get_memory_path(self) -> Path:
        """Get the memory file path."""
        return Path.cwd() / ".kode" / "memory.json"

    def _run(self, key: str, value: str) -> str:
        """Write memory."""
        try:
            memory_path = self._get_memory_path()

            # Load existing memories
            if memory_path.exists():
                with open(memory_path, "r", encoding="utf-8") as f:
                    memories = json.load(f)
            else:
                memories = {}

            # Update memory
            memories[key] = value

            # Save memories
            memory_path.parent.mkdir(parents=True, exist_ok=True)
            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=2)

            return f"Memory saved: {key}"

        except Exception as e:
            return f"Error writing memory: {str(e)}"
