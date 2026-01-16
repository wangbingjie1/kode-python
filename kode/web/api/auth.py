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
from kode.models import User, Plan, Project
from kode.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserProfile,
    GoogleCallbackRequest,
    EmailSendCodeRequest,
    EmailSendCodeResponse,
    EmailVerifyRequest,
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
import os

# 前端 URL（OAuth 回调重定向用）
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
from kode.utils.i18n import t
from kode.services.billing_service import BillingService
from kode.services.email_service import EmailService

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
            detail=t('auth.username_exists'),
        )

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t('auth.email_exists'),
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

    # 自动分配 Free 套餐
    try:
        free_plan_result = await db.execute(select(Plan).where(Plan.name == "free"))
        free_plan = free_plan_result.scalar_one_or_none()

        if free_plan:
            await BillingService.create_subscription(
                db=db,
                user_id=new_user.id,
                plan_id=free_plan.id,
                auto_renew=False
            )
    except Exception as e:
        # 订阅创建失败不影响注册，记录日志即可
        import logging
        logging.error(f"Failed to create free subscription for user {new_user.id}: {str(e)}")

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
            detail=t('auth.invalid_credentials'),
        )

    # 验证密码
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t('auth.invalid_credentials'),
        )

    # 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=t('auth.user_disabled'),
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
            detail=t('auth.invalid_refresh_token'),
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t('auth.invalid_token_format'),
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


@router.get("/google/callback")
async def google_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    谷歌OAuth2回调处理（GET请求）

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
                "code": code,
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

    # 4. 查找或创建用户（使用事务确保原子性）
    is_new_user = False
    try:
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
                user.updated_at = datetime.utcnow()
            else:
                # 创建新用户 - 确保 username 唯一
                # 如果 username 重复，添加后缀
                base_username = name
                username = base_username
                counter = 1

                while True:
                    result = await db.execute(select(User).where(User.username == username))
                    if not result.scalar_one_or_none():
                        break
                    username = f"{base_username}_{counter}"
                    counter += 1

                user = User(
                    id=str(uuid.uuid4()),
                    username=username,
                    email=email,
                    hashed_password=None,  # OAuth用户无密码
                    auth_provider="google",
                    google_id=google_id,
                    avatar_url=avatar_url,
                    is_active=True,
                )
                db.add(user)
                is_new_user = True

            await db.commit()
            await db.refresh(user)

            # 为新创建的用户自动分配 Free 套餐
            if is_new_user:
                try:
                    # 检查用户是否已有订阅（双重保险）
                    existing_sub = await BillingService.get_user_active_subscription(db, user.id)
                    if not existing_sub:
                        free_plan_result = await db.execute(select(Plan).where(Plan.name == "free"))
                        free_plan = free_plan_result.scalar_one_or_none()

                        if free_plan:
                            await BillingService.create_subscription(
                                db=db,
                                user_id=user.id,
                                plan_id=free_plan.id,
                                auto_renew=False
                            )
                except Exception as e:
                    import logging
                    logging.error(f"Failed to create free subscription for OAuth user {user.id}: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建用户失败: {str(e)}",
        )

    # 5. 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 6. 生成JWT令牌
    jwt_access_token = create_access_token(data={"sub": user.id})
    jwt_refresh_token = create_refresh_token(data={"sub": user.id})

    # 重定向到前端，并通过URL传递token
    redirect_url = f"{FRONTEND_URL}/?google_success=true&access_token={jwt_access_token}&refresh_token={jwt_refresh_token}"
    return RedirectResponse(url=redirect_url)


@router.post("/email/send-code", response_model=EmailSendCodeResponse)
async def send_email_verification_code(
    request: EmailSendCodeRequest,
):
    """
    发送邮箱验证码

    向指定邮箱发送6位数字验证码，有效期10分钟。
    同一邮箱60秒内只能发送一次。
    """
    success, message = await EmailService.send_verification_code(request.email)
    return EmailSendCodeResponse(success=success, message=message)


@router.post("/email/verify", response_model=TokenResponse)
async def verify_email_code(
    request: EmailVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    验证邮箱验证码并登录/注册

    验证成功后：
    - 如果邮箱已存在，直接登录
    - 如果邮箱不存在，自动创建新用户并登录
    """
    # 1. 验证验证码
    success, message = EmailService.verify_code(request.email, request.code)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    # 2. 查找或创建用户
    email = request.email.lower().strip()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    is_new_user = False
    if not user:
        # 新用户：自动创建账号
        # 使用邮箱前缀作为用户名，确保唯一性
        base_username = email.split("@")[0]
        username = base_username
        counter = 1

        while True:
            result = await db.execute(select(User).where(User.username == username))
            if not result.scalar_one_or_none():
                break
            username = f"{base_username}_{counter}"
            counter += 1

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=None,  # 验证码登录无密码
            auth_provider="email",
            is_active=True,
        )
        db.add(user)
        is_new_user = True

        await db.commit()
        await db.refresh(user)

        # 为新用户分配 Free 套餐
        try:
            free_plan_result = await db.execute(select(Plan).where(Plan.name == "free"))
            free_plan = free_plan_result.scalar_one_or_none()

            if free_plan:
                await BillingService.create_subscription(
                    db=db,
                    user_id=user.id,
                    plan_id=free_plan.id,
                    auto_renew=False
                )
        except Exception as e:
            import logging
            logging.error(f"Failed to create free subscription for email user {user.id}: {str(e)}")

    # 3. 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 4. 生成JWT令牌
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )
