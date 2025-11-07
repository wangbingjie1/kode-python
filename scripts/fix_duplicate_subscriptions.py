#!/usr/bin/env python
"""
修复重复订阅记录的脚本。

用途：
- 识别并清理数据库中同一用户拥有多条活跃订阅的情况
- 保留 end_date 最晚的订阅，将其他订阅设置为 CANCELLED

运行方式：
    python scripts/fix_duplicate_subscriptions.py

选项：
    --dry-run: 只显示会做什么，不实际修改数据库
    --verbose: 显示详细日志
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from kode.database.session import async_session_maker
from kode.models.subscription import Subscription, SubscriptionStatus


async def find_duplicate_subscriptions(db: AsyncSession) -> dict:
    """
    查找所有有重复活跃订阅的用户。

    Returns:
        dict: {user_id: [Subscription, ...]}
    """
    # 查询所有活跃订阅
    result = await db.execute(
        select(Subscription)
        .where(
            and_(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date > datetime.utcnow(),
            )
        )
        .order_by(Subscription.user_id, Subscription.end_date.desc())
    )
    subscriptions = result.scalars().all()

    # 按用户分组
    user_subscriptions = defaultdict(list)
    for sub in subscriptions:
        user_subscriptions[sub.user_id].append(sub)

    # 只保留有重复的用户
    duplicates = {
        user_id: subs for user_id, subs in user_subscriptions.items() if len(subs) > 1
    }

    return duplicates


async def fix_duplicate_subscriptions(dry_run: bool = False, verbose: bool = False):
    """
    修复重复订阅。

    保留 end_date 最晚的订阅，取消其他订阅。
    """
    async with async_session_maker() as db:
        try:
            duplicates = await find_duplicate_subscriptions(db)

            if not duplicates:
                print("✓ 未发现重复的活跃订阅")
                return

            print(f"发现 {len(duplicates)} 个用户有重复的活跃订阅:\n")

            total_cancelled = 0

            for user_id, subs in duplicates.items():
                print(f"用户 {user_id} 有 {len(subs)} 条活跃订阅:")

                # 第一条是 end_date 最晚的（已按降序排列），保留它
                keep_sub = subs[0]
                cancel_subs = subs[1:]

                print(f"  ✓ 保留: {keep_sub.id} (end_date: {keep_sub.end_date})")

                for sub in cancel_subs:
                    print(
                        f"  ✗ 取消: {sub.id} (end_date: {sub.end_date})"
                        + (" [dry-run]" if dry_run else "")
                    )

                    if not dry_run:
                        sub.status = SubscriptionStatus.CANCELLED
                        sub.auto_renew = False
                        if verbose:
                            print(
                                f"    - Stripe subscription ID: {sub.stripe_subscription_id}"
                            )
                            print(f"    - Created at: {sub.created_at}")

                    total_cancelled += 1

                print()

            if not dry_run:
                await db.commit()
                print(f"✓ 已取消 {total_cancelled} 条重复订阅")
            else:
                print(
                    f"[Dry run] 将会取消 {total_cancelled} 条重复订阅 (实际未修改)"
                )

        except Exception as e:
            print(f"✗ 执行失败: {e}")
            await db.rollback()
            raise


async def verify_no_duplicates(db: AsyncSession) -> bool:
    """验证是否还有重复订阅"""
    duplicates = await find_duplicate_subscriptions(db)
    return len(duplicates) == 0


async def main():
    parser = argparse.ArgumentParser(description="修复重复订阅记录")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只显示会做什么，不实际修改数据库",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")
    args = parser.parse_args()

    print("=" * 60)
    print("修复重复订阅脚本")
    print("=" * 60)
    print()

    if args.dry_run:
        print("⚠️  Dry run 模式 - 不会实际修改数据库\n")

    await fix_duplicate_subscriptions(dry_run=args.dry_run, verbose=args.verbose)

    # 验证
    if not args.dry_run:
        print("\n验证修复结果...")
        async with async_session_maker() as db:
            if await verify_no_duplicates(db):
                print("✓ 验证通过，没有重复订阅")
            else:
                print("✗ 验证失败，仍有重复订阅存在")


if __name__ == "__main__":
    asyncio.run(main())
