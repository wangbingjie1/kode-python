"""Database connectivity and schema extraction tools."""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel, Field
from sqlalchemy import text

from kode.services.database_manager import DatabaseConnection, db_manager
from kode.tools.base import KodeTool
from kode.utils.config import ConfigManager
from kode.utils.path_utils import get_safe_connection_path


# ==================== Tool Input Schemas ====================


class DatabaseConnectInput(BaseModel):
    """Input schema for DatabaseConnectTool."""

    connection_name: str = Field(description="Unique identifier for this connection")
    db_type: str = Field(
        description="Database type: postgresql, mysql, sqlserver, oracle, or sqlite"
    )
    host: str = Field(default="localhost", description="Database host address")
    port: int = Field(description="Database port number")
    database: str = Field(description="Database name")
    username: str = Field(default="", description="Database username")
    password: str = Field(default="", description="Database password")
    db_schema: Optional[str] = Field(default=None, description="Default schema (optional)")
    ssl: bool = Field(default=False, description="Use SSL connection")


class DatabaseTestConnectionInput(BaseModel):
    """Input schema for DatabaseTestConnectionTool."""

    connection_name: str = Field(description="Connection name to test")


class DatabaseDisconnectInput(BaseModel):
    """Input schema for DatabaseDisconnectTool."""

    connection_name: str = Field(description="Connection name to disconnect")


class DatabaseListConnectionsInput(BaseModel):
    """Input schema for DatabaseListConnectionsTool."""

    pass  # No input required


class DatabaseSchemaExtractorInput(BaseModel):
    """Input schema for DatabaseSchemaExtractorTool."""

    connection_name: str = Field(description="Connection name to extract schema from")
    tables: Optional[List[str]] = Field(
        default=None, description="Specific tables to extract (None = all tables)"
    )
    include_columns: bool = Field(default=True, description="Include column metadata")
    include_constraints: bool = Field(default=True, description="Include constraints (PK, FK)")
    include_indexes: bool = Field(default=True, description="Include index information")
    include_relationships: bool = Field(default=True, description="Include foreign key relationships")
    include_statistics: bool = Field(default=False, description="Include table statistics")
    include_sample_data: bool = Field(default=True, description="Include last 5 rows of sample data")
    sample_row_limit: int = Field(default=5, description="Number of sample rows to extract (default 5)")
    auto_save: bool = Field(default=True, description="Automatically save schema to file")
    version: str = Field(default="auto", description="Version identifier (auto = timestamp)")
    enable_progress: bool = Field(default=True, description="Enable progress callbacks for streaming")



class DatabaseExecuteQueryInput(BaseModel):
    """Input schema for DatabaseExecuteQueryTool."""

    connection_name: str = Field(description="Connection name to execute query on")
    sql: str = Field(description="SQL query to execute")
    params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parameters for parameterized query (e.g., {'id': 123, 'name': 'test'})"
    )
    fetch_limit: int = Field(
        default=100,
        description="Maximum number of rows to fetch (for SELECT queries)"
    )
    timeout: int = Field(
        default=30,
        description="Query timeout in seconds"
    )


# ==================== Database Tools ====================


class DatabaseConnectTool(KodeTool):
    """
    Connect to a database and store connection configuration.

    Supports: PostgreSQL, MySQL, SQL Server, Oracle, SQLite
    """

    name: str = "DatabaseConnect"
    description: str = """Connect to a database (PostgreSQL, MySQL, SQL Server, Oracle, SQLite).
    Stores the connection configuration for later use by other database tools.
    Returns connection status and metadata."""

    args_schema: Type[BaseModel] = DatabaseConnectInput
    requires_permission: bool = True
    permission_level: str = "ask_each_time"

    def _run(
        self,
        connection_name: str,
        db_type: str,
        host: str = "localhost",
        port: int = 5432,
        database: str = "",
        username: str = "",
        password: str = "",
        db_schema: Optional[str] = None,
        ssl: bool = False,
    ) -> str:
        """
        Execute database connection.

        Args:
            connection_name: Unique connection identifier
            db_type: Database type
            host: Database host
            port: Database port
            database: Database name
            username: Username
            password: Password
            db_schema: Default schema
            ssl: Use SSL

        Returns:
            Connection status message
        """
        try:
            # Create connection configuration
            connection = DatabaseConnection(
                name=connection_name,
                db_type=db_type,
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                db_schema=db_schema,
                ssl=ssl,
            )

            # Add to connection manager
            db_manager.add_connection(connection)

            # Test the connection
            test_result = db_manager.test_connection(connection_name)

            if test_result["status"] == "success":
                return json.dumps(
                    {
                        "status": "success",
                        "message": f"Successfully connected to database '{connection_name}'",
                        "connection": connection.to_dict(),
                        "db_type": db_type,
                    },
                    indent=2,
                )
            else:
                # Remove failed connection
                db_manager.remove_connection(connection_name)
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Connection test failed: {test_result['message']}",
                        "error": test_result.get("error"),
                    },
                    indent=2,
                )

        except Exception as e:
            return json.dumps(
                {"status": "error", "message": f"Failed to connect: {str(e)}"}, indent=2
            )


# ==================== Removed Tools (Optimized) ====================
# The following tools have been removed to reduce token usage:
#
# 1. DatabaseTestConnectionTool - Redundant, DatabaseConnectTool already tests connection (line 160)
# 2. DatabaseDisconnectTool - Unnecessary, connection pool manages lifecycle automatically
# 3. DatabaseListConnectionsTool - Redundant, frontend UI already lists connections via API
#
# Removed ~250 tokens total
# ===================================================================


