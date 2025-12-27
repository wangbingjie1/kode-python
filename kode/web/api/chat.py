"""
Chat API Routes

REST endpoints for conversation and message management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update
from typing import List
from datetime import datetime

from kode.database.session import get_db
from kode.models import Conversation, Message, Project, User, APICallTrace
from kode.models.ontology_version import OntologyVersion
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
    conversation_id: str, user_id: str, db: AsyncSession, *, check_exists: bool = False
) -> Conversation:
    """
    验证对话所有权（通过 Conversation -> Project -> User 链）

    Args:
        conversation_id: 对话 ID
        user_id: 用户 ID
        db: 数据库会话
        check_exists: 如果为 True，先检查对话是否存在以区分 404 和 403

    Returns:
        Conversation: 对话对象

    Raises:
        HTTPException: 404 如果对话不存在，403 如果不属于用户
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
        if check_exists:
            # 检查对话是否存在（用于区分 404 和 403）
            exists_result = await db.execute(
                select(Conversation.id).where(Conversation.id == conversation_id)
            )
            if not exists_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )
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

    # Get or create project
    if conversation.project_id:
        # If project_id provided, verify it belongs to current user
        project = await verify_project_ownership(
            conversation.project_id, current_user.id, db
        )
    else:
        # Otherwise, get or create default project for user
        result = await db.execute(
            select(Project)
            .where(Project.user_id == current_user.id)
            .order_by(Project.created_at)
        )
        project = result.scalar_one_or_none()

        if not project:
            # Create default project if user has none
            project = Project(
                name="默认项目",
                description="自动创建的默认项目",
                user_id=current_user.id,
            )
            db.add(project)
            await db.flush()  # Flush to get project.id

    # Create conversation
    db_conversation = Conversation(
        title=conversation.title or "New Conversation",
        project_id=project.id,
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

            # ❌ 移除错误的 usage 更新调用
            # increment_usage 不支持 conversation_count 参数
            # 会话计数不计入配额，只用于统计展示
            logger.info(f"Created conversation {db_conversation.id} for user {current_user.id} (total: {total_conversations})")
    except Exception as e:
        # 会话计数统计失败不应该影响主流程
        logger.warning(f"Failed to count conversations: {e}")

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

    # Get messages (按 sequence 排序，确保工具调用顺序正确)
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sequence, Message.created_at)  # sequence 优先，created_at 次之
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
    """Delete a conversation (soft delete for billing audit)"""
    # Verify conversation exists and belongs to current user
    # check_exists=True 用于区分 404（不存在）和 403（无权限）
    conversation = await verify_conversation_ownership(
        conversation_id, current_user.id, db, check_exists=True
    )

    # 软删除：设置 deleted_at 时间戳，保留数据用于 token 对账
    conversation.deleted_at = datetime.utcnow()
    await db.commit()

    logger.info(f"Soft deleted conversation {conversation_id} for user {current_user.id}")


@router.get("/projects/{project_id}/conversations", response_model=List[ConversationResponse])
async def list_project_conversations(
    project_id: str,
    limit: int = 50,
    offset: int = 0,
    search: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List conversations for a project with pagination and search

    Args:
        project_id: Project ID
        limit: Maximum number of conversations to return (default 50, max 100)
        offset: Number of conversations to skip (for pagination)
        search: Optional search keyword to filter by title
    """
    # Verify project exists and belongs to current user
    project = await verify_project_ownership(
        project_id, current_user.id, db
    )

    # Limit max results
    limit = min(limit, 100)

    # Build query - 排除已软删除的对话
    query = select(Conversation).where(
        and_(
            Conversation.project_id == project_id,
            Conversation.deleted_at.is_(None)  # 只显示未删除的
        )
    )

    # Add search filter if provided
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        query = query.where(Conversation.title.ilike(search_term))

    # Add ordering and pagination
    query = query.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
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
    # ⚠️ 关键说明：trace.input_tokens 只是常规输入，不包含缓存
    # 真实总输入 = regular + cache_creation + cache_read
    regular_input_tokens = sum(t.input_tokens for t in traces)
    total_cache_creation = sum(t.cache_creation_input_tokens for t in traces)
    total_cache_read = sum(t.cache_read_input_tokens for t in traces)
    total_output_tokens = sum(t.output_tokens for t in traces)

    # ✅ 完整输入计数
    true_total_input_tokens = regular_input_tokens + total_cache_creation + total_cache_read
    true_total_tokens = true_total_input_tokens + total_output_tokens

    total_cost = sum(t.total_cost for t in traces)
    total_savings = sum(t.cost_savings for t in traces)

    return {
        "conversation_id": conversation_id,
        "summary": {
            "total_calls": len(traces),
            "total_tokens": true_total_tokens,  # ✅ 完整计数
            "total_input_tokens": true_total_input_tokens,  # ✅ 完整输入
            "total_output_tokens": total_output_tokens,
            "total_cache_creation_tokens": total_cache_creation,
            "total_cache_read_tokens": total_cache_read,
            "total_cost_usd": round(total_cost, 8),
            "total_savings_usd": round(total_savings, 8),
        },
        "traces": [trace.to_dict() for trace in traces],
    }
