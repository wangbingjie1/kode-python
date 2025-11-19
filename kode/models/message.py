"""
Message Model

Database model for chat messages.
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from kode.database.session import Base


class Message(Base):
    """Message model for conversation messages"""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String(36), ForeignKey("conversations.id"), nullable=False, index=True
    )
    role = Column(String(20), nullable=False)  # "user", "assistant", "tool_use", or "tool_result"
    content = Column(Text, nullable=False, default="")  # 默认空字符串（tool_use 消息的 content 存储在 metadata 中）
    message_metadata = Column(JSON, default=dict)  # Store tool calls, model info, chart data, content blocks, etc.

    # Token 统计字段（仅 assistant 消息有值）
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    cache_creation_tokens = Column(Integer, default=0, nullable=False)
    cache_read_tokens = Column(Integer, default=0, nullable=False)

    # 序列号（确保消息顺序，尤其是工具调用消息）
    sequence = Column(Integer, nullable=False, default=0, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role})>"
