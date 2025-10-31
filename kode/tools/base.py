"""Base classes for Kode tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

try:
    from langchain.tools import BaseTool
except ImportError:
    from langchain_core.tools import BaseTool

from pydantic import BaseModel


class KodeTool(BaseTool, ABC):
    """
    Base class for all Kode tools.

    Extends LangChain's BaseTool with Kode-specific functionality.
    """

    requires_permission: bool = True
    """Whether this tool requires user permission."""

    permission_level: str = "ask_each_time"
    """Default permission level for this tool."""

    @abstractmethod
    def _run(self, *args: Any, **kwargs: Any) -> str:
        """
        Execute the tool synchronously.

        Returns:
            Tool execution result as string
        """
        pass

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """
        Execute the tool asynchronously.

        Default implementation calls synchronous version.
        Override for true async support.
        """
        return self._run(*args, **kwargs)

    def get_permission_details(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Get details about the tool action for permission prompt.

        Args:
            **kwargs: Tool arguments

        Returns:
            Dictionary with permission details
        """
        return {
            "tool_name": self.name,
            "description": self.description,
            "arguments": kwargs,
        }