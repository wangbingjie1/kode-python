"""
SSE (Server-Sent Events) API Routes

Provides real-time streaming of AI responses using SSE instead of WebSocket.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import AsyncGenerator
import json
import logging

from kode.database.session import get_db
from kode.models import Conversation, Message
from kode.services.conversation import AsyncConversationService
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


async def event_generator(
    conversation_id: str,
    task_content: str,
    conversation_service: AsyncConversationService,
    database_name: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for streaming AI responses.

    SSE format:
    data: {"type": "thinking", "content": "...", "metadata": {}}

    data: {"type": "chunk", "content": "...", "metadata": {}}

    data: {"type": "complete", "content": "...", "metadata": {}}

    """
    try:
        async for chunk in conversation_service.execute_task_streaming(
            task=task_content,
            conversation_id=conversation_id,
            user_id="default",  # TODO: Get from auth
            database_name=database_name,
        ):
            # Format as SSE event
            chunk_type = chunk.get('type')
            logger.info(f"[SSE] Sending chunk: type={chunk_type}")

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

    # Create conversation service
    conversation_service = AsyncConversationService()

    # Return SSE stream
    return StreamingResponse(
        event_generator(conversation_id, task, conversation_service, database_name),
        media_type="text/event-stream",
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
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
