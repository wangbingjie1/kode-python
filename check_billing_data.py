#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查商业化模块数据"""

import asyncio
import aiomysql
import sys
import io

# 设置输出编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def check_data():
    """检查数据"""
    conn = await aiomysql.connect(
        host="54.179.161.188",
        port=3306,
        user="glbgpt",
        password="root!@#123QWE,.12",
        db="test",
        charset='utf8mb4'
    )

    async with conn.cursor() as cursor:
        # 检查套餐
        await cursor.execute("SELECT id, name, display_name, price FROM plans ORDER BY sort_order")
        plans = await cursor.fetchall()
        print("=" * 60)
        print("套餐列表:")
        print("=" * 60)
        for plan in plans:
            print(f"  [{plan[1]}] {plan[2]} - ¥{plan[3]}/月 (ID: {plan[0]})")

        # 检查用户
        await cursor.execute("SELECT id, username, email FROM users")
        users = await cursor.fetchall()
        print("\n" + "=" * 60)
        print(f"用户列表: 共 {len(users)} 个")
        print("=" * 60)
        for user in users:
            print(f"  {user[1]} ({user[2]}) - ID: {user[0]}")

        # 检查订阅
        await cursor.execute("""
            SELECT s.id, u.username, p.display_name, s.status, s.start_date, s.end_date
            FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            JOIN plans p ON s.plan_id = p.id
        """)
        subscriptions = await cursor.fetchall()
        print("\n" + "=" * 60)
        print(f"订阅列表: 共 {len(subscriptions)} 个")
        print("=" * 60)
        for sub in subscriptions:
            print(f"  用户: {sub[1]}, 套餐: {sub[2]}, 状态: {sub[3]}")
            print(f"    有效期: {sub[4]} ~ {sub[5]}")

        # 检查使用量
        await cursor.execute("""
            SELECT u.username, uu.token_count, uu.message_count, uu.conversation_count
            FROM user_usage uu
            JOIN users u ON uu.user_id = u.id
        """)
        usages = await cursor.fetchall()
        print("\n" + "=" * 60)
        print(f"使用量记录: 共 {len(usages)} 个")
        print("=" * 60)
        for usage in usages:
            print(f"  用户: {usage[0]}")
            print(f"    Token: {usage[1]}, 消息: {usage[2]}, 对话: {usage[3]}")

    conn.close()
    print("\n" + "=" * 60)
    print("✓ 数据检查完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(check_data())
