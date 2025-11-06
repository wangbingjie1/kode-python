"""
Google OAuth2 Configuration

Google OAuth2 客户端配置和工具函数。
"""

import os
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

# 从环境变量读取配置
config = Config(environ=os.environ)

# Google OAuth2配置
GOOGLE_CLIENT_ID = config.get("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = config.get("GOOGLE_CLIENT_SECRET", default="")
GOOGLE_REDIRECT_URI = config.get("GOOGLE_REDIRECT_URI", default="http://localhost:8001/api/auth/google/callback")

# OAuth客户端实例
oauth = OAuth()

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile",
        },
    )


def get_google_oauth_url(redirect_uri: str) -> str:
    """
    生成谷歌OAuth2授权URL

    Args:
        redirect_uri: 回调地址

    Returns:
        授权URL
    """
    if not GOOGLE_CLIENT_ID:
        raise ValueError("Google OAuth未配置：缺少GOOGLE_CLIENT_ID")

    return (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=openid email profile&"
        f"access_type=offline&"
        f"prompt=consent"
    )
