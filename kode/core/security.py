"""
Security Utilities

JWT token generation, password hashing, and authentication utilities.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.hash import bcrypt
import os

# JWT配置 - SECRET_KEY must be set via environment variable
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY environment variable must be set. "
        "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码（使用bcrypt）

    Args:
        plain_password: 明文密码
        hashed_password: bcrypt哈希密码

    Returns:
        密码是否匹配
    """
    # Handle legacy SHA256 passwords for backward compatibility
    if len(hashed_password) == 64 and all(c in '0123456789abcdef' for c in hashed_password):
        # This looks like a SHA256 hash (legacy), reject it for security
        # Force users to reset password
        return False

    try:
        return bcrypt.verify(plain_password, hashed_password)
    except Exception:
        return False


def hash_password(password: str) -> str:
    """
    加密密码（使用bcrypt）

    Args:
        password: 明文密码

    Returns:
        bcrypt哈希密码
    """
    return bcrypt.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """
    验证令牌并返回payload

    Args:
        token: JWT令牌
        token_type: 令牌类型 ('access' 或 'refresh')

    Returns:
        payload字典，验证失败返回None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None
