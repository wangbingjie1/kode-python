"""Database connection manager service."""

import asyncio
from typing import Any, Dict, Optional, List
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import Session

from kode.core.security import encrypt_db_password, decrypt_db_password


class DatabaseConnection:
    """Represents a database connection configuration."""

    def __init__(
        self,
        name: str,
        db_type: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        db_schema: Optional[str] = None,
        ssl: bool = False,
        **kwargs: Any,
    ):
        """
        Initialize database connection configuration.

        Args:
            name: Unique connection identifier
            db_type: Database type (postgresql, mysql, sqlserver, oracle, sqlite)
            host: Database host
            port: Database port
            database: Database name
            username: Username
            password: Password
            db_schema: Default schema (optional)
            ssl: Use SSL connection
            **kwargs: Additional connection parameters
        """
        self.name = name
        self.db_type = db_type.lower()
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.db_schema = db_schema
        self.ssl = ssl
        self.extra_params = kwargs

    def get_connection_url(self, async_mode: bool = False) -> str:
        """
        Generate SQLAlchemy connection URL.

        Args:
            async_mode: Use async driver if True

        Returns:
            SQLAlchemy connection URL
        """
        # Encode password to handle special characters
        encoded_password = quote_plus(self.password)

        if self.db_type == "postgresql":
            driver = "asyncpg" if async_mode else "psycopg2"
            url = (
                f"postgresql+{driver}://{self.username}:{encoded_password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
            if self.ssl:
                url += "?ssl=require"

        elif self.db_type == "mysql":
            driver = "aiomysql" if async_mode else "pymysql"
            url = (
                f"mysql+{driver}://{self.username}:{encoded_password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
            if self.ssl:
                url += "?ssl=true"

        elif self.db_type == "sqlite":
            if async_mode:
                url = f"sqlite+aiosqlite:///{self.database}"
            else:
                url = f"sqlite:///{self.database}"

        elif self.db_type == "sqlserver":
            driver = "pyodbc"
            url = (
                f"mssql+{driver}://{self.username}:{encoded_password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
            if self.ssl:
                url += "?encrypt=yes"

        elif self.db_type == "oracle":
            driver = "cx_oracle"
            url = (
                f"oracle+{driver}://{self.username}:{encoded_password}"
                f"@{self.host}:{self.port}/?service_name={self.database}"
            )

        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

        return url

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without password)."""
        return {
            "name": self.name,
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "db_schema": self.db_schema,
            "ssl": self.ssl,
        }


class DatabaseConnectionManager:
    """
    Manages database connections and connection pools.

    Singleton pattern to ensure centralized connection management.
    """

    _instance: Optional["DatabaseConnectionManager"] = None
    _connections: Dict[str, DatabaseConnection] = {}
    _engines: Dict[str, Engine] = {}
    _async_engines: Dict[str, AsyncEngine] = {}

    def __new__(cls) -> "DatabaseConnectionManager":
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def add_connection(self, connection: DatabaseConnection) -> None:
        """
        Add a new database connection configuration.

        Args:
            connection: DatabaseConnection instance
        """
        if connection.name in self._connections:
            raise ValueError(f"Connection '{connection.name}' already exists")

        self._connections[connection.name] = connection

    def remove_connection(self, name: str) -> bool:
        """
        Remove a database connection from memory (does not close engines).
        Use close_connection_async() before calling this in async context.

        Args:
            name: Connection name

        Returns:
            True if removed, False if not found
        """
        if name in self._connections:
            del self._connections[name]
            return True
        return False

    def get_connection(self, name: str) -> Optional[DatabaseConnection]:
        """
        Get connection configuration by name.

        Args:
            name: Connection name

        Returns:
            DatabaseConnection or None
        """
        return self._connections.get(name)

    def list_connections(self) -> list[str]:
        """List all connection names."""
        return list(self._connections.keys())

    def get_engine(self, name: str, create_if_missing: bool = True) -> Optional[Engine]:
        """
        Get or create synchronous SQLAlchemy engine.

        Args:
            name: Connection name
            create_if_missing: Create engine if not exists

        Returns:
            SQLAlchemy Engine or None
        """
        if name in self._engines:
            return self._engines[name]

        if not create_if_missing:
            return None

        connection = self._connections.get(name)
        if not connection:
            raise ValueError(f"Connection '{name}' not found")

        url = connection.get_connection_url(async_mode=False)
        engine = create_engine(url, pool_pre_ping=True, echo=False)
        self._engines[name] = engine
        return engine

    def get_async_engine(
        self, name: str, create_if_missing: bool = True
    ) -> Optional[AsyncEngine]:
        """
        Get or create asynchronous SQLAlchemy engine.

        Args:
            name: Connection name
            create_if_missing: Create engine if not exists

        Returns:
            Async SQLAlchemy Engine or None
        """
        if name in self._async_engines:
            return self._async_engines[name]

        if not create_if_missing:
            return None

        connection = self._connections.get(name)
        if not connection:
            raise ValueError(f"Connection '{name}' not found")

        url = connection.get_connection_url(async_mode=True)
        engine = create_async_engine(url, pool_pre_ping=True, echo=False)
        self._async_engines[name] = engine
        return engine

    def test_connection(self, name: str) -> Dict[str, Any]:
        """
        Test database connection.

        Args:
            name: Connection name

        Returns:
            Dict with status and details
        """
        try:
            engine = self.get_engine(name)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            return {
                "status": "success",
                "message": f"Successfully connected to '{name}'",
                "connection": self._connections[name].to_dict(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to connect to '{name}': {str(e)}",
                "error": str(e),
            }

    async def test_connection_async(self, name: str) -> Dict[str, Any]:
        """
        Test database connection asynchronously.

        Args:
            name: Connection name

        Returns:
            Dict with status and details
        """
        try:
            engine = self.get_async_engine(name)
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()

            return {
                "status": "success",
                "message": f"Successfully connected to '{name}'",
                "connection": self._connections[name].to_dict(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to connect to '{name}': {str(e)}",
                "error": str(e),
            }

    def close_connection(self, name: str) -> None:
        """
        Close and remove connection engines (sync only).

        Args:
            name: Connection name
        """
        # Close sync engine
        if name in self._engines:
            self._engines[name].dispose()
            del self._engines[name]

        # For async engines, just remove from dict without disposing
        # Use close_connection_async() for proper async disposal
        if name in self._async_engines:
            del self._async_engines[name]

    async def close_connection_async(self, name: str) -> None:
        """
        Close and remove connection engines (async version).

        Args:
            name: Connection name
        """
        # Close sync engine
        if name in self._engines:
            self._engines[name].dispose()
            del self._engines[name]

        # Close async engine properly in async context
        if name in self._async_engines:
            await self._async_engines[name].dispose()
            del self._async_engines[name]

    def close_all(self) -> None:
        """Close all database connections."""
        connection_names = list(self._engines.keys()) + list(self._async_engines.keys())
        for name in set(connection_names):
            self.close_connection(name)

    def get_inspector(self, name: str):
        """
        Get SQLAlchemy inspector for schema introspection.

        Args:
            name: Connection name

        Returns:
            SQLAlchemy Inspector instance
        """
        engine = self.get_engine(name)
        return inspect(engine)

    def load_connections_from_db(self, db_session: Session) -> int:
        """
        Load all database connections from persistence storage.

        Args:
            db_session: SQLAlchemy session

        Returns:
            Number of connections loaded
        """
        from kode.models.database_connection import DatabaseConnectionModel

        try:
            # Query all connection records
            connection_models = db_session.query(DatabaseConnectionModel).all()

            count = 0
            for model in connection_models:
                # Skip if already loaded in memory
                if model.name in self._connections:
                    continue

                # Create DatabaseConnection object from model
                try:
                    decrypted_password = decrypt_db_password(model.password)
                except Exception as e:
                    # 如果解密失败，可能是旧数据（明文），直接使用
                    decrypted_password = model.password

                connection = DatabaseConnection(
                    name=model.name,
                    db_type=model.db_type,
                    host=model.host,
                    port=model.port,
                    database=model.database,
                    username=model.username,
                    password=decrypted_password,
                    db_schema=model.db_schema,
                    ssl=model.ssl,
                )

                self._connections[model.name] = connection
                count += 1

            return count

        except Exception as e:
            # If the table doesn't exist yet, just return 0
            return 0

    def save_connection_to_db(
        self, db_session: Session, connection: DatabaseConnection
    ) -> bool:
        """
        Save a database connection to persistence storage.

        Args:
            db_session: SQLAlchemy session
            connection: DatabaseConnection to save

        Returns:
            True if saved successfully
        """
        from kode.models.database_connection import DatabaseConnectionModel

        try:
            # Check if connection already exists
            existing = (
                db_session.query(DatabaseConnectionModel)
                .filter(DatabaseConnectionModel.name == connection.name)
                .first()
            )

            if existing:
                # Update existing connection
                existing.db_type = connection.db_type
                existing.host = connection.host
                existing.port = connection.port
                existing.database = connection.database
                existing.username = connection.username
                existing.password = encrypt_db_password(connection.password)
                existing.db_schema = connection.db_schema
                existing.ssl = connection.ssl
            else:
                # Create new connection record
                new_connection = DatabaseConnectionModel(
                    name=connection.name,
                    db_type=connection.db_type,
                    host=connection.host,
                    port=connection.port,
                    database=connection.database,
                    username=connection.username,
                    password=encrypt_db_password(connection.password),
                    db_schema=connection.db_schema,
                    ssl=connection.ssl,
                )
                db_session.add(new_connection)

            db_session.commit()
            return True

        except Exception as e:
            db_session.rollback()
            raise e

    def delete_connection_from_db(self, db_session: Session, name: str) -> bool:
        """
        Delete a database connection from persistence storage.

        Args:
            db_session: SQLAlchemy session
            name: Connection name

        Returns:
            True if deleted successfully
        """
        from kode.models.database_connection import DatabaseConnectionModel

        try:
            connection_model = (
                db_session.query(DatabaseConnectionModel)
                .filter(DatabaseConnectionModel.name == name)
                .first()
            )

            if connection_model:
                db_session.delete(connection_model)
                db_session.commit()
                return True

            return False

        except Exception as e:
            db_session.rollback()
            raise e


# Global singleton instance
db_manager = DatabaseConnectionManager()
