"""Base classes for Kode tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pathlib import Path
import json

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


class InteractiveTool(KodeTool):
    """
    支持多轮交互的工具基类

    用于需要多次用户输入的工具（如业务理解五问）。
    使用文件系统持久化交互状态。

    子类需要实现：
    - _run_interactive(): 核心交互逻辑
    - _get_state_file_path(): 状态文件路径
    """

    requires_permission: bool = False
    """交互式工具默认不需要每次都询问权限"""

    state_storage_dir: str = "interaction_state"
    """交互状态存储目录"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_state_dir()

    def _ensure_state_dir(self) -> None:
        """确保状态存储目录存在"""
        Path(self.state_storage_dir).mkdir(parents=True, exist_ok=True)

    def _get_state_file_path(self, session_id: str) -> Path:
        """
        获取会话状态文件路径

        Args:
            session_id: 会话标识符（如 conversation_id 或 connection_name）

        Returns:
            状态文件路径
        """
        return Path(self.state_storage_dir) / f"{self.name}_{session_id}.json"

    def _load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        加载会话状态

        Args:
            session_id: 会话标识符

        Returns:
            状态字典，不存在时返回None
        """
        path = self._get_state_file_path(session_id)
        if not path.exists():
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """
        保存会话状态

        Args:
            session_id: 会话标识符
            state: 状态字典
        """
        path = self._get_state_file_path(session_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def _clear_state(self, session_id: str) -> None:
        """
        清除会话状态

        Args:
            session_id: 会话标识符
        """
        path = self._get_state_file_path(session_id)
        if path.exists():
            path.unlink()

    @abstractmethod
    def _run_interactive(self, session_id: str, **kwargs: Any) -> str:
        """
        执行交互式工具逻辑

        子类实现此方法来处理多轮交互。
        可以通过 _load_state/_save_state 管理状态。

        Args:
            session_id: 会话标识符
            **kwargs: 工具参数（包含用户输入）

        Returns:
            工具执行结果（可能是下一个问题或最终结果）
        """
        pass

    def _run(self, **kwargs: Any) -> str:
        """
        KodeTool 要求的同步执行入口

        自动从 kwargs 中提取 session_id：
        1. 如果有 session_id 参数，直接使用
        2. 如果有 connection_name 参数，用它作为 session_id
        3. 否则使用 "default" 作为 session_id

        Args:
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        # 自动推导 session_id
        session_id = kwargs.pop("session_id", None)
        if session_id is None:
            session_id = kwargs.get("connection_name", "default")

        return self._run_interactive(session_id, **kwargs)