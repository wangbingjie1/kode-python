#!/usr/bin/env python3
"""
完整初始化数据库
创建所有表并添加默认数据
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from kode.database.session import engine, Base, async_session_maker
from kode.models import User, Plan, Subscription, Usage, Project, Conversation, Message
from sqlalchemy import select
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_all_tables():
    """创建所有表"""
    logger.info("Creating all tables...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("✓ All tables created successfully")


async def create_default_user():
    """创建默认用户"""
    logger.info("Creating default user...")

    async with async_session_maker() as db:
        # 检查是否已有用户
        result = await db.execute(select(User))
        existing_users = result.scalars().all()

        if existing_users:
            logger.info(f"✓ Users already exist ({len(existing_users)} found)")
            return existing_users[0]

        # 创建默认用户
        user = User(
            username="admin",
            email="admin@example.com",
            hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GHQ.iJYh7Kiu",  # password: admin123
            is_active=True,
            auth_provider="local",
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"✓ Created default user: {user.username}")
        return user


async def create_default_plans():
    """创建默认套餐"""
    logger.info("Creating default plans...")

    async with async_session_maker() as db:
        # 检查是否已有套餐
        result = await db.execute(select(Plan))
        existing_plans = result.scalars().all()

        if existing_plans:
            logger.info(f"✓ Plans already exist ({len(existing_plans)} plans found)")
            return

        # 创建三个默认套餐
        plans = [
            Plan(
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
            ),
            Plan(
                name="pro",
                display_name="专业版",
                description="适合个人开发者和小团队",
                price=99.0,
                billing_period="monthly",
                token_quota=2000000,  # 200万 tokens/月
                message_quota=1000,
                conversation_quota=50,
                database_connection_quota=5,
                database_access=True,
                advanced_analysis=True,
                ontology_building=True,
                priority_support=False,
                sort_order=2,
            ),
            Plan(
                name="enterprise",
                display_name="企业版",
                description="适合大型团队和企业客户",
                price=499.0,
                billing_period="monthly",
                token_quota=10000000,  # 1000万 tokens/月
                message_quota=10000,
                conversation_quota=500,
                database_connection_quota=50,
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
            ),
        ]

        for plan in plans:
            db.add(plan)

        await db.commit()
        logger.info(f"✓ Created {len(plans)} default plans")


async def assign_default_subscription(user: User):
    """为用户分配默认免费订阅"""
    from kode.models import SubscriptionStatus

    logger.info(f"Assigning default subscription to user {user.username}...")

    async with async_session_maker() as db:
        # 获取免费套餐
        result = await db.execute(select(Plan).where(Plan.name == "free"))
        free_plan = result.scalar_one_or_none()

        if not free_plan:
            logger.error("Free plan not found!")
            return

        # 检查用户是否已有订阅
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        existing_sub = result.scalar_one_or_none()

        if existing_sub:
            logger.info(f"✓ User {user.username} already has a subscription")
            return

        # 创建免费订阅
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=365 * 10)

        subscription = Subscription(
            user_id=user.id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
            start_date=start_date,
            end_date=end_date,
            auto_renew=False,
        )

        db.add(subscription)
        await db.flush()

        # 创建使用量记录
        usage = Usage(
            user_id=user.id,
            subscription_id=subscription.id,
            period_start=start_date,
            period_end=end_date,
            token_count=0,
            message_count=0,
            conversation_count=0,
            database_query_count=0,
        )

        db.add(usage)
        await db.commit()

        logger.info(f"✓ Assigned free subscription to {user.username}")


async def main():
    """运行完整初始化"""
    logger.info("=" * 60)
    logger.info("Starting database initialization")
    logger.info("=" * 60)

    try:
        # 1. 创建所有表
        await create_all_tables()

        # 2. 创建默认用户
        user = await create_default_user()

        # 3. 创建默认套餐
        await create_default_plans()

        # 4. 为用户分配免费订阅
        await assign_default_subscription(user)

        logger.info("=" * 60)
        logger.info("✓ Database initialization completed successfully!")
        logger.info("=" * 60)
        logger.info(f"\nDefault user credentials:")
        logger.info(f"  Username: admin")
        logger.info(f"  Password: admin123")

    except Exception as e:
        logger.error(f"✗ Initialization failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
