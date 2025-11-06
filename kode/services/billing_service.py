"""
Billing Service

订阅管理和使用量追踪服务。
"""

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
import logging

from kode.models import User, Plan, Subscription, SubscriptionStatus, Usage
from kode.schemas.billing import UsageSummary

logger = logging.getLogger(__name__)


class BillingService:
    """订阅和计费服务"""

    @staticmethod
    async def get_user_active_subscription(
        db: AsyncSession, user_id: str
    ) -> Optional[Subscription]:
        """
        获取用户当前有效的订阅。

        Args:
            db: 数据库会话
            user_id: 用户 ID

        Returns:
            有效的订阅对象，如果没有则返回 None
        """
        result = await db.execute(
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.end_date > datetime.utcnow(),
                )
            )
            .order_by(Subscription.end_date.desc())
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_subscription(
        db: AsyncSession,
        user_id: str,
        plan_id: str,
        auto_renew: bool = False,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
    ) -> Subscription:
        """
        创建新订阅。

        Args:
            db: 数据库会话
            user_id: 用户 ID
            plan_id: 套餐 ID
            auto_renew: 是否自动续费
            stripe_customer_id: Stripe 客户 ID
            stripe_subscription_id: Stripe 订阅 ID

        Returns:
            新创建的订阅对象
        """
        # 获取套餐信息
        plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan_result.scalar_one_or_none()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # 计算订阅结束时间
        start_date = datetime.utcnow()
        if plan.billing_period == "monthly":
            end_date = start_date + timedelta(days=30)
        elif plan.billing_period == "yearly":
            end_date = start_date + timedelta(days=365)
        else:
            end_date = start_date + timedelta(days=30)

        # 创建订阅
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.ACTIVE,
            start_date=start_date,
            end_date=end_date,
            auto_renew=auto_renew,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            last_payment_date=start_date,
        )

        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)

        # 创建使用量记录
        await BillingService.create_usage_record(
            db=db,
            user_id=user_id,
            subscription_id=subscription.id,
            period_start=start_date,
            period_end=end_date,
        )

        logger.info(f"Created subscription {subscription.id} for user {user_id}")
        return subscription

    @staticmethod
    async def cancel_subscription(
        db: AsyncSession, subscription_id: str, immediate: bool = False
    ) -> Subscription:
        """
        取消订阅。

        Args:
            db: 数据库会话
            subscription_id: 订阅 ID
            immediate: 是否立即取消（否则到期后取消）

        Returns:
            更新后的订阅对象
        """
        result = await db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        if immediate:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.end_date = datetime.utcnow()
        else:
            subscription.auto_renew = False

        await db.commit()
        await db.refresh(subscription)

        logger.info(
            f"Cancelled subscription {subscription_id} (immediate={immediate})"
        )
        return subscription

    @staticmethod
    async def create_usage_record(
        db: AsyncSession,
        user_id: str,
        subscription_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Usage:
        """
        创建使用量记录。

        Args:
            db: 数据库会话
            user_id: 用户 ID
            subscription_id: 订阅 ID
            period_start: 计费周期开始时间
            period_end: 计费周期结束时间

        Returns:
            使用量记录对象
        """
        usage = Usage(
            user_id=user_id,
            subscription_id=subscription_id,
            period_start=period_start,
            period_end=period_end,
            token_count=0,
            message_count=0,
            conversation_count=0,
            database_query_count=0,
        )

        db.add(usage)
        await db.commit()
        await db.refresh(usage)

        return usage

    @staticmethod
    async def get_current_usage(
        db: AsyncSession, user_id: str
    ) -> Optional[Usage]:
        """
        获取用户当前计费周期的使用量记录。

        Args:
            db: 数据库会话
            user_id: 用户 ID

        Returns:
            使用量记录，如果不存在则返回 None
        """
        now = datetime.utcnow()
        result = await db.execute(
            select(Usage)
            .where(
                and_(
                    Usage.user_id == user_id,
                    Usage.period_start <= now,
                    Usage.period_end > now,
                )
            )
            .order_by(Usage.created_at.desc())
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def increment_usage(
        db: AsyncSession,
        user_id: str,
        token_count: int = 0,
        message_count: int = 0,
        conversation_count: int = 0,
        database_query_count: int = 0,
    ) -> Usage:
        """
        增加用户使用量。

        Args:
            db: 数据库会话
            user_id: 用户 ID
            token_count: 增加的 Token 数量
            message_count: 增加的消息数量
            conversation_count: 增加的对话数量
            database_query_count: 增加的数据库查询次数

        Returns:
            更新后的使用量记录
        """
        usage = await BillingService.get_current_usage(db, user_id)

        if not usage:
            # 如果没有使用量记录，创建一个
            subscription = await BillingService.get_user_active_subscription(
                db, user_id
            )
            if subscription:
                period_start = subscription.start_date
                period_end = subscription.end_date
            else:
                # 如果没有订阅，创建一个月的使用量记录
                period_start = datetime.utcnow()
                period_end = period_start + timedelta(days=30)

            usage = await BillingService.create_usage_record(
                db=db,
                user_id=user_id,
                subscription_id=subscription.id if subscription else None,
                period_start=period_start,
                period_end=period_end,
            )

        # 增加使用量
        usage.token_count += token_count
        usage.message_count += message_count
        usage.conversation_count = max(usage.conversation_count, conversation_count)
        usage.database_query_count += database_query_count

        await db.commit()
        await db.refresh(usage)

        return usage

    @staticmethod
    async def get_usage_summary(
        db: AsyncSession, user_id: str
    ) -> UsageSummary:
        """
        获取用户使用量摘要。

        Args:
            db: 数据库会话
            user_id: 用户 ID

        Returns:
            使用量摘要
        """
        # 获取当前订阅
        subscription = await BillingService.get_user_active_subscription(db, user_id)
        if not subscription:
            raise ValueError(f"No active subscription found for user {user_id}")

        # 获取套餐信息
        plan_result = await db.execute(
            select(Plan).where(Plan.id == subscription.plan_id)
        )
        plan = plan_result.scalar_one()

        # 获取当前使用量
        usage = await BillingService.get_current_usage(db, user_id)
        if not usage:
            usage = await BillingService.create_usage_record(
                db=db,
                user_id=user_id,
                subscription_id=subscription.id,
                period_start=subscription.start_date,
                period_end=subscription.end_date,
            )

        # 计算剩余配额
        token_remaining = max(0, plan.token_quota - usage.token_count)
        message_remaining = max(0, plan.message_quota - usage.message_count)

        # 检查是否超额
        is_quota_exceeded = (
            usage.token_count >= plan.token_quota
            or usage.message_count >= plan.message_quota
            or usage.conversation_count >= plan.conversation_quota
        )

        return UsageSummary(
            current_period_start=usage.period_start,
            current_period_end=usage.period_end,
            token_used=usage.token_count,
            token_quota=plan.token_quota,
            token_remaining=token_remaining,
            message_used=usage.message_count,
            message_quota=plan.message_quota,
            message_remaining=message_remaining,
            conversation_count=usage.conversation_count,
            conversation_quota=plan.conversation_quota,
            database_query_count=usage.database_query_count,
            is_quota_exceeded=is_quota_exceeded,
        )

    @staticmethod
    async def check_quota(db: AsyncSession, user_id: str) -> bool:
        """
        检查用户是否还有可用配额。

        Args:
            db: 数据库会话
            user_id: 用户 ID

        Returns:
            True 如果有可用配额，False 如果已超额
        """
        try:
            summary = await BillingService.get_usage_summary(db, user_id)
            return not summary.is_quota_exceeded
        except ValueError:
            # 没有有效订阅
            return False

    @staticmethod
    async def list_plans(
        db: AsyncSession, active_only: bool = True
    ) -> List[Plan]:
        """
        列出所有套餐。

        Args:
            db: 数据库会话
            active_only: 是否只返回激活的套餐

        Returns:
            套餐列表
        """
        query = select(Plan)
        if active_only:
            query = query.where(Plan.is_active == True)
        query = query.order_by(Plan.sort_order, Plan.price)

        result = await db.execute(query)
        return result.scalars().all()
