"""Context manager for tracking conversation history and codebase state."""

from pathlib import Path
from typing import Any, Dict, List, Optional


class ContextManager:
    """
    Manages conversation context and codebase understanding.

    Equivalent to TypeScript's context management in src/context.ts
    """

    def __init__(self, project_root: Path, max_context_tokens: int = 100000):
        """
        Initialize context manager.

        Args:
            project_root: Project root directory
            max_context_tokens: Maximum tokens to keep in context
        """
        self.project_root = project_root
        self.max_context_tokens = max_context_tokens

        # Conversation history
        self.messages: List[Dict[str, str]] = []

        # File cache
        self.file_cache: Dict[str, str] = {}

        # Project metadata
        self.project_files: List[str] = []
        self.project_structure: Dict[str, Any] = {}

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """
        Add a message to conversation history.

        Args:
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata
        """
        message = {"role": role, "content": content}
        if metadata:
            message["metadata"] = metadata

        self.messages.append(message)

        # Trim if exceeding max context
        self._trim_context()

    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get conversation messages.

        Args:
            limit: Optional limit on number of messages

        Returns:
            List of messages
        """
        if limit:
            return self.messages[-limit:]
        return self.messages.copy()

    def clear_messages(self) -> None:
        """Clear conversation history."""
        self.messages.clear()

    def cache_file(self, file_path: str, content: str) -> None:
        """
        Cache file content.

        Args:
            file_path: Path to file
            content: File content
        """
        self.file_cache[file_path] = content

    def get_cached_file(self, file_path: str) -> Optional[str]:
        """
        Get cached file content.

        Args:
            file_path: Path to file

        Returns:
            File content if cached, None otherwise
        """
        return self.file_cache.get(file_path)

    def scan_project(self, include_patterns: Optional[List[str]] = None) -> None:
        """
        Scan project directory structure.

        Args:
            include_patterns: Optional glob patterns to include
        """
        if include_patterns is None:
            include_patterns = ["**/*.py", "**/*.md", "**/*.json", "**/*.toml"]

        files = []
        for pattern in include_patterns:
            files.extend(self.project_root.glob(pattern))

        self.project_files = [str(f.relative_to(self.project_root)) for f in files]

        # Build structure
        self.project_structure = self._build_tree(self.project_files)

    def _build_tree(self, files: List[str]) -> Dict[str, Any]:
        """Build directory tree from file list."""
        tree: Dict[str, Any] = {}
        for file_path in files:
            parts = Path(file_path).parts
            current = tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            # Add file
            current[parts[-1]] = None
        return tree

    def _trim_context(self) -> None:
        """Trim context to stay within token limits."""
        # Simple implementation: keep last N messages
        # In a real implementation, you'd count tokens and trim accordingly
        max_messages = 50
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]

    def get_project_summary(self) -> str:
        """
        Get a summary of the project structure.

        Returns:
            Formatted project summary
        """
        if not self.project_files:
            self.scan_project()

        summary = f"Project: {self.project_root.name}\n"
        summary += f"Total files: {len(self.project_files)}\n\n"
        summary += "File structure:\n"

        # Group by extension
        by_extension: Dict[str, int] = {}
        for file_path in self.project_files:
            ext = Path(file_path).suffix or "no extension"
            by_extension[ext] = by_extension.get(ext, 0) + 1

        for ext, count in sorted(by_extension.items()):
            summary += f"  {ext}: {count} files\n"

        return summary