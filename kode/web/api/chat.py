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
from kode.models import Conversation, Message, Project, User
from kode.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
)
from kode.web.dependencies import get_current_user
from kode.services.billing_service import BillingService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation"""
    # Verify project exists
    project_result = await db.execute(
        select(Project).where(Project.id == conversation.project_id)
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {conversation.project_id} not found",
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
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
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
    # Verify conversation exists
    conversation_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = conversation_result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
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
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
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
    # Verify project exists
    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Get conversations
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    return conversations
