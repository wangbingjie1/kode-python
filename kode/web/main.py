"""
FastAPI Application Entry Point

Main web application for Kode AI coding assistant with WebSocket support.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from kode.utils.logger import setup_logger
from kode.utils.config import ConfigManager

# Setup logger
logger = setup_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Kode AI Coding Assistant",
    description="AI-native coding assistant with web interface",
    version="0.2.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Kode Web Service...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create default user and project if they don't exist
    await create_default_data()
    logger.info("Default data initialized")

    # Load persisted database connections
    from kode.services.database_manager import db_manager
    from kode.database.session import SessionLocal

    db_session = SessionLocal()
    try:
        count = db_manager.load_connections_from_db(db_session)
        if count > 0:
            logger.info(f"Loaded {count} persisted database connections")
    except Exception as e:
        logger.warning(f"Could not load database connections: {e}")
    finally:
        db_session.close()

    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.get_all()

    logger.info(f"Loaded configuration with model: {config.get('models', {}).get('main')}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Kode Web Service...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Kode AI Coding Assistant",
        "version": "0.2.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    config_manager = ConfigManager()
    config = config_manager.get_all()

    # Remove sensitive data
    safe_config = {
        "models": config.get("models", {}),
        "modelPointers": config.get("modelPointers", {}),
        "verbose": config.get("verbose", False),
        "maxTokens": config.get("maxTokens", 4096),
        "temperature": config.get("temperature", 0.7),
    }

    return safe_config


# Import routers
from kode.web.api import chat, project, sse, database
from kode.database.session import init_db, async_session_maker
from kode.models import User, Project
from sqlalchemy import select

# Register routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(project.router, prefix="/api", tags=["projects"])
app.include_router(sse.router, prefix="/api/sse", tags=["sse"])
app.include_router(database.router, prefix="/api/database", tags=["database"])


async def create_default_data():
    """Create default user and project if they don't exist"""
    async with async_session_maker() as db:
        try:
            # Check if default user exists
            result = await db.execute(select(User).where(User.id == "default"))
            user = result.scalar_one_or_none()

            if not user:
                # Create default user
                user = User(
                    id="default",
                    username="default",
                    email="default@kode.local",
                    hashed_password="default",  # Placeholder password for demo
                )
                db.add(user)
                logger.info("Created default user")

            # Check if default project exists
            result = await db.execute(select(Project).where(Project.id == "default"))
            project = result.scalar_one_or_none()

            if not project:
                # Create default project
                project = Project(
                    id="default",
                    name="默认项目",
                    description="默认工作空间",
                    user_id="default",
                    config={},
                )
                db.add(project)
                logger.info("Created default project")

            await db.commit()

        except Exception as e:
            logger.error(f"Error creating default data: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    import uvicorn
    import sys

    # 修复 Windows 下 multiprocessing 的问题
    if sys.platform == "win32":
        import multiprocessing
        multiprocessing.freeze_support()

    uvicorn.run(
        "kode.web.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=["kode"],  # 只监控 kode 目录
        log_level="info",
    )
