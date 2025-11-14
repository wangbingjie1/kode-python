"""
Interactive tools for user engagement.

This module provides tools for asking the user questions and gathering input
during agent execution.
"""

import asyncio
from typing import Type, List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

from .base import KodeTool
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


class AskUserInput(BaseModel):
    """Input schema for AskUserTool."""

    question: str = Field(
        description="问题内容，用自然语言清晰描述需要用户回答的问题"
    )
    question_type: Literal["text", "select", "multiselect", "confirm"] = Field(
        default="text",
        description=(
            "问题类型：\n"
            "- text: 文本输入框（用户自由输入）\n"
            "- select: 单选（从选项中选一个）\n"
            "- multiselect: 多选（从选项中选多个）\n"
            "- confirm: 确认框（是/否）"
        )
    )
    options: Optional[List[str]] = Field(
        default=None,
        description="选项列表（仅当 question_type 为 select 或 multiselect 时需要）"
    )
    default_value: Optional[str] = Field(
        default=None,
        description="默认值（可选）"
    )
    required: bool = Field(
        default=True,
        description="是否必填"
    )
    context: Optional[str] = Field(
        default=None,
        description="上下文说明（帮助用户更好理解问题）"
    )


class AskUserTool(KodeTool):
    """
    交互式提问工具。

    此工具允许 AI Agent 在执行过程中暂停并向用户提问，等待用户回答后继续执行。

    **使用场景**：
    1. 不确定性消歧 - 当 AI 发现多种可能的解释或方案时
    2. 确认关键操作 - 在执行重要操作前获得用户确认
    3. 收集额外信息 - 当现有信息不足以完成任务时
    4. 业务逻辑分支 - 需要用户决策来选择执行路径

    **示例**：
    ```python
    # 文本输入
    result = await ask_user_tool.ainvoke({
        "question": "请输入数据库连接的主机地址",
        "question_type": "text",
        "default_value": "localhost"
    })

    # 单选
    result = await ask_user_tool.ainvoke({
        "question": "请选择要分析的数据表",
        "question_type": "select",
        "options": ["users", "orders", "products"]
    })

    # 确认框
    result = await ask_user_tool.ainvoke({
        "question": "确认要删除此数据库连接吗？",
        "question_type": "confirm",
        "context": "此操作不可撤销"
    })
    ```
    """

    name: str = "AskUser"
    description: str = (
        "向用户提出问题并等待回答。支持文本输入、单选、多选、确认等多种问题类型。"
        "当你需要用户的输入或确认时使用此工具。"
    )
    args_schema: Type[BaseModel] = AskUserInput
    requires_permission: bool = False  # 不需要额外权限，因为本身就是用户交互

    # Internal: asyncio.Event for synchronization
    _user_response_event: Optional[asyncio.Event] = None
    _user_response_data: Optional[Dict[str, Any]] = None

    def __init__(self, **kwargs):
        """Initialize AskUserTool."""
        super().__init__(**kwargs)
        self._user_response_event = None
        self._user_response_data = None

    def _prepare_question_payload(self, **kwargs) -> Dict[str, Any]:
        """
        Prepare question payload for frontend rendering.

        Returns:
            Dict with question data in standardized format
        """
        payload = {
            "question": kwargs.get("question"),
            "question_type": kwargs.get("question_type", "text"),
            "options": kwargs.get("options"),
            "default_value": kwargs.get("default_value"),
            "required": kwargs.get("required", True),
            "context": kwargs.get("context"),
        }

        # Validate options for select/multiselect
        if payload["question_type"] in ["select", "multiselect"]:
            if not payload["options"] or len(payload["options"]) == 0:
                raise ValueError(f"question_type '{payload['question_type']}' requires 'options' list")

        return payload

    def _run(self, **kwargs) -> str:
        """Synchronous run (not supported, use async version)."""
        raise NotImplementedError("AskUserTool only supports async execution via ainvoke()")

    async def ainvoke(self, input_data: Dict[str, Any], **kwargs) -> str:
        """
        Async invoke - ask user and wait for response.

        This method will:
        1. Raise a special exception (UserInputRequired) with question payload
        2. The exception is caught by anthropic_streaming.py
        3. SSE sends 'user_input_required' event to frontend
        4. Wait for user response via asyncio.Event
        5. Return user's answer

        Args:
            input_data: Question parameters

        Returns:
            User's response as string

        Raises:
            UserInputRequired: Special exception to signal streaming handler
        """
        # Prepare question payload
        payload = self._prepare_question_payload(**input_data)

        logger.info(f"[AskUserTool] Requesting user input: {payload['question']}")

        # Create event for waiting
        self._user_response_event = asyncio.Event()
        self._user_response_data = None

        # Raise special exception to be caught by streaming handler
        # The streaming handler will:
        # 1. Catch this exception
        # 2. Yield SSE event 'user_input_required' with payload
        # 3. Store reference to this tool instance
        # 4. Wait for user response
        from kode.exceptions import UserInputRequired
        raise UserInputRequired(
            question=payload["question"],
            question_type=payload["question_type"],
            options=payload.get("options"),
            default_value=payload.get("default_value"),
            required=payload.get("required", True),
            context=payload.get("context"),
            tool_instance=self  # Pass self for response injection
        )

    async def _set_user_response(self, response: Dict[str, Any]):
        """
        Internal method to inject user response.

        Called by streaming handler after user responds.

        Args:
            response: User response data
        """
        self._user_response_data = response
        if self._user_response_event:
            self._user_response_event.set()
        logger.info(f"[AskUserTool] User response received: {response}")

    async def _wait_for_response(self) -> str:
        """
        Wait for user response.

        Returns:
            User's answer as string
        """
        if not self._user_response_event:
            raise RuntimeError("No event set up for waiting user response")

        # Wait for user response (with timeout)
        try:
            await asyncio.wait_for(self._user_response_event.wait(), timeout=300.0)  # 5 min timeout
        except asyncio.TimeoutError:
            logger.error("[AskUserTool] User response timeout (5 minutes)")
            return "[用户未在规定时间内回答]"

        # Extract answer
        if not self._user_response_data:
            return "[无响应数据]"

        answer = self._user_response_data.get("answer")
        if answer is None:
            return "[空响应]"

        # Format answer based on type
        if isinstance(answer, list):
            return ", ".join(str(x) for x in answer)
        else:
            return str(answer)