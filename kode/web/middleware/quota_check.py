"""
Quota Check Middleware

配额检查中间件，用于在请求前验证用户配额。
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable
import logging

from kode.database.session import async_session_maker
from kode.services.billing_service import BillingService

logger = logging.getLogger(__name__)


class QuotaCheckMiddleware:
    """配额检查中间件"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """处理请求"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)

        # 只对特定端点进行配额检查
        protected_paths = [
            "/api/sse/chat",
            "/api/chat/conversations",
        ]

        should_check = any(
            request.url.path.startswith(path) for path in protected_paths
        )

        if should_check and request.method in ["GET", "POST"]:
            # 从请求中获取用户信息
            user = request.state.user if hasattr(request.state, "user") else None

            if user:
                # 检查配额
                async with async_session_maker() as db:
                    has_quota = await BillingService.check_quota(db, user.id)

                    if not has_quota:
                        response = JSONResponse(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            content={
                                "detail": "配额已用尽，请升级套餐或等待下个计费周期",
                                "error_code": "QUOTA_EXCEEDED",
                            },
                        )
                        await response(scope, receive, send)
                        return

        await self.app(scope, receive, send)


async def check_user_quota(user_id: str, db: AsyncSession) -> bool:
    """
    检查用户配额。

    Args:
        user_id: 用户 ID
        db: 数据库会话

    Returns:
        True 如果有配额，False 如果已超额

    Raises:
        HTTPException: 如果配额不足
    """
    has_quota = await BillingService.check_quota(db, user_id)

    if not has_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="配额已用尽，请升级套餐或等待下个计费周期",
            headers={"X-Error-Code": "QUOTA_EXCEEDED"},
        )

    return True
