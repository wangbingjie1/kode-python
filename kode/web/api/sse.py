"""
SSE (Server-Sent Events) API Routes

Provides real-time streaming of AI responses using SSE instead of WebSocket.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import AsyncGenerator, Optional, Dict, Any
from pydantic import BaseModel
import json
import logging

from kode.database.session import get_db
from kode.models import Conversation, Message, User
from kode.services.conversation import AsyncConversationService
from kode.services.billing_service import BillingService
from kode.utils.logger import setup_logger
from kode.web.dependencies import get_current_user
from kode.web.middleware.quota_check import check_user_quota
from kode.core.security import verify_token

logger = setup_logger(__name__)
router = APIRouter()


# ============================================================
# Global session manager for pending user inputs
# ============================================================
class UserInputSessionManager:
    """
    管理等待用户输入的会话。

    当 Agent 调用 AskUserTool 时，会在这里注册等待的工具实例。
    前端通过 POST 端点提交答案后，通过此管理器注入响应。
    """
    def __init__(self):
        self._pending_sessions: Dict[str, Any] = {}  # conversation_id -> tool_instance

    def register_pending_input(self, conversation_id: str, tool_instance: Any):
        """注册等待用户输入的会话"""
        self._pending_sessions[conversation_id] = tool_instance
        logger.info(f"[UserInputSession] Registered pending input for conversation {conversation_id}")

    def get_pending_input(self, conversation_id: str) -> Optional[Any]:
        """获取等待中的工具实例"""
        return self._pending_sessions.get(conversation_id)

    def remove_pending_input(self, conversation_id: str):
        """移除已完成的会话"""
        if conversation_id in self._pending_sessions:
            del self._pending_sessions[conversation_id]
            logger.info(f"[UserInputSession] Removed pending input for conversation {conversation_id}")

    async def submit_user_response(self, conversation_id: str, response_data: Dict[str, Any]) -> bool:
        """
        提交用户响应到等待中的工具实例。

        Returns:
            True if response was submitted successfully, False if no pending session
        """
        tool_instance = self.get_pending_input(conversation_id)
        if not tool_instance:
            logger.warning(f"[UserInputSession] No pending input found for conversation {conversation_id}")
            return False

        # Inject response into tool instance
        if hasattr(tool_instance, '_set_user_response'):
            await tool_instance._set_user_response(response_data)
            self.remove_pending_input(conversation_id)
            return True
        else:
            logger.error(f"[UserInputSession] Tool instance does not have _set_user_response method")
            return False


# Global instance
user_input_session_manager = UserInputSessionManager()


# ============================================================
# Pydantic models for API
# ============================================================
class UserInputResponse(BaseModel):
    """用户输入响应模型"""
    answer: Any  # 可以是 str, bool, list[str] 等
    question_type: str = "text"  # text, select, multiselect, confirm


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
    messages_to_save = []  # 收集需要保存的所有消息 (包括 chart, insight 等)

    # ✨ 收集真实的 token 使用量（来自 Anthropic API）
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_creation_tokens = 0
    total_cache_read_tokens = 0

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

            # Handle user_input_required event (special case)
            if chunk_type == "user_input_required":
                metadata = chunk.get("metadata", {})
                question_data = metadata.get("question_data", {})

                # Extract tool instance from exception (if available in metadata)
                # This should be set by anthropic_streaming.py when catching UserInputRequired
                # For now, we'll register the conversation as pending and wait
                logger.info(f"[SSE] User input required: {question_data.get('question')}")

                # Send event to frontend immediately
                event_data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

                # Note: The tool instance is already waiting via asyncio.Event
                # We don't need to register it here, it's managed in anthropic_streaming.py
                continue

            # ✨ 收集真实的 token 统计（来自 Anthropic API）
            if chunk_type == "token_usage":
                metadata = chunk.get("metadata", {})
                total_input_tokens += metadata.get("input_tokens", 0)
                total_output_tokens += metadata.get("output_tokens", 0)
                total_cache_creation_tokens += metadata.get("cache_creation_input_tokens", 0)
                total_cache_read_tokens += metadata.get("cache_read_input_tokens", 0)
                logger.info(
                    f"[SSE Token] Iteration {metadata.get('iteration')}: "
                    f"input={metadata.get('input_tokens')}, "
                    f"output={metadata.get('output_tokens')}, "
                    f"cache_creation={metadata.get('cache_creation_input_tokens')}, "
                    f"cache_read={metadata.get('cache_read_input_tokens')}"
                )

            # Collect assistant response content
            if chunk_type == "chunk":
                assistant_content += chunk.get("content", "")

            # Collect chart messages for persistence
            elif chunk_type == "chart":
                messages_to_save.append({
                    "role": "chart",
                    "content": "",
                    "metadata": {
                        "chart_type": chunk.get("metadata", {}).get("chart_type"),
                        "chart_config": chunk.get("content"),  # ECharts config
                        "data_summary": chunk.get("metadata", {}).get("data_summary")
                    }
                })
                logger.info(f"[SSE] Collected chart message for saving")

            # Collect insight messages for persistence
            elif chunk_type == "insight":
                messages_to_save.append({
                    "role": "insight",
                    "content": "",
                    "metadata": {
                        "insights": chunk.get("content"),  # List of insights
                        "total_count": chunk.get("metadata", {}).get("total_count"),
                        "data_summary": chunk.get("metadata", {}).get("data_summary")
                    }
                })
                logger.info(f"[SSE] Collected insight message for saving")

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

        # Save all messages to database (create new session)
        async with async_session_maker() as db:
            # Save assistant message
            if assistant_content:
                assistant_message = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_content,
                    metadata={}
                )
                db.add(assistant_message)
                logger.info(f"[SSE] Saved assistant message to conversation {conversation_id}")

            # Save chart/insight messages
            for msg_data in messages_to_save:
                message = Message(
                    conversation_id=conversation_id,
                    role=msg_data["role"],
                    content=msg_data["content"],
                    metadata=msg_data["metadata"]
                )
                db.add(message)
                logger.info(f"[SSE] Saved {msg_data['role']} message to conversation {conversation_id}")

            await db.commit()

            # ✨ 更新使用量统计（使用真实的 Anthropic API token 数据）
            actual_tokens = total_input_tokens + total_output_tokens

            # 💰 计算真实成本（Anthropic 定价，< 200K tokens）
            # 参考: https://www.anthropic.com/pricing
            regular_input_tokens = total_input_tokens - total_cache_creation_tokens - total_cache_read_tokens
            regular_input_cost = regular_input_tokens * 3 / 1_000_000  # $3/MTok
            cache_creation_cost = total_cache_creation_tokens * 3.75 / 1_000_000  # $3.75/MTok (1.25×)
            cache_read_cost = total_cache_read_tokens * 0.30 / 1_000_000  # $0.30/MTok (节省90%)
            output_cost = total_output_tokens * 15 / 1_000_000  # $15/MTok

            actual_cost = regular_input_cost + cache_creation_cost + cache_read_cost + output_cost

            # 计算无缓存的成本（对比）
            no_cache_input_cost = (regular_input_tokens + total_cache_creation_tokens + total_cache_read_tokens) * 3 / 1_000_000
            no_cache_cost = no_cache_input_cost + output_cost

            # 节省的成本和百分比
            cost_savings = no_cache_cost - actual_cost
            savings_percentage = (cost_savings / no_cache_cost * 100) if no_cache_cost > 0 else 0

            try:
                await BillingService.increment_usage(
                    db=db,
                    user_id=user_id,
                    token_count=actual_tokens,
                    database_query_count=0,
                )

                # 详细的开发日志（包含成本信息）
                logger.info(
                    f"\n{'='*80}\n"
                    f"[SSE Usage Summary] Conversation {conversation_id}\n"
                    f"{'='*80}\n"
                    f"📊 Token 统计:\n"
                    f"  常规输入:   {regular_input_tokens:>8,} tokens × $3.00/MTok  = ${regular_input_cost:>8.6f}\n"
                    f"  缓存创建:   {total_cache_creation_tokens:>8,} tokens × $3.75/MTok  = ${cache_creation_cost:>8.6f}\n"
                    f"  缓存读取:   {total_cache_read_tokens:>8,} tokens × $0.30/MTok  = ${cache_read_cost:>8.6f}\n"
                    f"  输出生成:   {total_output_tokens:>8,} tokens × $15.00/MTok = ${output_cost:>8.6f}\n"
                    f"  ─────────────────────────────────────────────────────────────\n"
                    f"  总输入:     {total_input_tokens:>8,} tokens\n"
                    f"  总输出:     {total_output_tokens:>8,} tokens\n"
                    f"  总计:       {actual_tokens:>8,} tokens\n"
                    f"\n"
                    f"💰 成本分析:\n"
                    f"  实际成本:   ${actual_cost:.6f}\n"
                    f"  无缓存成本: ${no_cache_cost:.6f}\n"
                    f"  节省:       ${cost_savings:.6f} ({savings_percentage:.1f}%)\n"
                    f"\n"
                    f"📦 用户配额扣除: {actual_tokens:,} tokens (简化计费)\n"
                    f"{'='*80}"
                )
            except Exception as e:
                # 使用量更新失败不应该影响主流程
                logger.warning(f"[SSE] Failed to update usage: {e}")

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
    # 检查用户配额
    await check_user_quota(current_user.id, db)

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


@router.post("/chat/{conversation_id}/user-response")
async def submit_user_response(
    conversation_id: str,
    response: UserInputResponse = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    接收用户对交互式提问的响应。

    当 Agent 调用 AskUserTool 后，前端会收到 'user_input_required' 事件。
    用户提交答案后，前端调用此端点将答案注入到等待中的工具实例。

    **Request Body**:
    ```json
    {
      "answer": "用户的回答" | true | false | ["选项1", "选项2"],
      "question_type": "text" | "select" | "multiselect" | "confirm"
    }
    ```

    **Returns**:
    ```json
    {
      "success": true,
      "message": "用户响应已提交"
    }
    ```

    **Flow**:
    1. Agent 调用 AskUserTool
    2. 异常被捕获，工具实例注册到全局 session manager
    3. SSE 发送 'user_input_required' 事件到前端
    4. 前端渲染问题界面，用户作答
    5. 前端调用此端点提交答案
    6. 答案注入到工具实例，asyncio.Event.set() 被调用
    7. Agent 继续执行
    """
    # Verify conversation exists and user has access
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    # TODO: Verify user owns this conversation (add owner_id to Conversation model)

    # Submit response to session manager
    logger.info(f"[User Response] Received for conversation {conversation_id}: {response.dict()}")

    success = await user_input_session_manager.submit_user_response(
        conversation_id,
        response.dict()
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending user input found for this conversation. The question may have already timed out."
        )

    logger.info(f"[User Response] Successfully submitted for conversation {conversation_id}")

    return {
        "success": True,
        "message": "用户响应已提交",
        "conversation_id": conversation_id,
    }
