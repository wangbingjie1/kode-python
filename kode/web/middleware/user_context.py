"""
用户上下文中间件

自动为所有需要认证的请求设置 user_id 上下文到 contextvars
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable, Optional, Dict, Any
import re

from kode.utils.context import set_user_context, clear_user_context
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    验证 JWT token 并返回 payload

    这是一个简化版本，直接从 kode.core.security 复制关键逻辑
    """
    try:
        from kode.core.security import verify_token as _verify_token
        return _verify_token(token, token_type)
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return None


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    用户上下文中间件

    作用：
    1. 自动从 JWT token 提取 user_id
    2. 设置到 contextvars（供工具使用）
    3. 请求结束后清理上下文

    优点：
    - 无需在每个端点手动设置 user_id
    - 工具内部可以直接调用 get_current_user_id()
    - 统一的上下文管理

    执行顺序：
    Request → UserContextMiddleware → QuotaCheckMiddleware → Endpoint
    """

    # 不需要认证的路径（跳过上下文设置）
    SKIP_PATHS = [
        "/health",
        "/api/auth/",  # 认证端点自己不需要上下文
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        中间件主逻辑

        Args:
            request: HTTP 请求
            call_next: 下一个中间件/端点

        Returns:
            HTTP 响应
        """
        # 检查是否需要跳过
        if self._should_skip(request.url.path):
            return await call_next(request)

        # 尝试提取 user_id
        user_id = await self._extract_user_id(request)

        if user_id:
            # 提取 conversation_id（如果URL中有）
            conversation_id = self._extract_conversation_id(request.url.path)

            # 设置用户上下文
            set_user_context(
                user_id=user_id,
                conversation_id=conversation_id,
                project_id=None,
            )

            logger.debug(
                f"[UserContextMiddleware] Set context: user_id={user_id}, "
                f"conversation_id={conversation_id}, path={request.url.path}"
            )

        try:
            # 执行请求
            response = await call_next(request)
            return response
        finally:
            # 清理上下文（避免内存泄漏）
            if user_id:
                clear_user_context()
                logger.debug(f"[UserContextMiddleware] Cleared context for user_id={user_id}")

    def _should_skip(self, path: str) -> bool:
        """检查是否应该跳过此路径"""
        return any(path.startswith(skip_path) for skip_path in self.SKIP_PATHS)

    async def _extract_user_id(self, request: Request) -> str | None:
        """
        从请求中提取 user_id

        支持两种方式：
        1. Authorization Header (Bearer token)
        2. Query Parameter ?token=... (用于 SSE)

        Returns:
            user_id (str) 或 None
        """
        # 方式 1：从 Authorization Header 获取
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # 移除 "Bearer " 前缀
            return self._decode_user_id_from_token(token)

        # 方式 2：从 Query Parameter 获取（SSE 专用）
        token = request.query_params.get("token")
        if token:
            return self._decode_user_id_from_token(token)

        # 没有找到 token
        return None

    def _decode_user_id_from_token(self, token: str) -> str | None:
        """
        从 JWT token 解码 user_id

        Args:
            token: JWT access token

        Returns:
            user_id (str) 或 None
        """
        try:
            payload = verify_token(token, token_type="access")
            if payload:
                user_id = payload.get("sub")
                return user_id
        except Exception as e:
            logger.warning(f"[UserContextMiddleware] Failed to decode token: {e}")
            return None

    def _extract_conversation_id(self, path: str) -> str | None:
        """
        从 URL 路径中提取 conversation_id

        示例：
        - /api/sse/chat/abc123/stream → "abc123"
        - /api/chat/abc123/user-response → "abc123"

        Args:
            path: URL 路径

        Returns:
            conversation_id (str) 或 None
        """
        # 正则匹配：/chat/{conversation_id}/...
        match = re.search(r"/chat/([^/]+)/", path)
        if match:
            return match.group(1)

        # 正则匹配：/sse/chat/{conversation_id}/...
        match = re.search(r"/sse/chat/([^/]+)/", path)
        if match:
            return match.group(1)

        return None
