"""
Billing API Routes

订阅和计费相关的 REST API 端点。
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging

from kode.database.session import get_db
from kode.models import User, Plan, Subscription
from kode.schemas.billing import (
    PlanCreate,
    PlanUpdate,
    PlanResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionCancel,
    UsageResponse,
    UsageSummary,
    StripeCheckoutSessionCreate,
    StripeCheckoutSessionResponse,
)
from kode.services.billing_service import BillingService
from kode.services.stripe_service import StripeService
from kode.web.dependencies import get_current_user
from kode.utils.config import ConfigManager

router = APIRouter()
logger = logging.getLogger(__name__)


# ============= Plan Management =============

@router.get("/plans", response_model=List[PlanResponse])
async def list_plans(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """列出所有套餐"""
    plans = await BillingService.list_plans(db, active_only=active_only)
    return plans


@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新套餐（管理员功能）"""
    # TODO: 添加管理员权限检查
    new_plan = Plan(**plan.dict())
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)

    logger.info(f"Created plan {new_plan.id} by user {current_user.id}")
    return new_plan


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取套餐详情"""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    return plan


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    plan_update: PlanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新套餐（管理员功能）"""
    # TODO: 添加管理员权限检查
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # 更新字段
    for field, value in plan_update.dict(exclude_unset=True).items():
        setattr(plan, field, value)

    await db.commit()
    await db.refresh(plan)

    logger.info(f"Updated plan {plan_id} by user {current_user.id}")
    return plan


# ============= Subscription Management =============

@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建订阅（用于测试或管理员手动创建）"""
    subscription = await BillingService.create_subscription(
        db=db,
        user_id=current_user.id,
        plan_id=subscription_data.plan_id,
        auto_renew=subscription_data.auto_renew,
    )

    # 加载关联的 plan
    await db.refresh(subscription, ["plan"])

    logger.info(f"Created subscription {subscription.id} for user {current_user.id}")
    return subscription


@router.get("/subscriptions/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的活跃订阅"""
    subscription = await BillingService.get_user_active_subscription(db, current_user.id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found",
        )

    # 加载关联的 plan
    await db.refresh(subscription, ["plan"])

    return subscription


@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    cancel_data: SubscriptionCancel,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消订阅"""
    # 验证订阅归属
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found",
        )

    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to cancel this subscription",
        )

    # 如果有 Stripe 订阅，通过 Stripe 取消
    if subscription.stripe_subscription_id:
        try:
            config = ConfigManager()
            stripe_key = config.get("stripe.secret_key") or None
            if stripe_key:
                stripe_service = StripeService(api_key=stripe_key)
                await stripe_service.cancel_subscription(
                    db, subscription_id, cancel_data.immediate
                )
            else:
                # 没有配置 Stripe，直接本地取消
                await BillingService.cancel_subscription(
                    db, subscription_id, cancel_data.immediate
                )
        except Exception as e:
            logger.error(f"Failed to cancel Stripe subscription: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel subscription via Stripe",
            )
    else:
        # 本地订阅，直接取消
        await BillingService.cancel_subscription(
            db, subscription_id, cancel_data.immediate
        )

    # 加载最新状态
    await db.refresh(subscription, ["plan"])

    logger.info(f"Cancelled subscription {subscription_id} for user {current_user.id}")
    return subscription


# ============= Usage Tracking =============

@router.get("/usage/me", response_model=UsageResponse)
async def get_my_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的使用量记录"""
    usage = await BillingService.get_current_usage(db, current_user.id)

    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No usage record found",
        )

    return usage


@router.get("/usage/me/summary", response_model=UsageSummary)
async def get_my_usage_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的使用量摘要"""
    try:
        summary = await BillingService.get_usage_summary(db, current_user.id)
        return summary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ============= Stripe Integration =============

@router.post("/stripe/checkout", response_model=StripeCheckoutSessionResponse)
async def create_stripe_checkout_session(
    checkout_data: StripeCheckoutSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建 Stripe Checkout Session"""
    try:
        config = ConfigManager()
        stripe_key = config.get("stripe.secret_key")
        if not stripe_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe is not configured",
            )

        stripe_service = StripeService(api_key=stripe_key)
        result = await stripe_service.create_checkout_session(
            db=db,
            user_id=current_user.id,
            plan_id=checkout_data.plan_id,
            success_url=checkout_data.success_url,
            cancel_url=checkout_data.cancel_url,
        )

        return StripeCheckoutSessionResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create Stripe checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    """处理 Stripe Webhook 事件"""
    try:
        config = ConfigManager()
        stripe_key = config.get("stripe.secret_key")
        webhook_secret = config.get("stripe.webhook_secret")

        if not stripe_key or not webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe is not configured",
            )

        if not stripe_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature",
            )

        payload = await request.body()

        stripe_service = StripeService(api_key=stripe_key)
        result = await stripe_service.handle_webhook(
            db=db,
            payload=payload,
            signature=stripe_signature,
            webhook_secret=webhook_secret,
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to handle Stripe webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        )
