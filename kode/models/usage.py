"""
Usage Model

用户使用量记录模型，追踪每个计费周期的使用情况。
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from kode.database.session import Base


class Usage(Base):
    """使用量记录模型"""

    __tablename__ = "usage"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(String, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=True)

    # 计费周期
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)

    # 使用量统计
    token_count = Column(Integer, default=0)  # Token 使用量
    message_count = Column(Integer, default=0)  # 消息条数
    conversation_count = Column(Integer, default=0)  # 当前对话数
    database_query_count = Column(Integer, default=0)  # 数据库查询次数

    # 记录时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="usage_records")
    subscription = relationship("Subscription", backref="usage_records")

    __table_args__ = (
        Index("idx_user_period", "user_id", "period_start", "period_end"),
    )

    def __repr__(self):
        return f"<Usage(id={self.id}, user_id={self.user_id}, tokens={self.token_count})>"
