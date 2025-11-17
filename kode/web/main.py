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
from kode.web.middleware.quota_check import QuotaCheckMiddleware

# Setup logger
logger = setup_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Kode AI Coding Assistant",
    description="AI-native coding assistant with web interface",
    version="0.2.0",
)

# CORS middleware - 使用环境变量配置允许的源
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
logger.info(f"CORS allowed origins: {CORS_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Quota check middleware (配额检查)
app.add_middleware(QuotaCheckMiddleware)

# Locale middleware (for i18n support)
app.add_middleware(LocaleMiddleware)


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
from kode.web.api import chat, project, sse, database, auth, billing, uncertainty
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
app.include_router(uncertainty.router, prefix="/api/uncertainty", tags=["uncertainty"])


async def create_default_data():
    """Create default user, project, and plans if they don't exist"""
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

            # Create default plans（纯 token 计费模式）
            result = await db.execute(select(Plan).where(Plan.name == "free"))
            if not result.scalar_one_or_none():
                free_plan = Plan(
                    name="free",
                    display_name="免费版",
                    description="体验 AI 助手的基础功能（按 Token 计费）",
                    price=0.0,
                    billing_period="monthly",
                    token_quota=100000,  # 【计费依据】10万 tokens/月
                    database_connection_quota=0,  # 【硬限制】基础设施限制
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
                    description="适合个人开发者和小团队（按 Token 计费）",
                    price=99.0,  # 99元/月
                    billing_period="monthly",
                    token_quota=2000000,  # 【计费依据】200万 tokens/月
                    database_connection_quota=5,  # 【硬限制】5 个数据库连接
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
                    description="适合大型团队和企业客户（按 Token 计费）",
                    price=499.0,  # 499元/月
                    billing_period="monthly",
                    token_quota=10000000,  # 【计费依据】1000万 tokens/月
                    database_connection_quota=50,  # 【硬限制】50 个数据库连接
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
        reload=False,
        reload_dirs=["kode"],  # 只监控 kode 目录
        log_level="info",
    )
