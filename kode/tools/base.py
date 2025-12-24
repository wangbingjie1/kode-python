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
    支持用户上下文注入（用于多租户隔离）。
    """

    requires_permission: bool = True
    """Whether this tool requires user permission."""

    permission_level: str = "ask_each_time"
    """Default permission level for this tool."""

    _execution_context: Optional[Dict[str, Any]] = None
    """执行上下文，包含 user_id, conversation_id 等信息"""

    async def send_progress(
        self,
        content: str,
        stage: Optional[str] = None,
        current: Optional[int] = None,
        total: Optional[int] = None,
        **extra_metadata: Any
    ) -> None:
        """
        发送进度消息到前端（通过 SSE）

        用于长时间运行的工具（如本体构建），实时向用户展示进度。

        Args:
            content: 进度描述文本（如 "🚀 开始构建 user_management（11 个表）"）
            stage: 阶段标识（如 "ontology_build"）
            current: 当前进度（如第 1 个）
            total: 总数（如共 6 个）
            **extra_metadata: 额外的元数据

        Example:
            await self.send_progress(
                content="🚀 开始构建 user_management（11 个表）",
                stage="ontology_build",
                domain="user_management",
                current=1,
                total=6
            )
        """
        if not self._execution_context:
            return  # 没有执行上下文时静默跳过（向后兼容）

        message_queue = self._execution_context.get("message_queue")
        if not message_queue:
            return  # 没有消息队列时静默跳过

        # 构建进度消息
        metadata = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
        if stage:
            metadata["stage"] = stage
        if current is not None:
            metadata["current"] = current
        if total is not None:
            metadata["total"] = total
            if current is not None:
                metadata["percent"] = round(current / total * 100, 1)
        metadata.update(extra_metadata)

        progress_message = {
            "type": "progress",
            "content": content,
            "metadata": metadata
        }

        # 异步放入队列
        await message_queue.put(progress_message)

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

    def set_execution_context(self, context: Dict[str, Any]) -> None:
        """
        设置执行上下文（在 ConversationService 中调用）

        Args:
            context: 执行上下文字典，包含：
                - user_id: 当前用户ID（必需）
                - conversation_id: 当前对话ID（可选）
                - project_id: 当前项目ID（可选）
        """
        self._execution_context = context

    def get_current_user_id(self) -> str:
        """
        获取当前用户ID

        Returns:
            用户ID

        Raises:
            RuntimeError: 如果执行上下文未设置
        """
        if not self._execution_context:
            raise RuntimeError("执行上下文未设置，请确保在 ConversationService 中调用了 set_execution_context")

        user_id = self._execution_context.get("user_id")
        if not user_id:
            raise RuntimeError("执行上下文中缺少 user_id")

        return user_id

    def get_current_conversation_id(self) -> Optional[str]:
        """
        获取当前对话ID（可选）

        Returns:
            对话ID，如果未设置则返回 None
        """
        if not self._execution_context:
            return None
        return self._execution_context.get("conversation_id")

    def get_current_project_id(self) -> Optional[str]:
        """
        获取当前项目ID（可选）

        Returns:
            项目ID，如果未设置则返回 None
        """
        if not self._execution_context:
            return None
        return self._execution_context.get("project_id")

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