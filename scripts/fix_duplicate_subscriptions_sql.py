#!/usr/bin/env python
"""
使用 SQL 直接修复重复订阅记录。

这个脚本会：
1. 查找同一用户有多条活跃订阅的情况
2. 保留 end_date 最晚的订阅
3. 将其他订阅设置为 CANCELLED 状态

运行前请确保：
- 已备份数据库
- 在项目虚拟环境中运行: python scripts/fix_duplicate_subscriptions_sql.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from kode.database.session import async_session_maker


async def fix_duplicates():
    """修复重复订阅"""
    async with async_session_maker() as db:
        try:
            # 1. 找出所有有重复活跃订阅的用户
            find_duplicates_sql = text("""
                SELECT user_id, COUNT(*) as cnt
                FROM subscriptions
                WHERE status = 'active' AND end_date > datetime('now')
                GROUP BY user_id
                HAVING COUNT(*) > 1
            """)

            result = await db.execute(find_duplicates_sql)
            duplicate_users = result.fetchall()

            if not duplicate_users:
                print("✓ 没有发现重复的活跃订阅")
                return

            print(f"发现 {len(duplicate_users)} 个用户有重复订阅:\n")

            total_cancelled = 0

            # 2. 对每个用户，保留最新的订阅，取消其他的
            for user_id, count in duplicate_users:
                print(f"用户 {user_id} 有 {count} 条活跃订阅")

                # 获取该用户的所有活跃订阅（按 end_date 降序）
                get_subs_sql = text("""
                    SELECT id, end_date, created_at
                    FROM subscriptions
                    WHERE user_id = :user_id AND status = 'active' AND end_date > datetime('now')
                    ORDER BY end_date DESC, created_at DESC
                """)

                subs_result = await db.execute(get_subs_sql, {"user_id": user_id})
                subs = subs_result.fetchall()

                # 第一条保留，其他的取消
                keep_sub = subs[0]
                cancel_subs = subs[1:]

                print(f"  ✓ 保留: {keep_sub[0]} (end_date: {keep_sub[1]})")

                for sub in cancel_subs:
                    print(f"  ✗ 取消: {sub[0]} (end_date: {sub[1]})")

                    # 更新为 CANCELLED 状态
                    update_sql = text("""
                        UPDATE subscriptions
                        SET status = 'cancelled', auto_renew = 0
                        WHERE id = :sub_id
                    """)

                    await db.execute(update_sql, {"sub_id": sub[0]})
                    total_cancelled += 1

                print()

            # 提交事务
            await db.commit()
            print(f"✓ 成功取消 {total_cancelled} 条重复订阅")

            # 3. 验证修复结果
            verify_result = await db.execute(find_duplicates_sql)
            remaining_duplicates = verify_result.fetchall()

            if not remaining_duplicates:
                print("✓ 验证通过，已无重复订阅")
            else:
                print(f"⚠️  仍有 {len(remaining_duplicates)} 个用户有重复订阅")

        except Exception as e:
            print(f"✗ 执行失败: {e}")
            await db.rollback()
            raise


def main():
    print("=" * 60)
    print("修复重复订阅脚本（SQL 版本）")
    print("=" * 60)
    print()
    print("⚠️  确保已备份数据库！")
    print()

    response = input("继续执行? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("已取消")
        return

    asyncio.run(fix_duplicates())


if __name__ == "__main__":
    main()
