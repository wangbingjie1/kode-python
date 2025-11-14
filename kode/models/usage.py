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

    __tablename__ = "user_usage"  # 避免使用 MySQL 保留关键字 usage

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=True)

    # 计费周期
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)

    # 使用量统计（纯 Token 计费模式）
    token_count = Column(Integer, default=0)  # 【计费依据】Token 使用量（唯一扣费项）
    database_query_count = Column(Integer, default=0)  # 【仅统计】数据库查询次数

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
