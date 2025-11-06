"""
Subscription Model

用户订阅模型，记录用户当前的订阅状态。
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from kode.database.session import Base


class SubscriptionStatus(str, enum.Enum):
    """订阅状态枚举"""
    ACTIVE = "active"  # 活跃
    EXPIRED = "expired"  # 已过期
    CANCELLED = "cancelled"  # 已取消
    TRIAL = "trial"  # 试用期


class Subscription(Base):
    """用户订阅模型"""

    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(String(36), ForeignKey("plans.id"), nullable=False)

    # 订阅状态
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False, index=True)

    # 时间范围
    start_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_date = Column(DateTime, nullable=False)  # 到期时间

    # 续费设置
    auto_renew = Column(Boolean, default=False)  # 是否自动续费

    # 支付信息
    payment_method = Column(String(50), nullable=True)  # 支付方式
    last_payment_date = Column(DateTime, nullable=True)  # 最后支付时间

    # Stripe 集成
    stripe_customer_id = Column(String(255), nullable=True, index=True)  # Stripe 客户 ID
    stripe_subscription_id = Column(String(255), nullable=True, unique=True, index=True)  # Stripe 订阅 ID
    stripe_payment_intent_id = Column(String(255), nullable=True)  # 最后一次支付意图 ID

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="subscriptions")
    plan = relationship("Plan", backref="subscriptions")

    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan_id={self.plan_id}, status={self.status})>"

    def is_valid(self) -> bool:
        """检查订阅是否有效"""
        return self.status == SubscriptionStatus.ACTIVE and self.end_date > datetime.utcnow()
