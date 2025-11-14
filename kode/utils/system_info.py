"""
系统信息工具 - 获取宿主机系统信息

用于在 AI Agent 提示词中注入系统环境信息，帮助 AI 更好地理解运行环境。
"""

import platform
import os
import sys
from typing import Dict
from pathlib import Path


def get_system_info() -> Dict[str, str]:
    """
    获取宿主机系统信息

    Returns:
        包含系统信息的字典
    """
    info = {}

    # 操作系统信息
    info['os_type'] = platform.system()  # Windows, Linux, Darwin(macOS)
    info['os_version'] = platform.version()
    info['os_release'] = platform.release()
    info['machine'] = platform.machine()  # x86_64, AMD64, ARM64 等
    info['processor'] = platform.processor()

    # Python 信息
    info['python_version'] = platform.python_version()
    info['python_implementation'] = platform.python_implementation()

    # 工作目录
    info['cwd'] = os.getcwd()

    # 环境变量（只提取关键的）
    info['shell'] = os.getenv('SHELL', os.getenv('COMSPEC', 'unknown'))
    info['user'] = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
    info['home'] = str(Path.home())

    # 系统路径分隔符
    info['path_sep'] = os.sep

    return info


def format_system_info_for_prompt() -> str:
    """
    格式化系统信息为适合添加到 AI 提示词的文本

    Returns:
        格式化的系统信息文本
    """
    info = get_system_info()

    # 根据操作系统类型调整描述
    os_friendly_name = {
        'Windows': 'Windows',
        'Linux': 'Linux',
        'Darwin': 'macOS'
    }.get(info['os_type'], info['os_type'])

    # 构建提示词片段（移除 emoji 避免 Windows 编码问题）
    lines = [
        "## 宿主机系统环境",
        "",
        f"**操作系统**: {os_friendly_name} {info['os_release']} ({info['machine']})",
        f"**Python 版本**: {info['python_version']}",
        f"**当前工作目录**: `{info['cwd']}`",
        f"**用户主目录**: `{info['home']}`",
        f"**Shell/终端**: {info['shell']}",
        f"**路径分隔符**: `{info['path_sep']}`",
        "",
        "**重要提示**:",
    ]

    # 根据操作系统添加特定提示
    if info['os_type'] == 'Windows':
        lines.extend([
            "- 使用 Windows 路径格式（反斜杠 `\\` 或正斜杠 `/`）",
            "- Shell 命令使用 PowerShell 或 cmd 语法",
            "- 文件路径不区分大小写",
            "- 使用 `dir` 而非 `ls`，使用 `del` 而非 `rm`",
        ])
    elif info['os_type'] in ['Linux', 'Darwin']:
        lines.extend([
            "- 使用 Unix/Linux 路径格式（正斜杠 `/`）",
            "- Shell 命令使用 bash/zsh 语法",
            "- 文件路径区分大小写",
            "- 使用标准 Unix 命令（ls, rm, chmod 等）",
        ])

    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    # 测试输出
    print("=== System Info Dict ===")
    import json
    print(json.dumps(get_system_info(), indent=2, ensure_ascii=False))

    print("\n=== Formatted for Prompt ===")
    print(format_system_info_for_prompt())
