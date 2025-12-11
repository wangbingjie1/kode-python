"""
Security Utilities

JWT token generation, password hashing, and authentication utilities.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import hashlib
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# JWT配置
SECRET_KEY = os.getenv("SECRET_KEY", "kode-secret-key-change-in-production")
ALGORITHM = "HS256"
# 延长 access token 有效期，避免频繁过期（尤其是心跳连接）
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 默认 8 小时
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 数据库密码加密配置
DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY", SECRET_KEY)


def _get_fernet_key() -> bytes:
    """
    从SECRET_KEY派生Fernet密钥（32字节）
    使用PBKDF2确保密钥强度
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"kode-db-encryption-salt",  # 固定盐值，生产环境应从环境变量读取
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(DB_ENCRYPTION_KEY.encode()))
    return key


def encrypt_db_password(plain_password: str) -> str:
    """
    加密数据库密码（使用Fernet对称加密）

    Args:
        plain_password: 明文密码

    Returns:
        加密后的密码（Base64编码字符串）
    """
    if not plain_password:
        return ""

    fernet = Fernet(_get_fernet_key())
    encrypted_bytes = fernet.encrypt(plain_password.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')


def decrypt_db_password(encrypted_password: str) -> str:
    """
    解密数据库密码

    Args:
        encrypted_password: 加密后的密码

    Returns:
        明文密码

    Raises:
        Exception: 解密失败（密钥错误或数据损坏）
    """
    if not encrypted_password:
        return ""

    try:
        fernet = Fernet(_get_fernet_key())
        decrypted_bytes = fernet.decrypt(encrypted_password.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"密码解密失败: {str(e)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码（使用SHA256）"""
    return hash_password(plain_password) == hashed_password


def hash_password(password: str) -> str:
    """加密密码（使用SHA256 + salt）"""
    # 使用SECRET_KEY作为盐值
    salted_password = f"{password}{SECRET_KEY}"
    return hashlib.sha256(salted_password.encode('utf-8')).hexdigest()


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
