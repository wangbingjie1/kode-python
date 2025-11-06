"""
语言本地化中间件

自动从请求头中提取 Accept-Language 并设置到上下文中。
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from kode.utils.i18n import set_locale, parse_accept_language


class LocaleMiddleware(BaseHTTPMiddleware):
    """语言本地化中间件"""

    async def dispatch(self, request: Request, call_next):
        # 从请求头中获取语言
        accept_language = request.headers.get('Accept-Language')

        # 解析并设置语言
        locale = parse_accept_language(accept_language)
        set_locale(locale)

        # 继续处理请求
        response = await call_next(request)
        return response
