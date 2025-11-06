"""
国际化 (i18n) 工具模块

提供轻量级的国际化支持，无需外部依赖。
支持通过 Accept-Language 请求头自动检测语言。
"""

import json
from pathlib import Path
from typing import Dict, Optional
from contextvars import ContextVar

# 当前请求的语言上下文
current_locale: ContextVar[str] = ContextVar('current_locale', default='zh-CN')

# 语言包缓存
_translations: Dict[str, Dict[str, any]] = {}
_loaded = False


def load_translations():
    """加载所有语言包"""
    global _translations, _loaded

    if _loaded:
        return

    locales_dir = Path(__file__).parent.parent / 'locales'
    if not locales_dir.exists():
        return

    for locale_file in locales_dir.glob('*.json'):
        locale_code = locale_file.stem  # zh_CN, en_US
        try:
            with open(locale_file, 'r', encoding='utf-8') as f:
                _translations[locale_code] = json.load(f)
        except Exception as e:
            print(f"Failed to load locale {locale_code}: {e}")

    _loaded = True


def set_locale(locale: str):
    """设置当前请求的语言"""
    # 标准化语言代码：zh-CN -> zh_CN
    normalized = locale.replace('-', '_')
    current_locale.set(normalized)


def get_locale() -> str:
    """获取当前语言"""
    return current_locale.get()


def t(key: str, locale: Optional[str] = None, **kwargs) -> str:
    """
    翻译函数

    Args:
        key: 翻译键，支持嵌套路径如 'auth.login.success'
        locale: 指定语言，如果为 None 则使用当前上下文语言
        **kwargs: 用于字符串格式化的参数

    Returns:
        翻译后的字符串，如果找不到则返回 key

    Example:
        >>> t('auth.login.success')
        '登录成功'
        >>> t('auth.welcome', username='张三')
        '欢迎，张三！'
    """
    load_translations()

    if locale is None:
        locale = get_locale()

    # 尝试获取翻译
    translation = _get_nested_value(_translations.get(locale, {}), key)

    # 如果当前语言没有翻译，回退到中文
    if translation is None and locale != 'zh_CN':
        translation = _get_nested_value(_translations.get('zh_CN', {}), key)

    # 如果还是没有，返回 key
    if translation is None:
        return key

    # 格式化字符串
    try:
        return translation.format(**kwargs) if kwargs else translation
    except (KeyError, ValueError):
        return translation


def _get_nested_value(data: dict, key: str) -> Optional[str]:
    """
    从嵌套字典中获取值

    Args:
        data: 字典数据
        key: 点分隔的键路径，如 'auth.login.success'

    Returns:
        找到的值，如果不存在则返回 None
    """
    keys = key.split('.')
    value = data

    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return None

    return value if isinstance(value, str) else None


def parse_accept_language(accept_language: Optional[str]) -> str:
    """
    解析 Accept-Language 请求头

    Args:
        accept_language: Accept-Language 请求头值
                        例如: "zh-CN,zh;q=0.9,en;q=0.8"

    Returns:
        解析后的语言代码，默认返回 'zh_CN'
    """
    if not accept_language:
        return 'zh_CN'

    # 解析语言列表和权重
    languages = []
    for item in accept_language.split(','):
        parts = item.strip().split(';')
        lang = parts[0].strip()

        # 提取权重
        q = 1.0
        if len(parts) > 1:
            try:
                q_param = parts[1].strip()
                if q_param.startswith('q='):
                    q = float(q_param[2:])
            except ValueError:
                pass

        languages.append((lang, q))

    # 按权重排序
    languages.sort(key=lambda x: x[1], reverse=True)

    # 查找支持的语言
    for lang, _ in languages:
        # 标准化：zh-CN -> zh_CN
        normalized = lang.replace('-', '_')

        # 精确匹配
        if normalized in _translations:
            return normalized

        # 前缀匹配（zh -> zh_CN）
        prefix = normalized.split('_')[0]
        if prefix == 'zh':
            return 'zh_CN'
        elif prefix == 'en':
            return 'en_US'

    return 'zh_CN'
