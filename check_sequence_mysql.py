"""
检查 MySQL 数据库中消息的 sequence 顺序问题
"""
import asyncio
from sqlalchemy import select, func
from kode.database.session import async_session_maker
from kode.models.message import Message

async def check_sequence():
    conversation_id = '5635e524-4ab3-497a-8324-e1d5bc30eeda'  # 今日收支明细

    async with async_session_maker() as db:
        # 查询指定会话的消息（按 sequence 排序）
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence, Message.created_at)
        )
        messages = result.scalars().all()

        print(f"\n会话 {conversation_id} 共有 {len(messages)} 条消息\n")
        print(f"{'Seq':<5} {'Role':<10} {'Type':<15} {'Tool':<25} {'Content Preview':<50} {'ToolUseID':<30}")
        print("-" * 160)

        for msg in messages:
            metadata = msg.message_metadata or {}
            msg_type = metadata.get('type', 'N/A')
            tool_name = metadata.get('tool_name', 'N/A')
            tool_use_id = metadata.get('tool_use_id', 'N/A')
            tool_use_id_short = tool_use_id[:20] if isinstance(tool_use_id, str) else 'N/A'

            content_preview = (msg.content[:50] if msg.content else 'N/A')

            print(f"{msg.sequence:<5} {msg.role:<10} {msg_type:<15} {tool_name:<25} {content_preview:<50} {tool_use_id_short:<30}")

if __name__ == "__main__":
    asyncio.run(check_sequence())
