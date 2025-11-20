"""
路径工具函数

处理数据库连接名到文件系统路径的转换,确保跨平台兼容性和多用户隔离。
"""


def get_safe_connection_path(connection_name: str) -> str:
    """
    将 connection_name 转换为文件系统安全路径。

    Web API 层使用 `{user_id}:{connection_name}` 格式作为连接唯一标识,
    但 Windows 文件系统不允许路径包含冒号,因此需要替换。

    Args:
        connection_name: 连接名称,可能包含用户前缀 (格式: "user_id:name") 或不包含 (旧数据)

    Returns:
        文件系统安全的路径字符串

    Examples:
        >>> get_safe_connection_path("1:erp_db")
        '1_erp_db'

        >>> get_safe_connection_path("yanfa")  # 兼容旧数据
        'yanfa'

        >>> get_safe_connection_path("123:my_database")
        '123_my_database'

    Notes:
        - Windows 禁止路径包含冒号 (:),必须替换
        - Linux/macOS 理论上支持冒号,但为了统一性也使用下划线
        - 向后兼容:不包含冒号的连接名原样返回(旧版数据)
    """
    if ":" in connection_name:
        # 新格式: user_id:name -> user_id_name
        return connection_name.replace(":", "_")
    else:
        # 旧格式或无用户前缀: 原样返回
        return connection_name
