#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为现有用户分配免费订阅"""

import asyncio
import sys
from pathlib import Path
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from kode.database.session import async_session_maker
from kode.models import User, Plan, Subscription, Usage, SubscriptionStatus
from sqlalchemy import select
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def assign_subscriptions():
    """为所有用户分配免费订阅"""
    async with async_session_maker() as db:
        # 获取免费套餐
        result = await db.execute(select(Plan).where(Plan.name == "free"))
        free_plan = result.scalar_one_or_none()

        if not free_plan:
            print("❌ 未找到免费套餐")
            return

        print(f"✓ 找到免费套餐: {free_plan.display_name} (ID: {free_plan.id})")

        # 获取所有用户
        result = await db.execute(select(User))
        users = result.scalars().all()

        print(f"\n共找到 {len(users)} 个用户\n")

        assigned_count = 0
        for user in users:
            # 检查用户是否已有订阅
            result = await db.execute(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            existing_sub = result.scalar_one_or_none()

            if existing_sub:
                print(f"跳过: {user.username} - 已有订阅")
                continue

            # 创建免费订阅
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=365 * 10)  # 10年有效期

            subscription = Subscription(
                user_id=user.id,
                plan_id=free_plan.id,
                status=SubscriptionStatus.ACTIVE,
                start_date=start_date,
                end_date=end_date,
                auto_renew=False,
            )

            db.add(subscription)
            await db.flush()  # 刷新以获取subscription.id

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

            print(f"✓ 为 {user.username} ({user.email}) 分配免费订阅")

        await db.commit()

        print(f"\n{'=' * 60}")
        print(f"✓ 成功为 {assigned_count} 个用户分配免费订阅")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(assign_subscriptions())
