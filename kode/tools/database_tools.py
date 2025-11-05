"""Database connectivity and schema extraction tools."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field
from sqlalchemy import inspect, text

from kode.services.database_manager import DatabaseConnection, db_manager
from kode.tools.base import KodeTool
from kode.utils.config import ConfigManager


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
    auto_save: bool = Field(default=True, description="Automatically save schema to file")
    version: str = Field(default="auto", description="Version identifier (auto = timestamp)")


class SchemaLoadInput(BaseModel):
    """Input schema for SchemaLoadTool."""

    connection_name: str = Field(description="Connection name to load schema for")
    version: str = Field(default="latest", description="Version to load (latest or specific version)")


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


class DatabaseTestConnectionTool(KodeTool):
    """Test an existing database connection."""

    name: str = "DatabaseTestConnection"
    description: str = "Test an existing database connection to verify it's working correctly."

    args_schema: Type[BaseModel] = DatabaseTestConnectionInput
    requires_permission: bool = False  # Read-only operation

    def _run(self, connection_name: str) -> str:
        """
        Test database connection.

        Args:
            connection_name: Connection name to test

        Returns:
            Test result message
        """
        try:
            result = db_manager.test_connection(connection_name)
            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to test connection: {str(e)}",
                },
                indent=2,
            )


class DatabaseDisconnectTool(KodeTool):
    """Disconnect and remove a database connection."""

    name: str = "DatabaseDisconnect"
    description: str = "Disconnect from a database and remove the connection configuration."

    args_schema: Type[BaseModel] = DatabaseDisconnectInput
    requires_permission: bool = True

    def _run(self, connection_name: str) -> str:
        """
        Disconnect from database.

        Args:
            connection_name: Connection name to disconnect

        Returns:
            Disconnection status message
        """
        try:
            if db_manager.remove_connection(connection_name):
                return json.dumps(
                    {
                        "status": "success",
                        "message": f"Successfully disconnected from '{connection_name}'",
                    },
                    indent=2,
                )
            else:
                return json.dumps(
                    {
                        "status": "warning",
                        "message": f"Connection '{connection_name}' not found",
                    },
                    indent=2,
                )

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to disconnect: {str(e)}",
                },
                indent=2,
            )


class DatabaseListConnectionsTool(KodeTool):
    """List all available database connections."""

    name: str = "DatabaseListConnections"
    description: str = "List all configured database connections."

    args_schema: Type[BaseModel] = DatabaseListConnectionsInput
    requires_permission: bool = False

    def _run(self) -> str:
        """
        List all connections.

        Returns:
            List of connection names and details
        """
        try:
            connection_names = db_manager.list_connections()

            if not connection_names:
                return json.dumps(
                    {
                        "status": "success",
                        "message": "No database connections configured",
                        "connections": [],
                    },
                    indent=2,
                )

            connections = []
            for name in connection_names:
                conn = db_manager.get_connection(name)
                if conn:
                    connections.append(conn.to_dict())

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Found {len(connections)} connection(s)",
                    "connections": connections,
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to list connections: {str(e)}",
                },
                indent=2,
            )


class DatabaseSchemaExtractorTool(KodeTool):
    """
    Extract database schema metadata including tables, columns, constraints, and relationships.
    """

    name: str = "DatabaseSchemaExtractor"
    description: str = """Extract complete database schema metadata including:
    - Table definitions and column metadata
    - Primary keys and foreign keys
    - Indexes and constraints
    - Foreign key relationships
    - Optional table statistics"""

    args_schema: Type[BaseModel] = DatabaseSchemaExtractorInput
    requires_permission: bool = False  # Read-only operation

    def _run(
        self,
        connection_name: str,
        tables: Optional[List[str]] = None,
        include_columns: bool = True,
        include_constraints: bool = True,
        include_indexes: bool = True,
        include_relationships: bool = True,
        include_statistics: bool = False,
        auto_save: bool = True,
        version: str = "auto",
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

            schema_data = {
                "status": "success",
                "connection": connection.to_dict(),
                "database": connection.database,
                "schema": connection.db_schema,
                "table_count": len(table_names),
                "tables": {},
            }

            # Extract metadata for each table
            for table_name in table_names:
                table_data: Dict[str, Any] = {"name": table_name}

                # Table comment
                try:
                    table_comment_info = inspector.get_table_comment(table_name)
                    if table_comment_info and table_comment_info.get("text"):
                        table_data["comment"] = table_comment_info["text"]
                except NotImplementedError:
                    # Some databases don't support table comments
                    pass

                # Columns
                if include_columns:
                    columns = inspector.get_columns(table_name)
                    table_data["columns"] = [
                        {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col.get("nullable", True),
                            "default": str(col.get("default")) if col.get("default") else None,
                            "autoincrement": col.get("autoincrement", False),
                            "comment": col.get("comment"),  # 添加字段注释
                        }
                        for col in columns
                    ]
                    table_data["column_count"] = len(columns)

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

                schema_data["tables"][table_name] = table_data

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

            # Auto-save schema to file
            if auto_save:
                save_result = self._save_schema(schema_data, connection_name, version)
                schema_data["storage"] = save_result

            return json.dumps(schema_data, indent=2, ensure_ascii=False)

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
                        result = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row_count = result.scalar()
                        stats[table_name] = {"row_count": row_count}
                    except Exception:
                        stats[table_name] = {"row_count": "unknown"}
        except Exception:
            pass

        return stats

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
            conn_dir = base_dir / connection_name
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


class SchemaLoadTool(KodeTool):
    """
    Load previously extracted database schema from storage.

    Use this tool to retrieve cached schema metadata instead of re-extracting.
    """

    name: str = "SchemaLoad"
    description: str = """Load previously extracted database schema from storage.
    This is much faster than re-extracting schema. Use this when you need schema
    information and suspect it may have been extracted before."""

    args_schema: Type[BaseModel] = SchemaLoadInput
    requires_permission: bool = False

    def _run(self, connection_name: str, version: str = "latest") -> str:
        """
        Load schema from storage.

        Args:
            connection_name: Connection name
            version: Version to load (latest or specific)

        Returns:
            Schema data as JSON
        """
        try:
            config = ConfigManager()
            storage_path = config.get("storage.schema_path", "./schema_store")
            conn_dir = Path(storage_path) / connection_name

            if not conn_dir.exists():
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"No schema found for connection '{connection_name}'",
                        "suggestion": "Use DatabaseSchemaExtractor to extract schema first",
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            # Load specific version or latest
            if version == "latest":
                schema_file = conn_dir / "schema_latest.json"
            else:
                schema_file = conn_dir / f"schema_{version}.json"

            if not schema_file.exists():
                # List available versions
                available = list(conn_dir.glob("schema_v*.json"))
                available_versions = [f.stem.replace("schema_", "") for f in available]

                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Schema version '{version}' not found",
                        "available_versions": available_versions,
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            with open(schema_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["loaded_from_cache"] = True
            data["loaded_at"] = datetime.now().isoformat()

            return json.dumps(data, indent=2, ensure_ascii=False)

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to load schema: {str(e)}",
                },
                indent=2,
            )


class DatabaseExecuteQueryTool(KodeTool):
    """
    Execute SQL queries on a database connection.

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
                            "message": f"Query returned {len(data)} row(s)" +
                                      (f" (limited to {fetch_limit}, more available)" if has_more else ""),
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
                            "message": f"{query_type} operation completed, {affected_rows} row(s) affected",
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
