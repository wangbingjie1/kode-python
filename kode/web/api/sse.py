"""
SSE (Server-Sent Events) API Routes

Provides real-time streaming of AI responses using SSE instead of WebSocket.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import AsyncGenerator, Optional
import json
import logging

from kode.database.session import get_db
from kode.models import Conversation, Message, User
from kode.services.conversation import AsyncConversationService
from kode.utils.logger import setup_logger
from kode.web.dependencies import get_current_user
from kode.core.security import verify_token

logger = setup_logger(__name__)
router = APIRouter()


async def get_user_from_token_or_header(
    token: Optional[str] = Query(None, description="JWT access token (for SSE)"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    从token参数或Authorization头获取当前用户
    用于SSE接口,因为EventSource不支持自定义HTTP头
    """
    # 优先使用token参数
    if token:
        payload = verify_token(token, token_type="access")
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌格式",
            )

        # 从数据库获取用户
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用",
            )

        return user

    # 如果没有token参数,使用标准的get_current_user(从Authorization头获取)
    # 注意: EventSource不支持自定义头,所以这里不会被触发
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="需要提供token参数进行认证",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def event_generator(
    conversation_id: str,
    task_content: str,
    conversation_service: AsyncConversationService,
    user_id: str,
    database_name: str | None = None,
    chat_history: list | None = None,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for streaming AI responses.

    SSE format:
    data: {"type": "thinking", "content": "...", "metadata": {}}

    data: {"type": "chunk", "content": "...", "metadata": {}}

    data: {"type": "complete", "content": "...", "metadata": {}}

    """
    from kode.database.session import async_session_maker

    assistant_content = ""  # 收集完整的 AI 回复

    try:
        async for chunk in conversation_service.execute_task_streaming(
            task=task_content,
            conversation_id=conversation_id,
            user_id=user_id,
            database_name=database_name,
            chat_history=chat_history or [],  # ← 传入历史消息
        ):
            # Format as SSE event
            chunk_type = chunk.get('type')
            logger.info(f"[SSE] Sending chunk: type={chunk_type}")

            # Collect assistant response content
            if chunk_type == "chunk":
                assistant_content += chunk.get("content", "")

            # Log tool call details for debugging
            if chunk_type in ('tool_call', 'tool_result'):
                metadata = chunk.get('metadata', {})
                logger.info(f"[SSE] Tool info: name={metadata.get('tool_name')}, status={metadata.get('status')}")
                if 'args' in metadata:
                    logger.info(f"[SSE] Tool args: {metadata['args']}")
                if 'result' in metadata:
                    result_preview = str(metadata['result'])[:200]
                    logger.info(f"[SSE] Tool result preview: {result_preview}")

            event_data = json.dumps(chunk, ensure_ascii=False)
            yield f"data: {event_data}\n\n"

        # Save assistant message to database (create new session)
        if assistant_content:
            async with async_session_maker() as db:
                assistant_message = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_content,
                    metadata={}
                )
                db.add(assistant_message)
                await db.commit()
                logger.info(f"[SSE] Saved assistant message to conversation {conversation_id}")

        # Send completion signal
        yield f"data: {json.dumps({'type': 'done', 'content': '', 'metadata': {}})}\n\n"

    except Exception as e:
        logger.error(f"Error in SSE stream: {e}", exc_info=True)
        error_data = json.dumps({
            "type": "error",
            "content": f"Error: {str(e)}",
            "metadata": {"error": str(e)}
        })
        yield f"data: {error_data}\n\n"


@router.get("/chat/{conversation_id}/stream")
async def stream_chat(
    conversation_id: str,
    task: str,
    database_name: str | None = None,
    current_user: User = Depends(get_user_from_token_or_header),
    db: AsyncSession = Depends(get_db),
):
    """
    SSE endpoint for streaming chat responses.

    Query Parameters:
        task: The user's message/task to execute
        database_name: Optional database connection name for context

    Response: text/event-stream with JSON data events

    Example usage:
        GET /api/sse/chat/{conversation_id}/stream?task=Hello&database_name=share_ai

    Client receives:
        data: {"type": "thinking", "content": "Processing...", "metadata": {}}

        data: {"type": "chunk", "content": "Hello! How can I help?", "metadata": {}}

        data: {"type": "complete", "content": "...", "metadata": {}}

        data: {"type": "done", "content": "", "metadata": {}}
    """
    # Verify conversation exists
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task parameter is required"
        )

    # Load conversation history (last 50 messages for context)
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .limit(50)
    )
    messages = messages_result.scalars().all()

    # Convert to chat history format
    chat_history = [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]

    logger.info(f"Loaded {len(chat_history)} messages from conversation {conversation_id}")

    # Create conversation service
    conversation_service = AsyncConversationService()

    # Save user message to database
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=task,
        metadata={"database_name": database_name} if database_name else None
    )
    db.add(user_message)
    await db.commit()

    # Return SSE stream (with history)
    return StreamingResponse(
        event_generator(
            conversation_id,
            task,
            conversation_service,
            current_user.id,
            database_name,
            chat_history,  # ← 传入历史消息
        ),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/chat/{conversation_id}/message")
async def send_message_sse(
    conversation_id: str,
    task: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Alternative endpoint: POST version for sending messages and getting SSE stream.

    Body:
        task: str - The user's message

    Returns SSE stream same as GET endpoint.
    """
    # Verify conversation exists
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is required"
        )

    # Create conversation service
    conversation_service = AsyncConversationService()

    # Return SSE stream
    return StreamingResponse(
        event_generator(conversation_id, task, conversation_service),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
