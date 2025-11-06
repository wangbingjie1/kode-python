#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加商业化模块

创建 plans, subscriptions, usage 表
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kode.database.session import engine, Base, async_session_maker
from kode.models import Plan, Subscription, Usage
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_billing_tables():
    """创建商业化相关表"""
    logger.info("Creating billing tables...")

    async with engine.begin() as conn:
        # 只创建商业化相关的表
        await conn.run_sync(Plan.__table__.create, checkfirst=True)
        await conn.run_sync(Subscription.__table__.create, checkfirst=True)
        await conn.run_sync(Usage.__table__.create, checkfirst=True)

    logger.info("✓ Billing tables created successfully")


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
            ),
            Plan(
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
            ),
        ]

        for plan in plans:
            db.add(plan)

        await db.commit()
        logger.info(f"✓ Created {len(plans)} default plans")


async def assign_default_subscriptions():
    """为现有用户分配默认免费订阅"""
    from kode.models import User
    from datetime import datetime, timedelta
    from kode.models import SubscriptionStatus

    logger.info("Assigning default subscriptions to existing users...")

    async with async_session_maker() as db:
        # 获取免费套餐
        result = await db.execute(select(Plan).where(Plan.name == "free"))
        free_plan = result.scalar_one_or_none()

        if not free_plan:
            logger.error("Free plan not found! Please run create_default_plans first.")
            return

        # 获取所有用户
        result = await db.execute(select(User))
        users = result.scalars().all()

        if not users:
            logger.info("No users found, skipping subscription assignment")
            return

        assigned_count = 0
        for user in users:
            # 检查用户是否已有订阅
            result = await db.execute(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            existing_sub = result.scalar_one_or_none()

            if existing_sub:
                logger.info(f"User {user.username} already has a subscription")
                continue

            # 创建免费订阅
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=365 * 10)  # 免费版有效期 10 年

            subscription = Subscription(
                user_id=user.id,
                plan_id=free_plan.id,
                status=SubscriptionStatus.ACTIVE,
                start_date=start_date,
                end_date=end_date,
                auto_renew=False,
            )

            db.add(subscription)

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
            assigned_count += 1

        await db.commit()
        logger.info(f"✓ Assigned free subscriptions to {assigned_count} users")


async def main():
    """运行迁移"""
    logger.info("=" * 60)
    logger.info("Starting billing module migration")
    logger.info("=" * 60)

    try:
        # 1. 创建表
        await create_billing_tables()

        # 2. 创建默认套餐
        await create_default_plans()

        # 3. 为现有用户分配免费订阅
        await assign_default_subscriptions()

        logger.info("=" * 60)
        logger.info("✓ Migration completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"✗ Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
