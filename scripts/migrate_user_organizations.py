"""
数据迁移脚本：为现有用户创建 Organization 记录

运行方式：
    python scripts/migrate_user_organizations.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from kode.database.session import async_session_maker
from kode.models import User, Organization


async def migrate_user_organizations():
    """为没有 Organization 的用户创建默认组织"""
    async with async_session_maker() as session:
        # 查找所有用户，预加载 organization 关系
        result = await session.execute(
            select(User).options(selectinload(User.organization))
        )
        all_users = result.scalars().all()

        # 过滤出没有 organization 的用户
        users_without_org = [u for u in all_users if u.organization is None]

        if not users_without_org:
            print("所有用户都已有 Organization，无需迁移")
            return

        print(f"发现 {len(users_without_org)} 个用户需要创建 Organization")

        for user in users_without_org:
            # 为每个用户创建默认组织
            org_name = user.username or user.email.split('@')[0] if user.email else f"用户{user.id[:8]}"
            org = Organization(
                name=f"{org_name}的组织",
                owner_id=user.id
            )
            session.add(org)
            print(f"  ✓ 为用户 {user.email or user.id} 创建组织: {org.name}")

        await session.commit()
        print(f"\n迁移完成，共创建 {len(users_without_org)} 个组织")


if __name__ == "__main__":
    asyncio.run(migrate_user_organizations())
