"""
Billing Schemas

Pydantic schemas for billing and subscription-related API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class BillingPeriod(str, Enum):
    """计费周期枚举"""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatusEnum(str, Enum):
    """订阅状态枚举"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    TRIAL = "trial"


# ============= Plan Schemas =============

class PlanBase(BaseModel):
    """套餐基础 Schema"""
    name: str = Field(..., max_length=50)
    display_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    billing_period: BillingPeriod = BillingPeriod.MONTHLY


class PlanCreate(PlanBase):
    """创建套餐 Schema"""
    token_quota: int = Field(..., ge=0)
    message_quota: int = Field(..., ge=0)
    conversation_quota: int = Field(..., ge=0)
    database_connection_quota: int = Field(default=0, ge=0)
    database_access: bool = False
    advanced_analysis: bool = False
    ontology_building: bool = False
    priority_support: bool = False
    features: Optional[Dict[str, Any]] = None
    sort_order: int = 0


class PlanUpdate(BaseModel):
    """更新套餐 Schema"""
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    token_quota: Optional[int] = Field(None, ge=0)
    message_quota: Optional[int] = Field(None, ge=0)
    conversation_quota: Optional[int] = Field(None, ge=0)
    database_connection_quota: Optional[int] = Field(None, ge=0)
    database_access: Optional[bool] = None
    advanced_analysis: Optional[bool] = None
    ontology_building: Optional[bool] = None
    priority_support: Optional[bool] = None
    features: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class PlanResponse(PlanBase):
    """套餐响应 Schema"""
    id: str
    token_quota: int
    message_quota: int
    conversation_quota: int
    database_connection_quota: int
    database_access: bool
    advanced_analysis: bool
    ontology_building: bool
    priority_support: bool
    features: Optional[Dict[str, Any]]
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


# ============= Subscription Schemas =============

class SubscriptionCreate(BaseModel):
    """创建订阅 Schema"""
    plan_id: str
    auto_renew: bool = False


class SubscriptionResponse(BaseModel):
    """订阅响应 Schema"""
    id: str
    user_id: str
    plan_id: str
    status: SubscriptionStatusEnum
    start_date: datetime
    end_date: datetime
    auto_renew: bool
    payment_method: Optional[str]
    last_payment_date: Optional[datetime]
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    # 关联对象
    plan: Optional[PlanResponse] = None

    class Config:
        from_attributes = True


class SubscriptionCancel(BaseModel):
    """取消订阅 Schema"""
    immediate: bool = Field(default=False, description="是否立即取消（否则到期后取消）")


# ============= Usage Schemas =============

class UsageResponse(BaseModel):
    """使用量响应 Schema"""
    id: str
    user_id: str
    subscription_id: Optional[str]
    period_start: datetime
    period_end: datetime
    token_count: int
    message_count: int
    conversation_count: int
    database_query_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsageSummary(BaseModel):
    """使用量摘要 Schema"""
    current_period_start: datetime
    current_period_end: datetime
    token_used: int
    token_quota: int
    token_remaining: int
    message_used: int
    message_quota: int
    message_remaining: int
    conversation_count: int
    conversation_quota: int
    database_query_count: int
    is_quota_exceeded: bool


# ============= Stripe Schemas =============

class StripeCheckoutSessionCreate(BaseModel):
    """创建 Stripe Checkout Session Schema"""
    plan_id: str
    success_url: str
    cancel_url: str


class StripeCheckoutSessionResponse(BaseModel):
    """Stripe Checkout Session 响应 Schema"""
    session_id: str
    checkout_url: str


class StripeWebhookEvent(BaseModel):
    """Stripe Webhook Event Schema"""
    type: str
    data: Dict[str, Any]
