"""Logging configuration for Kode."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "kode",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    verbose: bool = False,
) -> logging.Logger:
    """
    Setup logger with consistent formatting.

    Args:
        name: Logger name
        level: Logging level
        log_file: Optional file to write logs to
        verbose: Whether to enable verbose logging

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if verbose else level)

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (with UTF-8 encoding support)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    # 确保 handler 使用 UTF-8 编码，并在错误时替换无法编码的字符
    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        # 明确指定 UTF-8 编码，并在错误时替换
        file_handler = logging.FileHandler(log_file, encoding='utf-8', errors='replace')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return setup_logger(name)


def safe_log_exception(logger: logging.Logger, message: str, exc_info: Exception = None):
    """
    安全地记录异常，避免 UTF-8 编码问题。

    在 Windows 平台上，Python 的 traceback 模块可能在解析包含中文字符的源代码时
    遇到 UnicodeDecodeError。此函数提供降级处理。

    Args:
        logger: Logger 实例
        message: 日志消息
        exc_info: 异常对象（可选）
    """
    try:
        # 尝试正常记录（带 traceback）
        logger.error(message, exc_info=exc_info or True)
    except (UnicodeDecodeError, UnicodeEncodeError):
        # 如果 traceback 包含无法编码的字符，降级为简单日志
        error_msg = str(exc_info) if exc_info else "Unknown error"
        logger.error(f"{message} (encoding issue, traceback omitted): {error_msg}")