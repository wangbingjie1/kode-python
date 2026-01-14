"""
全局上下文管理（基于 contextvars）

用于在异步环境中传递用户上下文（user_id, conversation_id 等），
避免在每个函数调用中显式传递参数。

特性：
- 异步安全（支持 asyncio）
- 线程隔离（每个协程有独立上下文）
- 透明传递（无需修改工具代码）
"""

from contextvars import ContextVar
from typing import Optional

# ============ Context Variables ============

# 当前用户ID（用于多租户隔离）
current_user_id: ContextVar[Optional[str]] = ContextVar(
    'current_user_id',
    default=None
)

# 当前对话ID（可选）
current_conversation_id: ContextVar[Optional[str]] = ContextVar(
    'current_conversation_id',
    default=None
)

# 当前项目ID（可选）
current_project_id: ContextVar[Optional[str]] = ContextVar(
    'current_project_id',
    default=None
)


# ============ Helper Functions ============

def get_current_user_id() -> str:
    """
    获取当前用户ID

    Returns:
        用户ID

    Raises:
        RuntimeError: 如果上下文未设置
    """
    user_id = current_user_id.get()
    if not user_id:
        raise RuntimeError(
            "User context not set! You must call set_user_context(user_id=...) before using this function.\n"
            "This usually means:\n"
            "1. ConversationService.execute_task_streaming() was not called, OR\n"
            "2. The calling code forgot to set user_context.\n"
            "Fix: Ensure set_user_context() is called at the entry point of your request handler."
        )
    return user_id


def get_current_conversation_id() -> Optional[str]:
    """获取当前对话ID（可选）"""
    return current_conversation_id.get()


def get_current_project_id() -> Optional[str]:
    """获取当前项目ID（可选）"""
    return current_project_id.get()


def set_user_context(
    user_id: str,
    conversation_id: Optional[str] = None,
    project_id: Optional[str] = None
):
    """
    设置用户上下文（通常在 ConversationService 中调用）

    Args:
        user_id: 用户ID（必需）
        conversation_id: 对话ID（可选）
        project_id: 项目ID（可选）
    """
    current_user_id.set(user_id)
    if conversation_id:
        current_conversation_id.set(conversation_id)
    if project_id:
        current_project_id.set(project_id)


def clear_user_context():
    """清除用户上下文"""
    current_user_id.set(None)
    current_conversation_id.set(None)
    current_project_id.set(None)
