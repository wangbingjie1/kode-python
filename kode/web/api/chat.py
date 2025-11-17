"""
Chat API Routes

REST endpoints for conversation and message management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List
from datetime import datetime

from kode.database.session import get_db
from kode.models import Conversation, Message, Project, User, APICallTrace
from kode.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
)
from kode.web.dependencies import get_current_user
from kode.services.billing_service import BillingService
from kode.web.middleware.quota_check import check_user_quota
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def verify_project_ownership(
    project_id: str, user_id: str, db: AsyncSession
) -> Project:
    """
    验证项目所有权

    Args:
        project_id: 项目 ID
        user_id: 用户 ID
        db: 数据库会话

    Returns:
        Project: 项目对象

    Raises:
        HTTPException: 如果项目不存在或不属于用户
    """
    result = await db.execute(
        select(Project).where(
            and_(
                Project.id == project_id,
                Project.user_id == user_id
            )
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this project",
        )

    return project


async def verify_conversation_ownership(
    conversation_id: str, user_id: str, db: AsyncSession
) -> Conversation:
    """
    验证对话所有权（通过 Conversation -> Project -> User 链）

    Args:
        conversation_id: 对话 ID
        user_id: 用户 ID
        db: 数据库会话

    Returns:
        Conversation: 对话对象

    Raises:
        HTTPException: 如果对话不存在或不属于用户
    """
    result = await db.execute(
        select(Conversation)
        .join(Project, Conversation.project_id == Project.id)
        .where(
            and_(
                Conversation.id == conversation_id,
                Project.user_id == user_id
            )
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this conversation",
        )

    return conversation


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation"""
    # Check quota before creating conversation
    await check_user_quota(current_user.id, db)

    # Verify project exists and belongs to current user
    project = await verify_project_ownership(
        conversation.project_id, current_user.id, db
    )

    # Create conversation
    db_conversation = Conversation(
        title=conversation.title or "New Conversation",
        project_id=conversation.project_id,
    )

    db.add(db_conversation)
    await db.commit()
    await db.refresh(db_conversation)

    # 更新会话计数（统计用户当前计费周期的总会话数）
    try:
        usage = await BillingService.get_current_usage(db, current_user.id)
        if usage:
            # 统计当前计费周期内的会话数
            conversation_count_result = await db.execute(
                select(func.count(Conversation.id)).where(
                    and_(
                        Conversation.project_id.in_(
                            select(Project.id).where(Project.user_id == current_user.id)
                        ),
                        Conversation.created_at >= usage.period_start,
                        Conversation.created_at < usage.period_end,
                    )
                )
            )
            total_conversations = conversation_count_result.scalar() or 0

            # 更新使用量记录中的会话计数
            await BillingService.increment_usage(
                db=db,
                user_id=current_user.id,
                conversation_count=total_conversations,
            )
            logger.info(f"Updated conversation count to {total_conversations} for user {current_user.id}")
    except Exception as e:
        # 使用量更新失败不应该影响主流程
        logger.warning(f"Failed to update conversation count: {e}")

    return db_conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation by ID"""
    # Verify conversation exists and belongs to current user
    conversation = await verify_conversation_ownership(
        conversation_id, current_user.id, db
    )

    return conversation


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a conversation"""
    # Verify conversation exists and belongs to current user
    conversation = await verify_conversation_ownership(
        conversation_id, current_user.id, db
    )

    # Get messages
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .limit(limit)
    )
    messages = messages_result.scalars().all()

    return messages


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation"""
    # Verify conversation exists and belongs to current user
    conversation = await verify_conversation_ownership(
        conversation_id, current_user.id, db
    )

    await db.delete(conversation)
    await db.commit()

    # 更新会话计数（删除后重新统计）
    try:
        usage = await BillingService.get_current_usage(db, current_user.id)
        if usage:
            # 统计当前计费周期内的会话数
            conversation_count_result = await db.execute(
                select(func.count(Conversation.id)).where(
                    and_(
                        Conversation.project_id.in_(
                            select(Project.id).where(Project.user_id == current_user.id)
                        ),
                        Conversation.created_at >= usage.period_start,
                        Conversation.created_at < usage.period_end,
                    )
                )
            )
            total_conversations = conversation_count_result.scalar() or 0

            # 更新使用量记录中的会话计数
            await BillingService.increment_usage(
                db=db,
                user_id=current_user.id,
                conversation_count=total_conversations,
            )
            logger.info(f"Updated conversation count to {total_conversations} after deletion for user {current_user.id}")
    except Exception as e:
        # 使用量更新失败不应该影响主流程
        logger.warning(f"Failed to update conversation count after deletion: {e}")


@router.get("/projects/{project_id}/conversations", response_model=List[ConversationResponse])
async def list_project_conversations(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for a project"""
    # Verify project exists and belongs to current user
    project = await verify_project_ownership(
        project_id, current_user.id, db
    )

    # Get conversations
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    return conversations


@router.get("/conversations/{conversation_id}/api_traces")
async def get_conversation_api_traces(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话的 API 调用追踪记录（用于真实成本分析）"""
    # 验证会话所有权
    conversation = await verify_conversation_ownership(
        conversation_id, current_user.id, db
    )

    # 查询该会话的所有 API traces
    result = await db.execute(
        select(APICallTrace)
        .where(APICallTrace.conversation_id == conversation_id)
        .order_by(APICallTrace.created_at)
    )
    traces = result.scalars().all()

    # 计算汇总统计
    total_input_tokens = sum(t.input_tokens for t in traces)
    total_output_tokens = sum(t.output_tokens for t in traces)
    total_cache_creation = sum(t.cache_creation_input_tokens for t in traces)
    total_cache_read = sum(t.cache_read_input_tokens for t in traces)

    total_cost = sum(t.total_cost for t in traces)
    total_savings = sum(t.cost_savings for t in traces)

    return {
        "conversation_id": conversation_id,
        "summary": {
            "total_calls": len(traces),
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cache_creation_tokens": total_cache_creation,
            "total_cache_read_tokens": total_cache_read,
            "total_cost_usd": round(total_cost, 8),
            "total_savings_usd": round(total_savings, 8),
        },
        "traces": [trace.to_dict() for trace in traces],
    }
