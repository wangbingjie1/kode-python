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

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    future=True,
)

# Create sync engine for sync operations
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
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
