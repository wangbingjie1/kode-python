"""
Stripe Integration Service

Stripe 支付集成服务。
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from kode.models import User, Plan, Subscription, SubscriptionStatus
from kode.services.billing_service import BillingService

logger = logging.getLogger(__name__)


class StripeService:
    """Stripe 支付服务"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Stripe 服务。

        Args:
            api_key: Stripe API Key，如果不提供则从环境变量读取
        """
        if not STRIPE_AVAILABLE:
            raise ImportError("stripe package is not installed. Run: pip install stripe")

        self.api_key = api_key or os.getenv("STRIPE_SECRET_KEY")
        if not self.api_key:
            raise ValueError("STRIPE_SECRET_KEY not configured")

        stripe.api_key = self.api_key
        logger.info("Stripe service initialized")

    async def create_customer(
        self, user: User, email: Optional[str] = None
    ) -> str:
        """
        创建 Stripe 客户。

        Args:
            user: 用户对象
            email: 客户邮箱（可选）

        Returns:
            Stripe 客户 ID
        """
        try:
            customer = stripe.Customer.create(
                email=email or user.email,
                metadata={
                    "user_id": user.id,
                    "username": user.username,
                },
            )
            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise

    async def create_checkout_session(
        self,
        db: AsyncSession,
        user_id: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, str]:
        """
        创建 Stripe Checkout Session。

        Args:
            db: 数据库会话
            user_id: 用户 ID
            plan_id: 套餐 ID
            success_url: 支付成功跳转 URL
            cancel_url: 支付取消跳转 URL

        Returns:
            包含 session_id 和 checkout_url 的字典
        """
        # 获取用户
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # 获取套餐
        plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan_result.scalar_one_or_none()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # 获取或创建 Stripe 客户
        stripe_customer_id = None
        subscription = await BillingService.get_user_active_subscription(db, user_id)
        if subscription and subscription.stripe_customer_id:
            stripe_customer_id = subscription.stripe_customer_id
        else:
            stripe_customer_id = await self.create_customer(user)

        # 创建 Checkout Session
        try:
            # 计算价格（转换为分）
            unit_amount = int(plan.price * 100)

            # 创建订阅模式的 checkout session
            session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "cny",
                            "unit_amount": unit_amount,
                            "recurring": {
                                "interval": "month" if plan.billing_period == "monthly" else "year",
                            },
                            "product_data": {
                                "name": plan.display_name,
                                "description": plan.description,
                            },
                        },
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": user_id,
                    "plan_id": plan_id,
                },
            )

            logger.info(f"Created Stripe checkout session {session.id} for user {user_id}")
            return {
                "session_id": session.id,
                "checkout_url": session.url,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe checkout session: {e}")
            raise

    async def handle_webhook(
        self, db: AsyncSession, payload: bytes, signature: str, webhook_secret: str
    ) -> Dict[str, Any]:
        """
        处理 Stripe Webhook 事件。

        Args:
            db: 数据库会话
            payload: Webhook 负载
            signature: Stripe 签名
            webhook_secret: Webhook 密钥

        Returns:
            处理结果
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise

        event_type = event["type"]
        data = event["data"]["object"]

        logger.info(f"Received Stripe webhook: {event_type} [event_id: {event.get('id', 'unknown')}]")

        try:
            # 处理订阅创建成功
            if event_type == "checkout.session.completed":
                await self._handle_checkout_completed(db, data)

            # 处理订阅支付成功
            elif event_type == "invoice.payment_succeeded":
                await self._handle_payment_succeeded(db, data)

            # 处理订阅支付失败
            elif event_type == "invoice.payment_failed":
                await self._handle_payment_failed(db, data)

            # 处理订阅取消
            elif event_type == "customer.subscription.deleted":
                await self._handle_subscription_deleted(db, data)

            # 其他不需要处理的事件（仅记录日志）
            elif event_type in [
                # 发票相关
                "invoice.created",
                "invoice.finalized",
                "invoice.paid",
                "invoice.updated",
                "invoice_payment.paid",
                # 客户相关
                "customer.created",
                "customer.updated",
                "customer.deleted",
                # 订阅相关
                "customer.subscription.created",
                "customer.subscription.updated",
                # 支付相关
                "payment_intent.created",
                "payment_intent.succeeded",
                "payment_intent.payment_failed",
                "payment_method.attached",
                "payment_method.detached",
                "payment_method.updated",
                "charge.succeeded",
                "charge.failed",
                "charge.refunded",
            ]:
                logger.info(f"Event {event_type} received, no action needed")

            # 未处理的事件类型
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")

            return {"status": "success", "event_type": event_type}

        except Exception as e:
            logger.error(f"Error processing webhook event {event_type}: {e}", exc_info=True)
            # 不要向 Stripe 返回错误，避免重试风暴
            # 但记录错误以便后续排查
            return {"status": "error", "event_type": event_type, "error": str(e)}

    async def _handle_checkout_completed(
        self, db: AsyncSession, session_data: Dict[str, Any]
    ):
        """处理 Checkout Session 完成事件"""
        user_id = session_data["metadata"]["user_id"]
        plan_id = session_data["metadata"]["plan_id"]
        stripe_customer_id = session_data["customer"]
        stripe_subscription_id = session_data.get("subscription")

        # 创建或更新订阅
        await BillingService.create_subscription(
            db=db,
            user_id=user_id,
            plan_id=plan_id,
            auto_renew=True,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
        )

        logger.info(f"Checkout completed for user {user_id}, plan {plan_id}")

    async def _handle_payment_succeeded(
        self, db: AsyncSession, invoice_data: Dict[str, Any]
    ):
        """处理支付成功事件"""
        stripe_subscription_id = invoice_data.get("subscription")
        if not stripe_subscription_id:
            logger.warning("invoice.payment_succeeded event missing subscription ID")
            return

        # 更新订阅状态
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(
                f"Subscription not found for Stripe subscription {stripe_subscription_id}. "
                "This is normal if checkout.session.completed hasn't been processed yet."
            )
            return

        try:
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.last_payment_date = datetime.utcnow()

            # 续期
            if subscription.end_date and subscription.end_date < datetime.utcnow():
                plan_result = await db.execute(
                    select(Plan).where(Plan.id == subscription.plan_id)
                )
                plan = plan_result.scalar_one_or_none()

                if not plan:
                    logger.error(f"Plan {subscription.plan_id} not found for subscription {subscription.id}")
                    return

                if plan.billing_period == "monthly":
                    subscription.end_date = datetime.utcnow() + timedelta(days=30)
                else:
                    subscription.end_date = datetime.utcnow() + timedelta(days=365)

            await db.commit()
            logger.info(f"Payment succeeded for subscription {subscription.id}")
        except Exception as e:
            logger.error(f"Error updating subscription after payment: {e}", exc_info=True)
            await db.rollback()
            raise

    async def _handle_payment_failed(
        self, db: AsyncSession, invoice_data: Dict[str, Any]
    ):
        """处理支付失败事件"""
        stripe_subscription_id = invoice_data.get("subscription")
        if not stripe_subscription_id:
            return

        # 更新订阅状态
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.status = SubscriptionStatus.EXPIRED
            await db.commit()
            logger.warning(f"Payment failed for subscription {subscription.id}")

    async def _handle_subscription_deleted(
        self, db: AsyncSession, subscription_data: Dict[str, Any]
    ):
        """处理订阅删除事件"""
        stripe_subscription_id = subscription_data["id"]

        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.end_date = datetime.utcnow()
            await db.commit()
            logger.info(f"Subscription {subscription.id} deleted")

    async def cancel_subscription(
        self, db: AsyncSession, subscription_id: str, immediate: bool = False
    ):
        """
        取消 Stripe 订阅。

        Args:
            db: 数据库会话
            subscription_id: 本地订阅 ID
            immediate: 是否立即取消
        """
        result = await db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError(f"Subscription {subscription_id} not found or not linked to Stripe")

        try:
            if immediate:
                # 立即取消
                stripe.Subscription.delete(subscription.stripe_subscription_id)
            else:
                # 计费周期结束时取消
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True,
                )

            # 更新本地订阅
            await BillingService.cancel_subscription(db, subscription_id, immediate)

            logger.info(f"Cancelled Stripe subscription {subscription.stripe_subscription_id}")

        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel Stripe subscription: {e}")
            raise
