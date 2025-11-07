"""
FastAPI Dependencies

Authentication and common dependencies for API routes.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from kode.database.session import get_db
from kode.models import User
from kode.core.security import verify_token

# HTTP Bearer Token认证
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    从JWT令牌获取当前用户

    依赖注入，用于需要认证的路由
    """
    token = credentials.credentials

    # 验证令牌
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌格式",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 从数据库获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    可选的用户认证（不强制要求登录）

    用于可以匿名访问但登录后提供更多功能的路由
    """
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    要求管理员权限

    依赖注入，用于需要管理员权限的路由
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限才能执行此操作",
        )
    return current_user
