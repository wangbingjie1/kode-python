"""
Database Session Management

Provides async SQLAlchemy session for database operations.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import AsyncGenerator
import os
from dotenv import load_dotenv

# Load environment variables from .env file (override existing values)
load_dotenv(override=True)

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./kode.db"  # Async SQLite
)

# Sync database URL for sync operations (like connection persistence)
# Convert async driver to sync driver for synchronous operations
def get_sync_url(async_url: str) -> str:
    """Convert async database URL to sync URL"""
    if "mysql+aiomysql" in async_url:
        return async_url.replace("mysql+aiomysql", "mysql+pymysql")
    elif "postgresql+asyncpg" in async_url:
        return async_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    elif "sqlite+aiosqlite" in async_url:
        return async_url.replace("sqlite+aiosqlite", "sqlite")
    return async_url

SYNC_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    get_sync_url(DATABASE_URL)
)

# Create async engine with connection pool settings
# MySQL-specific pool configuration for better stability
pool_config = {
    "pool_pre_ping": True,  # Test connections before using them
    "pool_recycle": 3600,   # Recycle connections after 1 hour
    "pool_size": 10,        # Connection pool size
    "max_overflow": 20,     # Max overflow connections
    "echo_pool": False,     # Pool debug logging
}

# Add MySQL-specific settings if using MySQL
if "mysql" in DATABASE_URL:
    # aiomysql 支持的连接参数
    pool_config.update({
        "connect_args": {
            "connect_timeout": 10,        # Connection timeout (seconds)
            "charset": "utf8mb4",
            "autocommit": False,
        }
    })

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    future=True,
    **pool_config
)

# Create sync engine for sync operations with same pool config
sync_pool_config = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "pool_size": 10,
    "max_overflow": 20,
}

if "mysql" in SYNC_DATABASE_URL:
    # pymysql 支持的连接参数
    sync_pool_config.update({
        "connect_args": {
            "connect_timeout": 10,
            "read_timeout": 30,           # pymysql 支持 read_timeout
            "write_timeout": 30,          # pymysql 支持 write_timeout
            "charset": "utf8mb4",
        }
    })

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    **sync_pool_config
)

# Create async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Create sync session maker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)

# Base class for ORM models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.

    Usage in FastAPI:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Also create tables for sync engine
    Base.metadata.create_all(bind=sync_engine)


async def drop_db():
    """Drop all database tables (use with caution!)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
