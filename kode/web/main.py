"""
FastAPI Application Entry Point

Main web application for Kode AI coding assistant with WebSocket support.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os

from kode.utils.logger import setup_logger
from kode.utils.config import ConfigManager
from kode.web.middleware.locale import LocaleMiddleware

# Setup logger
logger = setup_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Kode AI Coding Assistant",
    description="AI-native coding assistant with web interface",
    version="0.2.0",
)

# CORS configuration - secure by default
# For production, set ALLOWED_ORIGINS environment variable
# Example: ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []

# Development mode fallback - only allow localhost
if not allowed_origins:
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:8001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8001",
    ]
    logger.warning(
        "ALLOWED_ORIGINS not set - using development defaults (localhost only). "
        "For production, set ALLOWED_ORIGINS environment variable."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Accept-Language"],
)

# Locale middleware (for i18n support)
app.add_middleware(LocaleMiddleware)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Kode Web Service...")

    # Validate required environment variables
    is_production = os.getenv("ENVIRONMENT", "").lower() == "production"

    # Check for required API keys
    has_anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    has_openai_key = bool(os.getenv("OPENAI_API_KEY"))

    if not has_anthropic_key and not has_openai_key:
        logger.error(
            "CRITICAL: No AI API keys found. "
            "Set either ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable."
        )
        if is_production:
            raise RuntimeError(
                "At least one AI API key (ANTHROPIC_API_KEY or OPENAI_API_KEY) must be set in production"
            )
        else:
            logger.warning("Continuing in development mode without AI API keys - AI features will not work")

    # Validate SECRET_KEY (already checked during import of security.py, but log it)
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        logger.error("SECRET_KEY not set - this should have been caught earlier")
    elif secret_key == "kode-secret-key-change-in-production":
        logger.error("CRITICAL: Using default SECRET_KEY value")
        if is_production:
            raise RuntimeError("SECRET_KEY must be changed from default value in production")

    # Check ENCRYPTION_KEY for database password encryption
    if not os.getenv("ENCRYPTION_KEY") and not secret_key:
        logger.error("Neither ENCRYPTION_KEY nor SECRET_KEY is set - cannot encrypt database passwords")
        if is_production:
            raise RuntimeError("ENCRYPTION_KEY or SECRET_KEY must be set for secure password encryption")

    # Warn about CORS in production
    if is_production and not os.getenv("ALLOWED_ORIGINS"):
        logger.warning(
            "Production mode without ALLOWED_ORIGINS set - "
            "using default localhost origins which is likely incorrect for production"
        )

    logger.info("Environment validation complete")

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
from kode.web.api import chat, project, sse, database, auth, billing
from kode.database.session import init_db, async_session_maker
from kode.models import User, Project, Plan
from sqlalchemy import select

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(project.router, prefix="/api", tags=["projects"])
app.include_router(sse.router, prefix="/api/sse", tags=["sse"])
app.include_router(database.router, prefix="/api/database", tags=["database"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])


async def create_default_data():
    """Create default user, project, and plans if they don't exist"""
    async with async_session_maker() as db:
        try:
            # Check if default user exists
            result = await db.execute(select(User).where(User.id == "default"))
            user = result.scalar_one_or_none()

            # Only create default user in development environment
            # In production, users must register properly
            is_production = os.getenv("ENVIRONMENT", "").lower() == "production"

            if not user:
                # Import here to avoid circular dependency
                from kode.core.security import hash_password
                import secrets

                if not is_production:
                    # Development mode - create default user with random password
                    random_password = secrets.token_urlsafe(16)

                    user = User(
                        id="default",
                        username="default",
                        email="default@kode.local",
                        hashed_password=hash_password(random_password),
                    )
                    db.add(user)
                    logger.warning(
                        f"Created default user for development. "
                        f"Username: default, Password: {random_password}"
                    )
                    logger.warning(
                        "IMPORTANT: Default user is disabled in production. "
                        "Set ENVIRONMENT=production to disable this."
                    )
                else:
                    # Production mode - create system user only
                    logger.info(
                        "Production mode - skipping default user creation. "
                        "Users must register through the API."
                    )
                    user = User(
                        id="system",
                        username="system",
                        email="system@kode.local",
                        hashed_password=hash_password(secrets.token_urlsafe(32)),
                    )
                    db.add(user)
                    logger.info("Created system user")

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

            # Create default plans (类似 Cursor 的套餐体系)
            result = await db.execute(select(Plan).where(Plan.name == "free"))
            if not result.scalar_one_or_none():
                free_plan = Plan(
                    name="free",
                    display_name="免费版",
                    description="体验 AI 助手的基础功能",
                    price=0.0,
                    billing_period="monthly",
                    token_quota=100000,  # 10万 tokens/月
                    message_quota=50,  # 50 条消息/月
                    conversation_quota=3,  # 3 个对话
                    database_connection_quota=0,
                    database_access=False,
                    advanced_analysis=False,
                    ontology_building=False,
                    priority_support=False,
                    sort_order=1,
                )
                db.add(free_plan)
                logger.info("Created Free plan")

            result = await db.execute(select(Plan).where(Plan.name == "pro"))
            if not result.scalar_one_or_none():
                pro_plan = Plan(
                    name="pro",
                    display_name="专业版",
                    description="适合个人开发者和小团队",
                    price=99.0,  # 99元/月
                    billing_period="monthly",
                    token_quota=2000000,  # 200万 tokens/月
                    message_quota=1000,  # 1000 条消息/月
                    conversation_quota=50,  # 50 个对话
                    database_connection_quota=5,  # 5 个数据库连接
                    database_access=True,
                    advanced_analysis=True,
                    ontology_building=True,
                    priority_support=False,
                    sort_order=2,
                )
                db.add(pro_plan)
                logger.info("Created Pro plan")

            result = await db.execute(select(Plan).where(Plan.name == "enterprise"))
            if not result.scalar_one_or_none():
                enterprise_plan = Plan(
                    name="enterprise",
                    display_name="企业版",
                    description="适合大型团队和企业客户",
                    price=499.0,  # 499元/月
                    billing_period="monthly",
                    token_quota=10000000,  # 1000万 tokens/月
                    message_quota=10000,  # 10000 条消息/月
                    conversation_quota=500,  # 500 个对话
                    database_connection_quota=50,  # 50 个数据库连接
                    database_access=True,
                    advanced_analysis=True,
                    ontology_building=True,
                    priority_support=True,
                    features={
                        "custom_model": True,
                        "api_access": True,
                        "dedicated_support": True,
                    },
                    sort_order=3,
                )
                db.add(enterprise_plan)
                logger.info("Created Enterprise plan")

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
