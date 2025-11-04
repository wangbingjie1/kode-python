"""Database connectivity and schema extraction tools."""

import json
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field
from sqlalchemy import inspect

from kode.services.database_manager import DatabaseConnection, db_manager
from kode.tools.base import KodeTool


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

            return json.dumps(schema_data, indent=2)

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
