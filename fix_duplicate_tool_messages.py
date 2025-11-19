"""
修复数据库中的重复工具消息问题

删除所有 tool_use_id 为 None 的 tool_use 和 tool_result 消息
"""
import asyncio
from sqlalchemy import select, delete
from kode.database.session import async_session_maker
from kode.models.message import Message

async def fix_duplicates():
    async with async_session_maker() as db:
        # 查询所有 tool 消息中 tool_use_id 为 None 的
        result = await db.execute(
            select(Message)
        )
        all_messages = result.scalars().all()

        to_delete = []
        for msg in all_messages:
            metadata = msg.message_metadata or {}
            msg_type = metadata.get('type')
            tool_use_id = metadata.get('tool_use_id')

            # 如果是 tool 消息但没有 tool_use_id（或为 None），则删除
            if msg_type in ['tool_use', 'tool_result'] and not tool_use_id:
                to_delete.append(msg)
                print(f"将删除: Seq={msg.sequence}, ConvID={msg.conversation_id[:8]}, Type={msg_type}, Tool={metadata.get('tool_name')}")

        if to_delete:
            print(f"\n共找到 {len(to_delete)} 条无效工具消息，开始删除...")
            for msg in to_delete:
                await db.delete(msg)
            await db.commit()
            print(f"已删除 {len(to_delete)} 条无效消息")
        else:
            print("没有找到需要删除的消息")

if __name__ == "__main__":
    asyncio.run(fix_duplicates())
