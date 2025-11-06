"""
Authentication API Routes

User registration, login, token refresh, and profile endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import httpx
import uuid

from kode.database.session import get_db
from kode.models import User
from kode.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserProfile,
    GoogleCallbackRequest,
)
from kode.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from kode.core.oauth import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
from kode.web.dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """用户注册"""

    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册",
        )

    # 创建新用户
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # 转换为响应格式
    return UserProfile(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        is_active=new_user.is_active,
        created_at=new_user.created_at.isoformat(),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""

    # 查找用户
    result = await db.execute(select(User).where(User.username == credentials.username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 验证密码
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 生成令牌
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
):
    """刷新访问令牌"""

    # 验证刷新令牌
    payload = verify_token(token_data.refresh_token, token_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌格式",
        )

    # 验证用户是否存在且活跃
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
        )

    # 生成新令牌
    new_access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.get("/profile", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户信息"""
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
        auth_provider=current_user.auth_provider,
        avatar_url=current_user.avatar_url,
    )


@router.get("/google/login")
async def google_login():
    """
    发起谷歌OAuth2登录

    返回谷歌授权URL，前端跳转到该URL
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="谷歌登录未配置",
        )

    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid email profile&"
        f"access_type=offline&"
        f"prompt=consent"
    )

    return {"auth_url": google_auth_url}


@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(
    callback_data: GoogleCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    谷歌OAuth2回调处理

    接收授权码，交换访问令牌，获取用户信息，创建/登录用户
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="谷歌登录未配置",
        )

    # 1. 交换授权码获取访问令牌
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": callback_data.code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="授权码验证失败",
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        # 2. 使用访问令牌获取用户信息
        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_info_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="获取用户信息失败",
            )

        user_info = user_info_response.json()

    # 3. 提取用户信息
    google_id = user_info.get("id")
    email = user_info.get("email")
    name = user_info.get("name", email.split("@")[0])
    avatar_url = user_info.get("picture")

    if not google_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户信息不完整",
        )

    # 4. 查找或创建用户
    # 先通过google_id查找
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        # 再通过email查找（可能是已有用户首次使用谷歌登录）
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            # 关联现有用户到谷歌账号
            user.google_id = google_id
            user.auth_provider = "google"
            user.avatar_url = avatar_url
        else:
            # 创建新用户
            user = User(
                id=str(uuid.uuid4()),
                username=name,
                email=email,
                hashed_password=None,  # OAuth用户无密码
                auth_provider="google",
                google_id=google_id,
                avatar_url=avatar_url,
                is_active=True,
            )
            db.add(user)

        await db.commit()
        await db.refresh(user)

    # 5. 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 6. 生成JWT令牌
    jwt_access_token = create_access_token(data={"sub": user.id})
    jwt_refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenResponse(
        access_token=jwt_access_token,
        refresh_token=jwt_refresh_token,
        token_type="bearer",
    )
