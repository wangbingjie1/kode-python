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
    ConversationListResponse,
    MessageResponse,
)
from kode.web.dependencies import get_current_user
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
                Project.user_id == user_id,
                Conversation.deleted_at.is_(None)  # 排除已软删除的
            )
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        if check_exists:
            # 检查对话是否存在（用于区分 404 和 403）
            # 已删除的对话也视为不存在
            exists_result = await db.execute(
                select(Conversation.id).where(
                    and_(
                        Conversation.id == conversation_id,
                        Conversation.deleted_at.is_(None)
                    )
                )
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
    # ✅ 优化：移除配额检查，创建空会话不消耗 token
    # 配额检查移到发送消息时进行（SSE 端点）

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
    # ✅ 优化：在 Python 端生成所有字段，避免 refresh 查询
    now = datetime.utcnow()
    db_conversation = Conversation(
        title=conversation.title or "New Conversation",
        project_id=project.id,
        created_at=now,
        updated_at=now,
    )

    db.add(db_conversation)
    await db.commit()
    # 不需要 refresh，id/created_at/updated_at 都在 Python 端生成

    logger.info(f"Created conversation {db_conversation.id} for user {current_user.id}")

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


@router.get("/projects/{project_id}/conversations", response_model=ConversationListResponse)
async def list_project_conversations(
    project_id: str,
    limit: int = 20,
    offset: int = 0,
    search: str = None,
    search_content: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List conversations for a project with pagination and search

    Args:
        project_id: Project ID
        limit: Maximum number of conversations to return (default 20, max 100)
        offset: Number of conversations to skip (for pagination)
        search: Optional search keyword to filter by title (and content if search_content=True)
        search_content: If True, also search in message content (slower)
    """
    # Verify project exists and belongs to current user
    project = await verify_project_ownership(
        project_id, current_user.id, db
    )

    # Limit max results
    limit = min(limit, 100)

    # 基础条件：项目内未删除的对话
    base_condition = and_(
        Conversation.project_id == project_id,
        Conversation.deleted_at.is_(None)
    )

    # 搜索消息内容时，需要关联 Message 表
    matched_messages = {}  # conversation_id -> matched_message
    content_matched_ids = set()

    if search and search.strip() and search_content:
        search_term = f"%{search.strip()}%"
        # 搜索消息内容，获取匹配的对话ID和消息片段
        content_query = (
            select(Message.conversation_id, Message.content)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .join(Project, Conversation.project_id == Project.id)
            .where(
                and_(
                    Conversation.project_id == project_id,
                    Conversation.deleted_at.is_(None),
                    Project.user_id == current_user.id,
                    Message.role == "user",  # 只搜索用户消息
                    Message.content.ilike(search_term)
                )
            )
            .distinct()
        )
        content_result = await db.execute(content_query)
        for conv_id, content in content_result:
            content_matched_ids.add(conv_id)
            # 提取匹配片段（最多100字符）
            if conv_id not in matched_messages:
                search_lower = search.strip().lower()
                content_lower = content.lower()
                idx = content_lower.find(search_lower)
                if idx >= 0:
                    start = max(0, idx - 30)
                    end = min(len(content), idx + len(search.strip()) + 70)
                    snippet = content[start:end]
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(content):
                        snippet = snippet + "..."
                    matched_messages[conv_id] = snippet

    # 构建主查询
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        if search_content and content_matched_ids:
            # 标题匹配 OR 内容匹配
            query = select(Conversation).where(
                and_(
                    base_condition,
                    (Conversation.title.ilike(search_term) | Conversation.id.in_(content_matched_ids))
                )
            )
        else:
            # 仅标题匹配
            query = select(Conversation).where(
                and_(base_condition, Conversation.title.ilike(search_term))
            )
    else:
        query = select(Conversation).where(base_condition)

    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 添加排序和分页
    query = query.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)

    # 执行查询
    result = await db.execute(query)
    conversations = result.scalars().all()

    # 构建响应，附加匹配的消息片段
    items = []
    for conv in conversations:
        item = ConversationResponse(
            id=conv.id,
            title=conv.title,
            project_id=conv.project_id,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            matched_message=matched_messages.get(conv.id)
        )
        items.append(item)

    return ConversationListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total
    )


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
