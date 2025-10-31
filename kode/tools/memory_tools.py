"""Memory tools for persistent storage across sessions."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field

from .base import KodeTool


class MemoryReadInput(BaseModel):
    """Input for MemoryReadTool."""

    key: Optional[str] = Field(default=None, description="Memory key to read (optional)")


class MemoryReadTool(KodeTool):
    """
    Read from persistent memory storage.

    Equivalent to TypeScript's MemoryReadTool
    """

    name: str = "MemoryRead"
    description: str = """Read from persistent memory storage.
- Can read all memories or a specific key
- Memories persist across sessions
- Stored in .kode/memory.json
- Useful for remembering context, preferences, or facts"""
    args_schema: Type[BaseModel] = MemoryReadInput
    requires_permission: bool = False

    def _get_memory_path(self) -> Path:
        """Get the memory file path."""
        return Path.cwd() / ".kode" / "memory.json"

    def _run(self, key: Optional[str] = None) -> str:
        """Read from memory."""
        try:
            memory_path = self._get_memory_path()
            if not memory_path.exists():
                return "No memories stored yet"

            with open(memory_path, "r", encoding="utf-8") as f:
                memories = json.load(f)

            if key:
                # Read specific key
                if key in memories:
                    value = memories[key]
                    return f"{key}: {json.dumps(value, indent=2)}"
                else:
                    return f"No memory found for key: {key}"
            else:
                # Read all memories
                if not memories:
                    return "No memories stored"
                return json.dumps(memories, indent=2)

        except Exception as e:
            return f"Error reading memory: {str(e)}"


class MemoryWriteInput(BaseModel):
    """Input for MemoryWriteTool."""

    key: str = Field(description="Memory key")
    value: str = Field(description="Memory value (can be JSON string)")


class MemoryWriteTool(KodeTool):
    """
    Write to persistent memory storage.

    Equivalent to TypeScript's MemoryWriteTool
    """

    name: str = "MemoryWrite"
    description: str = """Write to persistent memory storage.
- Store information that persists across sessions
- Can store strings, numbers, objects (as JSON)
- Useful for remembering user preferences, project context, facts
- Stored in .kode/memory.json"""
    args_schema: Type[BaseModel] = MemoryWriteInput
    requires_permission: bool = True

    def _get_memory_path(self) -> Path:
        """Get the memory file path."""
        return Path.cwd() / ".kode" / "memory.json"

    def _run(self, key: str, value: str) -> str:
        """Write to memory."""
        try:
            memory_path = self._get_memory_path()

            # Ensure directory exists
            memory_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing memories
            memories = {}
            if memory_path.exists():
                with open(memory_path, "r", encoding="utf-8") as f:
                    memories = json.load(f)

            # Try to parse value as JSON, otherwise store as string
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                parsed_value = value

            # Update memory
            memories[key] = parsed_value

            # Save memories
            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=2)

            return f"Memory saved: {key} = {json.dumps(parsed_value)}"

        except Exception as e:
            return f"Error writing memory: {str(e)}"