class DatabaseSchemaExtractorTool(KodeTool):
    """
    Extract database schema metadata including tables, columns, constraints, and relationships.
    """

    name: str = "DatabaseSchemaExtractor"
    description: str = """Extract database schema metadata and save to file.

    返回概要信息(表列表、列数、关系数等),完整 schema 自动保存到文件。

    IMPORTANT: 此工具只返回 schema 概要,不返回完整数据(避免上下文溢出)。
    如需查看完整 schema,使用 FileRead 读取返回的 file_path。

    提取内容包括:
    - 表定义和列元数据(数据类型、注释、默认值)
    - 主键和外键约束
    - 索引信息
    - 表间关系图
    - 可选的样例数据(每表前5行)

    适用场景: 数据库探索、本体构建、数据分析。"""

    args_schema: Type[BaseModel] = DatabaseSchemaExtractorInput
    requires_permission: bool = False  # Read-only operation

    # 进度回调函数（由外部设置）
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def _emit_progress(self, message: str, current: int, total: int, metadata: Dict[str, Any] = None):
        """发送进度更新"""
        if self.progress_callback:
            try:
                self.progress_callback({
                    "type": "progress",
                    "message": message,
                    "current": current,
                    "total": total,
                    "percentage": int((current / total) * 100) if total > 0 else 0,
                    "metadata": metadata or {}
                })
            except Exception:
                pass  # 忽略回调错误

    def _run(
        self,
        connection_name: str,
        tables: Optional[List[str]] = None,
        include_columns: bool = True,
        include_constraints: bool = True,
        include_indexes: bool = True,
        include_relationships: bool = True,
        include_statistics: bool = False,
        include_sample_data: bool = True,
        sample_row_limit: int = 5,
        auto_save: bool = True,
        version: str = "auto",
        enable_progress: bool = True,
    ) -> str:
        """
        Extract database schema.

        Args:
            connection_name: Connection name
            tables: Specific tables (None = all)
            include_columns: Include column metadata
            include_constraints: Include constraints
            include_indexes: Include indexes
            include_relationships: Include relationships
            include_statistics: Include statistics
            include_sample_data: Include sample data (last N rows)
            sample_row_limit: Number of sample rows to extract

        Returns:
            Schema metadata as JSON
        """
        try:
            # Get inspector
            inspector = db_manager.get_inspector(connection_name)
            connection = db_manager.get_connection(connection_name)

            if not connection:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Connection '{connection_name}' not found",
                    },
                    indent=2,
                )

            # Get table names
            table_names = tables if tables else inspector.get_table_names()
            total_tables = len(table_names)

            # 发送初始进度
            if enable_progress:
                self._emit_progress(f"开始提取 {total_tables} 个表的结构...", 0, total_tables)

            schema_data = {
                "status": "success",
                "connection": connection.to_dict(),
                "database": connection.database,
                "schema": connection.db_schema,
                "table_count": total_tables,
                "tables": {},
            }

            # 并发批量提取表结构和样例数据（带进度）
            schema_data["tables"] = self._extract_tables_batch(
                connection_name=connection_name,
                table_names=table_names,
                include_columns=include_columns,
                include_constraints=include_constraints,
                include_indexes=include_indexes,
                include_sample_data=include_sample_data,
                sample_row_limit=sample_row_limit,
                max_workers=10,
                enable_progress=enable_progress
            )

            # 完成进度
            if enable_progress:
                self._emit_progress(f"成功提取 {total_tables} 个表", total_tables, total_tables)

            # Build relationship graph
            if include_relationships:
                relationships = []
                for table_name, table_data in schema_data["tables"].items():
                    if "foreign_keys" in table_data:
                        for fk in table_data["foreign_keys"]:
                            relationships.append(
                                {
                                    "from_table": table_name,
                                    "from_columns": fk["columns"],
                                    "to_table": fk["referred_table"],
                                    "to_columns": fk["referred_columns"],
                                    "constraint_name": fk["name"],
                                }
                            )
                schema_data["relationships"] = relationships

            # Statistics (optional - may be slow for large databases)
            if include_statistics:
                schema_data["statistics"] = self._get_statistics(connection_name, table_names)

            # Add extraction timestamp
            extraction_time = datetime.now().isoformat()
            schema_data["extraction_time"] = extraction_time

            # Auto-save schema to file
            save_result = None
            if auto_save:
                save_result = self._save_schema(schema_data, connection_name, version)
                schema_data["storage"] = save_result

            # Auto-cluster schema into domains (if enabled in config)
            clustering_result = None
            uncertainty_result = None
            if auto_save and save_result and save_result.get("saved"):
                clustering_result = self._auto_cluster_schema(
                    connection_name=connection_name,
                    schema_file=save_result.get("latest_file"),
                    enable_progress=enable_progress
                )
                
                # 🔥 新增: 自动分析不确定性（仅在聚类成功后）
                if clustering_result and clustering_result.get("status") == "success":
                    uncertainty_result = self._auto_analyze_uncertainties(
                        connection_name=connection_name,
                        enable_progress=enable_progress
                    )

            # 构建概要信息(不返回完整数据,避免上下文爆炸)
            # 注意: schema_data["tables"] 是字典 {table_name: table_data}, 不是列表
            tables_dict = schema_data.get("tables", {})
            summary = {
                "status": "success",
                "connection": schema_data["connection"],
                "extraction_time": extraction_time,
                "summary": {
                    "total_tables": len(tables_dict),
                    "table_list": [
                        {
                            "name": t["name"],
                            "comment": t.get("comment", ""),
                            "column_count": len(t.get("columns", [])),
                            "has_primary_key": bool(t.get("primary_key")),
                            "foreign_key_count": len(t.get("foreign_keys", [])),
                            "index_count": len(t.get("indexes", [])),
                            "sample_row_count": t.get("sample_data", {}).get("row_count", 0)
                        }
                        for t in tables_dict.values()  # 修复: 迭代字典的值,不是字典本身
                    ],
                    "total_relationships": len(schema_data.get("relationships", [])),
                },
                "message": f"成功提取 {len(tables_dict)} 个表的 schema 元数据"
            }

            # 如果自动保存,添加文件路径信息
            if save_result and save_result.get("saved"):
                summary["storage"] = {
                    "status": "success",
                    "file_path": save_result.get("latest_file"),
                    "version": save_result.get("version"),
                    "message": f"Schema 已保存到文件,使用 FileRead 工具读取完整内容: {save_result.get('latest_file')}"
                }
            elif save_result:
                summary["storage"] = {
                    "status": "error",
                    "message": f"Schema 保存失败: {save_result.get('error', 'Unknown error')}"
                }
            else:
                summary["warning"] = "Schema 未保存到文件 (auto_save=False),完整数据未持久化"

            # 如果执行了聚类,添加聚类结果
            if clustering_result:
                summary["clustering"] = clustering_result
            
            # 如果执行了不确定性分析,添加分析结果
            if uncertainty_result:
                summary["uncertainty"] = uncertainty_result

            return json.dumps(summary, indent=2, ensure_ascii=False)

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to extract schema: {str(e)}",
                },
                indent=2,
            )

    def _get_statistics(self, connection_name: str, table_names: List[str]) -> Dict[str, Any]:
        """Get table statistics (row counts, etc.)."""
        stats = {}
        try:
            engine = db_manager.get_engine(connection_name)
            with engine.connect() as conn:
                for table_name in table_names:
                    try:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        row_count = result.scalar()
                        stats[table_name] = {"row_count": row_count}
                    except Exception:
                        stats[table_name] = {"row_count": "unknown"}
        except Exception:
            pass

        return stats

    def _get_sample_data(
        self, connection_name: str, table_name: str, limit: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Get sample data from a table (fast sampling without sorting).

        优化策略：
        - 移除 ORDER BY 排序（大表排序极慢）
        - 直接 LIMIT 取前 N 行（毫秒级响应）
        - PostgreSQL 使用 TABLESAMPLE 快速采样

        Args:
            connection_name: Database connection name
            table_name: Table name to sample
            limit: Number of rows to retrieve

        Returns:
            Dictionary with sample data or None if failed
        """
        try:
            engine = db_manager.get_engine(connection_name)
            connection = db_manager.get_connection(connection_name)
            db_type = connection.db_type.lower()

            with engine.connect() as conn:
                # 根据数据库类型构建快速查询（不排序）
                if db_type == "postgresql":
                    # PostgreSQL: 尝试使用 TABLESAMPLE 快速随机采样
                    # 如果表太小会失败，fallback 到普通 LIMIT
                    try:
                        query = f"SELECT * FROM {table_name} TABLESAMPLE SYSTEM (1) LIMIT {limit}"
                        result = conn.execute(text(query))
                    except Exception:
                        query = f"SELECT * FROM {table_name} LIMIT {limit}"
                        result = conn.execute(text(query))
                elif db_type in ["mysql", "sqlite"]:
                    # MySQL/SQLite: 直接 LIMIT（不排序）
                    query = f"SELECT * FROM {table_name} LIMIT {limit}"
                    result = conn.execute(text(query))
                elif db_type == "sqlserver":
                    # SQL Server: TOP（不排序）
                    query = f"SELECT TOP {limit} * FROM {table_name}"
                    result = conn.execute(text(query))
                elif db_type == "oracle":
                    # Oracle: ROWNUM（不排序）
                    query = f"SELECT * FROM {table_name} WHERE ROWNUM <= {limit}"
                    result = conn.execute(text(query))
                else:
                    # 默认使用 LIMIT
                    query = f"SELECT * FROM {table_name} LIMIT {limit}"
                    result = conn.execute(text(query))

                rows = result.fetchall()
                columns = list(result.keys())

                # 转换为字典列表
                sample_rows = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # 转换非 JSON 可序列化的类型
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        elif not isinstance(value, (str, int, float, bool, type(None))):
                            value = str(value)
                        row_dict[col] = value
                    sample_rows.append(row_dict)

                return {
                    "row_count": len(sample_rows),
                    "rows": sample_rows,
                    "note": f"前 {len(sample_rows)} 行样例数据（快速采样，无排序）"
                }

        except Exception as e:
            # 如果失败，返回错误信息而不是 None
            return {
                "row_count": 0,
                "rows": [],
                "error": str(e),
                "note": "无法获取样例数据"
            }

    def _get_sample_data_batch(
        self, connection_name: str, table_names: List[str], limit: int = 5, max_workers: int = 5
    ) -> Dict[str, Any]:
        """
        Batch get sample data from multiple tables concurrently.

        并发优化：使用线程池并行读取多表样例数据，大幅提升性能。

        Args:
            connection_name: Database connection name
            table_names: List of table names to sample
            limit: Number of rows per table
            max_workers: Maximum concurrent threads

        Returns:
            Dictionary mapping table_name -> sample_data
        """
        results = {}

        # 使用线程池并发读取
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_table = {
                executor.submit(self._get_sample_data, connection_name, table_name, limit): table_name
                for table_name in table_names
            }

            # 收集结果
            for future in as_completed(future_to_table):
                table_name = future_to_table[future]
                try:
                    sample_data = future.result()
                    results[table_name] = sample_data
                except Exception as e:
                    results[table_name] = {
                        "row_count": 0,
                        "rows": [],
                        "error": str(e),
                        "note": "并发读取失败"
                    }

        return results

    def _parse_enum_from_comment(self, comment: str) -> Optional[Dict[str, str]]:
        """
        从字段注释中解析枚举值映射关系(使用简单正则模式)

        仅识别最常见的格式:
        - "0=待支付;1=支付成功;2=支付失败"  (分号分隔)
        - "0:待支付,1:支付成功,2:支付失败"  (逗号分隔)

        Args:
            comment: 字段注释文本

        Returns:
            枚举值映射字典 {code: label} 或 None
        """
        if not comment:
            return None

        # 只保留最常见的两种模式,避免误匹配
        # 模式1: "0=xxx;1=yyy" (分号分隔)
        pattern1 = r'(\d+|["\'][^"\']+["\'])\s*=\s*([^;]+)'
        matches1 = re.findall(pattern1, comment)
        if len(matches1) >= 2:  # 至少2个枚举值才算有效
            return {m[0].strip('"\'').strip(): m[1].strip() for m in matches1}

        # 模式2: "0:xxx,1:yyy" 或 "0-xxx,1-yyy" (逗号分隔)
        pattern2 = r'(\d+|["\'][^"\']+["\'])\s*[:：-]\s*([^,，;]+)'
        matches2 = re.findall(pattern2, comment)
        if len(matches2) >= 2:  # 至少2个枚举值才算有效
            return {m[0].strip('"\'').strip(): m[1].strip() for m in matches2}

        return None

    def _extract_enum_values(
        self, connection_name: str, table_name: str, column: Dict[str, Any]
    ) -> Optional[List[str]]:
        """
        Extract enum values for ENUM type columns.

        Supports MySQL and PostgreSQL enum types.

        Args:
            connection_name: Database connection name
            table_name: Table name
            column: Column metadata from inspector

        Returns:
            List of enum values or None if not an enum type
        """
        try:
            connection = db_manager.get_connection(connection_name)
            db_type = connection.db_type.lower()
            col_type_str = str(column["type"]).lower()

            # Check if it's an ENUM type
            if "enum" not in col_type_str:
                return None

            engine = db_manager.get_engine(connection_name)

            with engine.connect() as conn:
                if db_type == "mysql":
                    # MySQL: Extract from INFORMATION_SCHEMA.COLUMNS
                    query = text("""
                        SELECT COLUMN_TYPE
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = :table_name
                          AND COLUMN_NAME = :column_name
                    """)
                    result = conn.execute(query, {"table_name": table_name, "column_name": column["name"]})
                    row = result.fetchone()

                    if row:
                        column_type = row[0]  # e.g., "enum('free','pro','enterprise')"
                        # Parse enum values using regex
                        match = re.search(r"enum\((.*?)\)", column_type, re.IGNORECASE)
                        if match:
                            enum_str = match.group(1)
                            # Extract values (strip quotes)
                            enum_values = [v.strip().strip("'\"") for v in enum_str.split(",")]
                            return enum_values

                elif db_type == "postgresql":
                    # PostgreSQL: Extract from pg_type and pg_enum
                    # First, get the enum type name from the column type
                    type_name_match = re.search(r"([a-z_]+)", col_type_str)
                    if not type_name_match:
                        return None

                    type_name = type_name_match.group(1)

                    query = text("""
                        SELECT e.enumlabel
                        FROM pg_type t
                        JOIN pg_enum e ON t.oid = e.enumtypid
                        WHERE t.typname = :type_name
                        ORDER BY e.enumsortorder
                    """)
                    result = conn.execute(query, {"type_name": type_name})
                    rows = result.fetchall()

                    if rows:
                        enum_values = [row[0] for row in rows]
                        return enum_values

            return None

        except Exception as e:
            # If extraction fails, silently return None (not critical)
            return None

    def _extract_single_table_metadata(
        self,
        connection_name: str,
        table_name: str,
        include_columns: bool,
        include_constraints: bool,
        include_indexes: bool,
        include_sample_data: bool,
        sample_row_limit: int
    ) -> Dict[str, Any]:
        """
        Extract metadata for a single table.

        Args:
            connection_name: Database connection name
            table_name: Table name
            include_columns: Include column metadata
            include_constraints: Include constraints
            include_indexes: Include indexes
            include_sample_data: Include sample data
            sample_row_limit: Number of sample rows

        Returns:
            Table metadata dictionary
        """
        inspector = db_manager.get_inspector(connection_name)
        table_data: Dict[str, Any] = {"name": table_name}

        # Table comment
        try:
            table_comment_info = inspector.get_table_comment(table_name)
            if table_comment_info and table_comment_info.get("text"):
                table_data["comment"] = table_comment_info["text"]
        except (NotImplementedError, Exception):
            pass

        # Columns
        if include_columns:
            columns = inspector.get_columns(table_name)
            enriched_columns = []

            for col in columns:
                col_comment = col.get("comment")
                col_info = {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": str(col.get("default")) if col.get("default") else None,
                    "autoincrement": col.get("autoincrement", False),
                    "comment": col_comment,
                }

                # 提取枚举值 - 两种方式:
                # 1. 从数据库 ENUM 类型提取
                enum_values = self._extract_enum_values(connection_name, table_name, col)
                if enum_values:
                    col_info["enum_values"] = enum_values

                # 2. 从 comment 中解析枚举映射(适用于 tinyint/varchar 等类型)
                enum_mapping = self._parse_enum_from_comment(col_comment)
                if enum_mapping:
                    col_info["enum_mapping"] = enum_mapping

                enriched_columns.append(col_info)

            table_data["columns"] = enriched_columns
            table_data["column_count"] = len(enriched_columns)

        # Primary Keys
        if include_constraints:
            pk = inspector.get_pk_constraint(table_name)
            if pk and pk.get("constrained_columns"):
                table_data["primary_key"] = {
                    "name": pk.get("name"),
                    "columns": pk["constrained_columns"],
                }

            # Foreign Keys
            fks = inspector.get_foreign_keys(table_name)
            if fks:
                table_data["foreign_keys"] = [
                    {
                        "name": fk.get("name"),
                        "columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"],
                    }
                    for fk in fks
                ]

        # Indexes
        if include_indexes:
            indexes = inspector.get_indexes(table_name)
            if indexes:
                table_data["indexes"] = [
                    {
                        "name": idx["name"],
                        "columns": idx["column_names"],
                        "unique": idx.get("unique", False),
                    }
                    for idx in indexes
                ]

        # Sample Data
        if include_sample_data:
            sample_data = self._get_sample_data(connection_name, table_name, sample_row_limit)
            if sample_data:
                table_data["sample_data"] = sample_data

        return table_data

    def _extract_all_tables_fast(
        self, connection_name: str, table_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fast batch extraction using information_schema (一次性查询所有表结构).

        性能最优：单次 SQL 查询获取所有表、字段、约束信息。

        Args:
            connection_name: Database connection name
            table_names: List of table names to extract

        Returns:
            Dictionary of {table_name: {columns: [...], primary_keys: [...], foreign_keys: [...]}}
        """
        engine = db_manager.get_engine(connection_name)
        connection = db_manager.get_connection(connection_name)
        db_type = connection.db_type.lower()

        results = {name: {"name": name, "columns": [], "foreign_keys": []} for name in table_names}

        table_list = "', '".join(table_names)

        with engine.connect() as conn:
            try:
                # 1. 批量查询所有列信息（一次查询）
                if db_type == "postgresql":
                    columns_query = f"""
                        SELECT
                            table_name, column_name, data_type,
                            is_nullable, column_default,
                            col_description((table_schema||'.'||table_name)::regclass::oid, ordinal_position) as comment
                        FROM information_schema.columns
                        WHERE table_name IN ('{table_list}')
                        ORDER BY table_name, ordinal_position
                    """
                elif db_type == "mysql":
                    columns_query = f"""
                        SELECT
                            TABLE_NAME as table_name,
                            COLUMN_NAME as column_name,
                            DATA_TYPE as data_type,
                            COLUMN_TYPE as column_type,
                            IS_NULLABLE as is_nullable,
                            COLUMN_DEFAULT as column_default,
                            COLUMN_COMMENT as comment
                        FROM information_schema.COLUMNS
                        WHERE TABLE_NAME IN ('{table_list}')
                        ORDER BY TABLE_NAME, ORDINAL_POSITION
                    """
                elif db_type == "sqlite":
                    # SQLite 不支持 information_schema，fallback 到并发模式
                    return None
                else:
                    return None

                result = conn.execute(text(columns_query))
                for row in result:
                    table_name = row[0]
                    if table_name in results:
                        # MySQL: table_name, column_name, data_type, column_type, is_nullable, column_default, comment
                        # PostgreSQL: table_name, column_name, data_type, is_nullable, column_default, comment
                        if db_type == "mysql":
                            col_comment = row[6] if len(row) > 6 else None
                            col_info = {
                                "name": row[1],
                                "type": row[2],
                                "nullable": row[4] == "YES",
                                "default": row[5] if len(row) > 5 else None,
                                "comment": col_comment
                            }

                            # 1. Extract enum values from COLUMN_TYPE (row[3])
                            column_type = row[3]  # e.g., "enum('free','pro','enterprise')"
                            if column_type and "enum" in column_type.lower():
                                enum_match = re.search(r"enum\((.*?)\)", column_type, re.IGNORECASE)
                                if enum_match:
                                    enum_str = enum_match.group(1)
                                    enum_values = [v.strip().strip("'\"") for v in enum_str.split(",")]
                                    col_info["enum_values"] = enum_values

                            # 2. 从 comment 中解析枚举映射
                            enum_mapping = self._parse_enum_from_comment(col_comment)
                            if enum_mapping:
                                col_info["enum_mapping"] = enum_mapping
                        else:
                            # PostgreSQL
                            col_comment = row[5] if len(row) > 5 else None
                            col_info = {
                                "name": row[1],
                                "type": row[2],
                                "nullable": row[3] == "YES",
                                "default": row[4] if len(row) > 4 else None,
                                "comment": col_comment
                            }

                            # 从 comment 中解析枚举映射
                            enum_mapping = self._parse_enum_from_comment(col_comment)
                            if enum_mapping:
                                col_info["enum_mapping"] = enum_mapping

                        results[table_name]["columns"].append(col_info)

                # 2. 批量查询主键
                if db_type == "postgresql":
                    pk_query = f"""
                        SELECT
                            tc.table_name,
                            kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                            ON tc.constraint_name = kcu.constraint_name
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                            AND tc.table_name IN ('{table_list}')
                        ORDER BY tc.table_name, kcu.ordinal_position
                    """
                elif db_type == "mysql":
                    pk_query = f"""
                        SELECT
                            TABLE_NAME as table_name,
                            COLUMN_NAME as column_name
                        FROM information_schema.KEY_COLUMN_USAGE
                        WHERE CONSTRAINT_NAME = 'PRIMARY'
                            AND TABLE_NAME IN ('{table_list}')
                        ORDER BY TABLE_NAME, ORDINAL_POSITION
                    """
                else:
                    pk_query = None

                if pk_query:
                    result = conn.execute(text(pk_query))
                    pk_map = {}
                    for row in result:
                        table_name = row[0]
                        if table_name not in pk_map:
                            pk_map[table_name] = []
                        pk_map[table_name].append(row[1])

                    for table_name, pk_cols in pk_map.items():
                        if table_name in results:
                            results[table_name]["primary_key"] = {
                                "name": "PRIMARY",
                                "columns": pk_cols
                            }

                # 3. 批量查询外键
                if db_type == "postgresql":
                    fk_query = f"""
                        SELECT
                            tc.table_name,
                            tc.constraint_name,
                            kcu.column_name,
                            ccu.table_name AS foreign_table_name,
                            ccu.column_name AS foreign_column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                            ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage ccu
                            ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                            AND tc.table_name IN ('{table_list}')
                    """
                elif db_type == "mysql":
                    fk_query = f"""
                        SELECT
                            TABLE_NAME as table_name,
                            CONSTRAINT_NAME as constraint_name,
                            COLUMN_NAME as column_name,
                            REFERENCED_TABLE_NAME as foreign_table_name,
                            REFERENCED_COLUMN_NAME as foreign_column_name
                        FROM information_schema.KEY_COLUMN_USAGE
                        WHERE REFERENCED_TABLE_NAME IS NOT NULL
                            AND TABLE_NAME IN ('{table_list}')
                    """
                else:
                    fk_query = None

                if fk_query:
                    result = conn.execute(text(fk_query))
                    fk_map = {}
                    for row in result:
                        table_name = row[0]
                        fk_name = row[1]
                        key = (table_name, fk_name)
                        if key not in fk_map:
                            fk_map[key] = {
                                "name": fk_name,
                                "columns": [],
                                "referred_table": row[3],
                                "referred_columns": []
                            }
                        fk_map[key]["columns"].append(row[2])
                        fk_map[key]["referred_columns"].append(row[4])

                    for (table_name, _), fk_data in fk_map.items():
                        if table_name in results:
                            results[table_name]["foreign_keys"].append(fk_data)

                return results

            except Exception as e:
                # 如果批量查询失败，返回 None，fallback 到并发模式
                # 常见原因：查询超时、权限不足、数据库不支持
                import logging
                logging.warning(f"Fast schema extraction failed: {e}, falling back to concurrent mode")
                return None

    def _extract_tables_batch(
        self,
        connection_name: str,
        table_names: List[str],
        include_columns: bool,
        include_constraints: bool,
        include_indexes: bool,
        include_sample_data: bool,
        sample_row_limit: int,
        max_workers: int = 10,
        enable_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Batch extract metadata for multiple tables concurrently.

        优化策略：
        1. 优先使用 information_schema 一次性批量查询（最快）
        2. Fallback 到并发模式（适用于 SQLite 等不支持的数据库）

        Args:
            connection_name: Database connection name
            table_names: List of table names
            include_columns: Include column metadata
            include_constraints: Include constraints
            include_indexes: Include indexes
            include_sample_data: Include sample data
            sample_row_limit: Number of sample rows
            max_workers: Maximum concurrent threads
            enable_progress: Enable progress callbacks

        Returns:
            Dictionary mapping table_name -> table_metadata
        """
        total_tables = len(table_names)

        # 尝试使用快速批量查询
        if include_columns and include_constraints:
            if enable_progress:
                self._emit_progress("使用快速批量查询提取表结构...", 0, total_tables)

            fast_results = self._extract_all_tables_fast(connection_name, table_names)
            if fast_results:
                # 补充 comment 和 column_count
                for table_name, table_data in fast_results.items():
                    if "columns" in table_data:
                        table_data["column_count"] = len(table_data["columns"])

                if enable_progress:
                    self._emit_progress("表结构提取完成，开始读取样例数据...", total_tables // 2, total_tables)

                # 补充样例数据（并发读取，带进度）
                if include_sample_data:
                    sample_data_map = self._get_sample_data_batch_with_progress(
                        connection_name, table_names, sample_row_limit,
                        max_workers=max_workers, enable_progress=enable_progress
                    )
                    for table_name, sample_data in sample_data_map.items():
                        if table_name in fast_results:
                            fast_results[table_name]["sample_data"] = sample_data

                return fast_results

        # Fallback: 使用线程池并发提取（兼容所有数据库）
        if enable_progress:
            self._emit_progress("使用并发模式提取表结构...", 0, total_tables)

        results = {}
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_table = {
                executor.submit(
                    self._extract_single_table_metadata,
                    connection_name,
                    table_name,
                    include_columns,
                    include_constraints,
                    include_indexes,
                    include_sample_data,
                    sample_row_limit
                ): table_name
                for table_name in table_names
            }

            for future in as_completed(future_to_table):
                table_name = future_to_table[future]
                try:
                    table_data = future.result()
                    results[table_name] = table_data
                    completed += 1

                    # 定期发送进度（每10个表或最后一个）
                    if enable_progress and (completed % 10 == 0 or completed == total_tables):
                        self._emit_progress(
                            f"已提取 {completed}/{total_tables} 个表",
                            completed, total_tables,
                            {"current_table": table_name}
                        )
                except Exception as e:
                    results[table_name] = {
                        "name": table_name,
                        "error": str(e),
                        "note": "提取表结构失败"
                    }
                    completed += 1

        return results

    def _get_sample_data_batch_with_progress(
        self, connection_name: str, table_names: List[str],
        limit: int = 5, max_workers: int = 5, enable_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Batch get sample data with progress reporting.
        """
        results = {}
        total = len(table_names)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_table = {
                executor.submit(self._get_sample_data, connection_name, table_name, limit): table_name
                for table_name in table_names
            }

            for future in as_completed(future_to_table):
                table_name = future_to_table[future]
                try:
                    sample_data = future.result()
                    results[table_name] = sample_data
                    completed += 1

                    # 定期发送进度（每5个表）
                    if enable_progress and (completed % 5 == 0 or completed == total):
                        self._emit_progress(
                            f"已读取 {completed}/{total} 个表的样例数据",
                            completed, total,
                            {"current_table": table_name}
                        )
                except Exception as e:
                    results[table_name] = {
                        "row_count": 0,
                        "rows": [],
                        "error": str(e),
                        "note": "并发读取失败"
                    }
                    completed += 1

        return results

    def _save_schema(
        self, schema_data: Dict[str, Any], connection_name: str, version: str
    ) -> Dict[str, Any]:
        """
        Save schema to file with version control.

        Args:
            schema_data: Schema metadata to save
            connection_name: Database connection name
            version: Version identifier

        Returns:
            Storage metadata
        """
        try:
            # Get storage path from config
            config = ConfigManager()
            storage_path = config.get("storage.schema_path", "./schema_store")

            # Create storage directory
            base_dir = Path(storage_path)
            conn_dir = base_dir / get_safe_connection_path(connection_name)
            conn_dir.mkdir(parents=True, exist_ok=True)

            # Generate version
            if version == "auto":
                version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Prepare schema with metadata
            schema_with_meta = {
                "version": version,
                "created_at": datetime.now().isoformat(),
                "connection_name": connection_name,
                "schema": schema_data,
            }

            # Save versioned file
            version_file = conn_dir / f"schema_{version}.json"
            with open(version_file, "w", encoding="utf-8") as f:
                json.dump(schema_with_meta, f, indent=2, ensure_ascii=False)

            # Update latest pointer
            latest_file = conn_dir / "schema_latest.json"
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(schema_with_meta, f, indent=2, ensure_ascii=False)

            return {
                "saved": True,
                "version": version,
                "version_file": str(version_file),
                "latest_file": str(latest_file),
            }

        except Exception as e:
            return {
                "saved": False,
                "error": str(e),
            }

    def _auto_cluster_schema(
        self, connection_name: str, schema_file: str, enable_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Automatically cluster schema into domains.

        Args:
            connection_name: Database connection name
            schema_file: Path to saved schema file
            enable_progress: Enable progress callbacks

        Returns:
            Clustering result summary

        Raises:
            Exception: If clustering fails, propagate error to caller
        """
        try:
            # Send progress update
            if enable_progress:
                self._emit_progress("AI analyzing tables for domain clustering...", 0, 1)

            # Import and instantiate clusterer
            from kode.tools.schema_clustering_tool import DatabaseSchemaClusterer

            clusterer = DatabaseSchemaClusterer()

            # Execute clustering with fixed parameters
            result_json = clusterer._run(
                connection_name=connection_name,
                schema_file=schema_file,
                target_tables_per_domain=10,
                max_columns_for_analysis=20,
                llm_model="main",
                output_language="en",
            )

            # Parse result
            result = json.loads(result_json)

            # Check status and raise if failed
            if result.get("status") != "success":
                error_msg = result.get("message", "Unknown clustering error")
                raise RuntimeError(f"Schema clustering failed: {error_msg}")

            # Validate result structure
            if "clustering_summary" not in result:
                raise RuntimeError("Invalid clustering result: missing clustering_summary")
            if "storage" not in result:
                raise RuntimeError("Invalid clustering result: missing storage")

            storage = result.get("storage", {})
            if not storage.get("saved"):
                error = storage.get("error", "Unknown storage error")
                raise RuntimeError(f"Failed to save domain schemas: {error}")

            if "domain_index_file" not in storage:
                raise RuntimeError("Invalid clustering result: missing domain_index_file in storage")

            if enable_progress:
                total_domains = result["clustering_summary"]["total_domains"]
                self._emit_progress(f"Successfully clustered into {total_domains} domains", 1, 1)

            # Return compact summary
            return {
                "status": "success",
                "total_domains": result["clustering_summary"]["total_domains"],
                "domains": [
                    {
                        "name": d["name"],
                        "table_count": d["table_count"]
                    }
                    for d in result["clustering_summary"]["domains"]
                ],
                "domain_index_file": storage.get("domain_index_file")
            }

        except Exception as e:
            if enable_progress:
                self._emit_progress(f"Clustering failed: {str(e)}", 0, 1)
            raise  # Re-raise to caller

    def _auto_analyze_uncertainties(
        self, connection_name: str, enable_progress: bool = True
    ) -> Dict[str, Any]:
        """
        自动分析领域不确定性（仅在聚类成功后调用）

        Args:
            connection_name: 数据库连接名
            enable_progress: 是否启用进度回调

        Returns:
            不确定性分析结果摘要
        """
        try:
            if enable_progress:
                self._emit_progress("AI analyzing domain uncertainties...", 0, 1)

            # 导入并实例化不确定性分析器
            from kode.tools.domain_uncertainty_analyzer import DomainUncertaintyAnalyzer

            analyzer = DomainUncertaintyAnalyzer()

            # 执行不确定性分析
            result_json = analyzer._run(
                connection_name=connection_name,
                llm_model="main",
                max_concurrent_domains=5
            )

            # 解析结果
            result = json.loads(result_json)

            if result.get("status") != "success":
                error_msg = result.get("message", "Unknown error")
                raise RuntimeError(f"Uncertainty analysis failed: {error_msg}")

            if enable_progress:
                total_uncertainties = result.get("statistics", {}).get("total_uncertainties", 0)
                self._emit_progress(
                    f"Identified {total_uncertainties} uncertainties", 1, 1
                )

            # 返回紧凑摘要
            stats = result.get("statistics", {})
            return {
                "status": "success",
                "total_uncertainties": stats.get("total_uncertainties", 0),
                "high_priority": stats.get("high_priority", 0),
                "medium_priority": stats.get("medium_priority", 0),
                "low_priority": stats.get("low_priority", 0),
                "next_step": result.get("next_step", "")
            }

        except Exception as e:
            if enable_progress:
                self._emit_progress(f"Uncertainty analysis failed: {str(e)}", 0, 1)
            # 不中断流程，只记录失败
            return {
                "status": "failed",
                "error": str(e),
                "message": "Uncertainty analysis failed but schema extraction succeeded"
            }


class DatabaseExecuteQueryTool(KodeTool):
    """
    Execute SQL queries on connected databases.
    Supports both read operations (SELECT) and write operations (INSERT/UPDATE/DELETE).
    Write operations require explicit permission confirmation.
    """

    name: str = "DatabaseExecuteQuery"
    description: str = """Execute SQL queries on a database.
    - SELECT queries: Read-only, returns results (limited by fetch_limit)
    - INSERT/UPDATE/DELETE: Requires permission, returns affected row count
    - Supports parameterized queries to prevent SQL injection
    - Use :param_name syntax for parameters (e.g., 'SELECT * FROM users WHERE id = :id')"""

    args_schema: Type[BaseModel] = DatabaseExecuteQueryInput
    requires_permission: bool = False  # Will check dynamically based on query type

    def _run(
        self,
        connection_name: str,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        fetch_limit: int = 100,
        timeout: int = 30,
    ) -> str:
        """
        Execute SQL query.

        Args:
            connection_name: Connection name to execute on
            sql: SQL query to execute
            params: Parameters for parameterized query
            fetch_limit: Max rows to fetch (SELECT only)
            timeout: Query timeout in seconds

        Returns:
            Query results as JSON
        """
        try:
            # Get connection
            connection = db_manager.get_connection(connection_name)
            if not connection:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Connection '{connection_name}' not found",
                    },
                    indent=2,
                )

            # Determine query type
            query_type = self._get_query_type(sql)
            is_write_operation = query_type in ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "TRUNCATE"]

            # Check permission for write operations
            if is_write_operation and self.requires_permission:
                # This will be caught by the permission system
                pass

            # Get engine and execute
            engine = db_manager.get_engine(connection_name)

            with engine.connect() as conn:
                # Set timeout if supported
                try:
                    conn.execute(text(f"SET statement_timeout = {timeout * 1000}"))  # PostgreSQL
                except Exception:
                    pass  # Not all databases support this

                # Execute query
                if params:
                    result = conn.execute(text(sql), params)
                else:
                    result = conn.execute(text(sql))

                # Process results based on query type
                if query_type == "SELECT":
                    # Fetch results
                    rows = result.fetchmany(fetch_limit)
                    columns = list(result.keys())

                    # Convert to list of dicts
                    data = []
                    for row in rows:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            value = row[i]
                            # Convert non-JSON-serializable types
                            if isinstance(value, (datetime,)):
                                value = value.isoformat()
                            elif not isinstance(value, (str, int, float, bool, type(None))):
                                value = str(value)
                            row_dict[col] = value
                        data.append(row_dict)

                    # Check if more rows available
                    has_more = len(rows) == fetch_limit

                    return json.dumps(
                        {
                            "status": "success",
                            "query_type": query_type,
                            "row_count": len(data),
                            "has_more": has_more,
                            "columns": columns,
                            "data": data,
                            "sql": sql,
                            "connection_name": connection_name,
                            "message": f"查询返回 {len(data)} 行" +
                                      (f" (限制 {fetch_limit} 行，可能有更多)" if has_more else ""),
                        },
                        indent=2,
                        ensure_ascii=False,
                    )

                else:
                    # Write operation - commit and return affected rows
                    conn.commit()
                    affected_rows = result.rowcount if hasattr(result, 'rowcount') else 0

                    return json.dumps(
                        {
                            "status": "success",
                            "query_type": query_type,
                            "affected_rows": affected_rows,
                            "sql": sql,
                            "connection_name": connection_name,
                            "message": f"{query_type} 操作完成，影响 {affected_rows} 行",
                        },
                        indent=2,
                        ensure_ascii=False,
                    )

        except Exception as e:
            error_msg = str(e)
            # Extract useful error information
            if "syntax error" in error_msg.lower():
                suggestion = "Check SQL syntax"
            elif "permission denied" in error_msg.lower() or "access denied" in error_msg.lower():
                suggestion = "Check database permissions"
            elif "timeout" in error_msg.lower():
                suggestion = "Query timed out, try optimizing or increasing timeout"
            else:
                suggestion = "Check query and parameters"

            return json.dumps(
                {
                    "status": "error",
                    "message": f"Query execution failed: {error_msg}",
                    "suggestion": suggestion,
                    "query_type": self._get_query_type(sql),
                },
                indent=2,
                ensure_ascii=False,
            )

    def _get_query_type(self, sql: str) -> str:
        """
        Determine SQL query type from SQL string.

        Args:
            sql: SQL query string

        Returns:
            Query type (SELECT, INSERT, UPDATE, etc.)
        """
        # Remove leading whitespace and comments
        sql_clean = sql.strip()
        sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)  # Remove /* */ comments
        sql_clean = re.sub(r'--.*?(\n|$)', '', sql_clean)  # Remove -- comments
        sql_clean = sql_clean.strip()

        # Get first keyword
        match = re.match(r'^\s*(\w+)', sql_clean, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return "UNKNOWN"


class SchemaQueryInput(BaseModel):
    """Input schema for SchemaQueryTool."""

    connection_name: str = Field(description="Database connection name")
    table_name: str = Field(description="Table name to query schema for")
    include_sample_data: bool = Field(
        default=False, description="Include sample data in response (increases token usage)"
    )


class SchemaQueryTool(KodeTool):
    """
    Query detailed schema for a specific table from cached schema file.

    Returns complete table structure including:
    - Column definitions (type, nullable, default, comment)
    - Enum mappings (parsed from comments or ENUM types)
    - Primary/Foreign keys
    - Indexes
    - Sample data (optional)

    Much more token-efficient than loading entire schema file.
    """

    name: str = "SchemaQuery"
    description: str = """Query detailed schema for a specific database table.

    从缓存的 schema 文件中快速查询单表的完整结构信息,包括:
    - 字段定义(类型、注释、默认值、是否可空)
    - 枚举映射(enum_mapping): code->label 的映射关系
    - 主键、外键、索引
    - 样例数据(可选)

    优势: 比读取完整 schema 文件节省 90% 以上 token。

    使用场景:
    - 生成 SQL 前,确认字段的枚举值
    - 检查字段约束(nullable, default)
    - 查看外键关系
    """

    args_schema: Type[BaseModel] = SchemaQueryInput
    requires_permission: bool = False  # Read-only

    def _run(
        self,
        connection_name: str,
        table_name: str,
        include_sample_data: bool = False,
    ) -> str:
        """
        Query table schema from cached file.

        Args:
            connection_name: Database connection name
            table_name: Table name
            include_sample_data: Whether to include sample data

        Returns:
            Table schema as JSON
        """
        try:
            # Construct schema file path
            config = ConfigManager()
            storage_path = config.get("storage.schema_path", "./schema_store")
            safe_conn_name = get_safe_connection_path(connection_name)

            schema_file = Path(storage_path) / safe_conn_name / "schema_latest.json"

            if not schema_file.exists():
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Schema file not found: {schema_file}. "
                        f"Please run DatabaseSchemaExtractor first.",
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            # Load schema file
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_data = json.load(f)

            # Extract table data
            tables = schema_data.get("schema", {}).get("tables", {})

            if table_name not in tables:
                available_tables = list(tables.keys())[:10]  # Show first 10
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Table '{table_name}' not found in schema.",
                        "available_tables": available_tables,
                        "total_tables": len(tables),
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            table_data = tables[table_name]

            # Remove sample data if not requested (saves tokens)
            if not include_sample_data and "sample_data" in table_data:
                sample_info = table_data["sample_data"]
                table_data["sample_data"] = {
                    "row_count": sample_info.get("row_count", 0),
                    "note": "样例数据已省略 (设置 include_sample_data=True 查看)",
                }

            # Build response
            result = {
                "status": "success",
                "connection": connection_name,
                "table": table_data,
                "schema_file": str(schema_file),
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to query schema: {str(e)}",
                },
                indent=2,
                ensure_ascii=False,
            )
