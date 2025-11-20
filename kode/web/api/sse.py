"""
SSE (Server-Sent Events) API Routes

Provides real-time streaming of AI responses using SSE instead of WebSocket.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import AsyncGenerator, Optional, Dict, Any
from pydantic import BaseModel, Field
import asyncio
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
# Helper function for serializing chunks
# ============================================================
def serialize_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 chunk 中的不可序列化对象转换为可 JSON 序列化的字典。

    主要处理 Anthropic SDK 返回的特殊对象如 ThinkingBlock, ToolUseBlock 等。
    """

    def convert_value(v):
        # 处理 Anthropic SDK 对象（有 model_dump 方法）
        if hasattr(v, "model_dump"):
            return v.model_dump()
        # 处理字典
        elif isinstance(v, dict):
            return {k: convert_value(val) for k, val in v.items()}
        # 处理列表
        elif isinstance(v, list):
            return [convert_value(item) for item in v]
        # 其他类型直接返回
        else:
            return v

    return convert_value(chunk)


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
        logger.info(
            f"[UserInputSession] Registered pending input for conversation {conversation_id}"
        )

    def get_pending_input(self, conversation_id: str) -> Optional[Any]:
        """获取等待中的工具实例"""
        return self._pending_sessions.get(conversation_id)

    def remove_pending_input(self, conversation_id: str):
        """移除已完成的会话"""
        if conversation_id in self._pending_sessions:
            del self._pending_sessions[conversation_id]
            logger.info(
                f"[UserInputSession] Removed pending input for conversation {conversation_id}"
            )

    async def submit_user_response(
        self, conversation_id: str, response_data: Dict[str, Any]
    ) -> bool:
        """
        提交用户响应到等待中的工具实例。

        Returns:
            True if response was submitted successfully, False if no pending session
        """
        tool_instance = self.get_pending_input(conversation_id)
        if not tool_instance:
            logger.warning(
                f"[UserInputSession] No pending input found for conversation {conversation_id}"
            )
            return False

        # Inject response into tool instance
        if hasattr(tool_instance, "_set_user_response"):
            await tool_instance._set_user_response(response_data)
            self.remove_pending_input(conversation_id)
            return True
        else:
            logger.error(
                f"[UserInputSession] Tool instance does not have _set_user_response method"
            )
            return False


# Global instance
user_input_session_manager = UserInputSessionManager()


# ============================================================
# Global streaming session manager
# ============================================================
class StreamingSessionManager:
    """
    管理活跃的SSE streaming会话。

    支持终止正在进行的流式响应和追加新消息。
    """

    def __init__(self):
        self._active_sessions: Dict[str, Dict[str, Any]] = {}  # conversation_id -> session_data

    def register_session(
        self, conversation_id: str, cancel_event: asyncio.Event, message_queue: asyncio.Queue
    ):
        """注册一个活跃的streaming会话"""
        self._active_sessions[conversation_id] = {
            "cancel_event": cancel_event,
            "message_queue": message_queue,
            "created_at": asyncio.get_event_loop().time(),
        }
        logger.info(f"[StreamingSession] Registered session for conversation {conversation_id}")

    def get_session(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        return self._active_sessions.get(conversation_id)

    def remove_session(self, conversation_id: str):
        """移除会话"""
        if conversation_id in self._active_sessions:
            del self._active_sessions[conversation_id]
            logger.info(f"[StreamingSession] Removed session for conversation {conversation_id}")

    def cancel_session(self, conversation_id: str) -> bool:
        """
        终止指定的streaming会话。

        Returns:
            True if session was cancelled, False if session not found
        """
        session = self.get_session(conversation_id)
        if not session:
            logger.warning(
                f"[StreamingSession] No active session found for conversation {conversation_id}"
            )
            return False

        # Set cancel event
        cancel_event = session["cancel_event"]
        cancel_event.set()
        logger.info(f"[StreamingSession] Cancelled session for conversation {conversation_id}")
        return True

    async def append_message(self, conversation_id: str, message: str) -> bool:
        """
        向活跃的streaming会话追加新消息。

        Args:
            conversation_id: 会话ID
            message: 要追加的消息内容

        Returns:
            True if message was appended, False if session not found
        """
        session = self.get_session(conversation_id)
        if not session:
            logger.warning(
                f"[StreamingSession] No active session found for conversation {conversation_id}"
            )
            return False

        # Put message into queue
        message_queue = session["message_queue"]
        await message_queue.put(
            {
                "role": "user",
                "content": message,
            }
        )
        logger.info(f"[StreamingSession] Appended message to conversation {conversation_id}")
        return True


# Global instance
streaming_session_manager = StreamingSessionManager()


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
    new_title: str | None = None,  # 新增：标题更新
    user_message_sequence: int = 0,  # 新增：user 消息的序列号（用于后续递增）
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for streaming AI responses.

    SSE format:
    data: {"type": "thinking", "content": "...", "metadata": {}}

    data: {"type": "chunk", "content": "...", "metadata": {}}

    data: {"type": "complete", "content": "...", "metadata": {}}

    """
    # 创建取消事件和消息队列
    cancel_event = asyncio.Event()
    message_queue = asyncio.Queue()

    # 注册streaming会话
    streaming_session_manager.register_session(conversation_id, cancel_event, message_queue)

    # 如果有新标题，先发送标题更新事件
    if new_title:
        title_update_data = json.dumps(
            {
                "type": "title_updated",
                "content": new_title,
                "metadata": {"conversation_id": conversation_id},
            },
            ensure_ascii=False,
        )
        yield f"data: {title_update_data}\n\n"
        logger.info(f"[SSE] Sent title update: {new_title}")

    # 最外层异常捕获：确保所有错误（包括初始化阶段）都能被正确处理
    try:
        from kode.database.session import async_session_maker
        from kode.services.api_trace_service import api_trace_service

        assistant_content = ""  # 收集完整的 AI 回复
        assistant_metadata = {}  # 收集 assistant 消息的 metadata（chart, insight 等）

        # ✨ 收集真实的 token 使用量（来自 Anthropic API）
        total_input_tokens = 0
        total_output_tokens = 0
        total_cache_creation_tokens = 0
        total_cache_read_tokens = 0

        # 🔍 API 调用追踪（用于上下文工程优化）
        current_iteration = 0
        api_traces = []  # 记录每次迭代的调用

        # 📝 收集所有消息（文本块 + 工具调用），按顺序保存
        all_messages = []  # List of Message objects to save (in order)
        message_sequence = user_message_sequence  # 从 user 消息的序列号开始递增

        # 将cancel_event和message_queue传递给conversation_service
        async for chunk in conversation_service.execute_task_streaming(
            task=task_content,
            conversation_id=conversation_id,
            user_id=user_id,
            database_name=database_name,
            chat_history=chat_history or [],  # ← 传入历史消息
            cancel_event=cancel_event,  # ← 传入取消事件
            message_queue=message_queue,  # ← 传入消息队列
        ):
            # Format as SSE event
            chunk_type = chunk.get("type")
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
                # Serialize chunk to handle non-JSON serializable objects
                serialized_chunk = serialize_chunk(chunk)
                event_data = json.dumps(serialized_chunk, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

                # Note: The tool instance is already waiting via asyncio.Event
                # We don't need to register it here, it's managed in anthropic_streaming.py
                continue

            # ✨ 收集真实的 token 统计（来自 Anthropic API）
            if chunk_type == "token_usage":
                metadata = chunk.get("metadata", {})
                iteration_num = metadata.get("iteration", 1)

                # 累加总量
                total_input_tokens += metadata.get("input_tokens", 0)
                total_output_tokens += metadata.get("output_tokens", 0)
                total_cache_creation_tokens += metadata.get("cache_creation_input_tokens", 0)
                total_cache_read_tokens += metadata.get("cache_read_input_tokens", 0)

                logger.info(
                    f"[SSE Token] Iteration {iteration_num}: "
                    f"input={metadata.get('input_tokens')}, "
                    f"output={metadata.get('output_tokens')}, "
                    f"cache_creation={metadata.get('cache_creation_input_tokens')}, "
                    f"cache_read={metadata.get('cache_read_input_tokens')}"
                )

                # 🔍 创建本次迭代的追踪记录
                trace = api_trace_service.create_trace(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    model_name=metadata.get("model", "claude-sonnet-4-5"),
                    iteration=iteration_num,
                )
                trace.set_token_usage(
                    input_tokens=metadata.get("input_tokens", 0),
                    output_tokens=metadata.get("output_tokens", 0),
                    cache_creation_tokens=metadata.get("cache_creation_input_tokens", 0),
                    cache_read_tokens=metadata.get("cache_read_input_tokens", 0),
                )

                # 设置上下文摘要
                if chat_history:
                    total_chars = sum(len(msg.get("content", "")) for msg in chat_history)
                    trace.set_context_summary(
                        history_count=len(chat_history),
                        total_context_chars=total_chars,
                    )

                # 🔍 设置完整的请求和响应内容
                request_data = metadata.get("request_data")
                response_data = metadata.get("response_data")
                if request_data:
                    trace.set_request_content(
                        system_prompt=request_data.get("system", ""),
                        messages=request_data.get("messages", []),
                        tools=request_data.get("tools", []),
                    )
                if response_data:
                    trace.set_response_content(
                        content=response_data.get("content", ""),
                        stop_reason=response_data.get("stop_reason", ""),
                        usage=response_data.get("usage", {}),
                    )

                api_traces.append(trace)
                current_iteration = iteration_num

            # ✨ 处理文本块事件（按 content_blocks 顺序发送的）
            if chunk_type == "text_block":
                text_content = chunk.get("content", "")
                if text_content:
                    # 立即保存文本块为 assistant 消息
                    message_sequence += 1
                    text_msg = Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=text_content,
                        sequence=message_sequence,
                        message_metadata={
                            "type": "text",  # 标记为文本块
                            "iteration": current_iteration,
                        },
                    )
                    all_messages.append(text_msg)
                    logger.info(f"[SSE] Text block saved at sequence {message_sequence}")

            # Collect assistant response content (用于最终统计，但不再单独保存)
            elif chunk_type == "chunk":
                assistant_content += chunk.get("content", "")
            elif chunk_type == "thinking":
                # ✨ Extended Thinking 内容
                thinking_text = chunk.get("content", "")
                assistant_content += f"\n\n[思考]\n{thinking_text}\n"

            # Collect chart data into metadata (NOT as separate message)
            elif chunk_type == "chart":
                if "charts" not in assistant_metadata:
                    assistant_metadata["charts"] = []
                assistant_metadata["charts"].append(
                    {
                        "chart_type": chunk.get("metadata", {}).get("chart_type"),
                        "chart_config": chunk.get("content"),  # ECharts config
                        "data_summary": chunk.get("metadata", {}).get("data_summary"),
                    }
                )
                logger.info(f"[SSE] Collected chart data into metadata")

            # Collect insight data into metadata (NOT as separate message)
            elif chunk_type == "insight":
                if "insights" not in assistant_metadata:
                    assistant_metadata["insights"] = []
                assistant_metadata["insights"].append(
                    {
                        "insights": chunk.get("content"),  # List of insights
                        "total_count": chunk.get("metadata", {}).get("total_count"),
                        "data_summary": chunk.get("metadata", {}).get("data_summary"),
                    }
                )
                logger.info(f"[SSE] Collected insight data into metadata")

            # 📝 保存工具调用消息到列表（稍后批量保存到数据库）
            if chunk_type == "tool_call":
                metadata = chunk.get("metadata", {})
                tool_name = metadata.get("tool_name")
                tool_args = metadata.get("args", {})
                tool_use_id = metadata.get("tool_use_id")

                logger.info(
                    f"[SSE] Tool call: name={tool_name}, id={tool_use_id}, status={metadata.get('status')}"
                )
                logger.info(f"[SSE] Tool args: {tool_args}")

                # 创建 tool_use 消息
                message_sequence += 1
                tool_use_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",  # tool_use 属于 assistant 的一部分
                    content="",  # content 为空字符串，数据在 metadata 中
                    sequence=message_sequence,  # ← 确保顺序
                    message_metadata={
                        "type": "tool_use",
                        "tool_use_id": tool_use_id,  # ← 保存 tool_use_id
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "iteration": current_iteration,
                    },
                )
                all_messages.append(tool_use_msg)

            # 📝 保存用户输入响应消息（当用户回答问题后）
            elif chunk_type == "user_input_received":
                metadata = chunk.get("metadata", {})
                user_answer = chunk.get("content", "")

                # 格式化 user_answer 为可读文本
                if isinstance(user_answer, dict):
                    # 如果是批量问答格式 {"answers": {...}}
                    if "answers" in user_answer:
                        answer_count = len(user_answer["answers"])
                        answer_text = f"已提交 {answer_count} 个问题的回答"
                    else:
                        answer_text = str(user_answer)
                elif isinstance(user_answer, str):
                    answer_text = user_answer
                else:
                    answer_text = str(user_answer)

                logger.info(
                    f"[SSE] User input received: {answer_text[:100]}"
                )

                # 创建 user 消息记录用户的回答
                message_sequence += 1
                user_answer_msg = Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=f"回答: {answer_text}",
                    sequence=message_sequence,
                    message_metadata={
                        "type": "user_answer",
                        "tool_name": metadata.get("tool_name"),
                        "question": metadata.get("question"),
                        "iteration": current_iteration,
                    },
                )
                all_messages.append(user_answer_msg)

            elif chunk_type == "tool_result":
                metadata = chunk.get("metadata", {})
                tool_name = metadata.get("tool_name")
                tool_use_id = metadata.get("tool_use_id")
                result = metadata.get("result", "")
                result_preview = str(result)[:200]

                logger.info(
                    f"[SSE] Tool result: name={tool_name}, id={tool_use_id}, status={metadata.get('status')}"
                )
                logger.info(f"[SSE] Tool result preview: {result_preview}")

                # 创建 tool_result 消息
                message_sequence += 1
                tool_result_msg = Message(
                    conversation_id=conversation_id,
                    role="user",  # tool_result 作为 user 角色传回给模型
                    content=result,  # 工具结果存储在 content 中
                    sequence=message_sequence,  # ← 确保顺序
                    message_metadata={
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,  # ← 保存 tool_use_id，用于关联
                        "tool_name": tool_name,
                        "tool_args": metadata.get("tool_args", {}),
                        "status": metadata.get("status", "completed"),
                        "iteration": current_iteration,
                    },
                )
                all_messages.append(tool_result_msg)

            # Serialize chunk to handle non-JSON serializable objects (e.g., ThinkingBlock)
            serialized_chunk = serialize_chunk(chunk)

            # 特别处理 chart 类型：确保 content 是对象而不是字符串
            if chunk_type == "chart" and isinstance(serialized_chunk.get("content"), str):
                try:
                    serialized_chunk["content"] = json.loads(serialized_chunk["content"])
                    logger.info(f"[SSE] Deserialized chart config string to object")
                except json.JSONDecodeError:
                    logger.error(f"[SSE] Chart content is string but not valid JSON")

            event_data = json.dumps(serialized_chunk, ensure_ascii=False)
            yield f"data: {event_data}\n\n"

        # Save all messages to database (create new session)
        async with async_session_maker() as db:
            # 📝 保存所有消息（文本块 + 工具调用），已按顺序排列
            if all_messages:
                for msg in all_messages:
                    db.add(msg)
                logger.info(
                    f"[SSE] Saved {len(all_messages)} messages (text blocks + tools) to conversation {conversation_id}"
                )

            # ✨ 保存最终的 assistant 消息（包含 token 统计和 metadata）
            # 注意：这条消息只用于记录 token 使用量和 charts/insights，不包含实际文本内容
            # 实际文本内容已经在上面的 text_block 消息中保存了
            if total_input_tokens > 0 or total_output_tokens > 0:
                message_sequence += 1
                final_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content="",  # 内容为空，只用于记录 token 和 metadata
                    sequence=message_sequence,
                    message_metadata={
                        "type": "final",  # 标记为最终统计消息
                        **assistant_metadata,  # Contains charts, insights, etc.
                    },
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    cache_creation_tokens=total_cache_creation_tokens,
                    cache_read_tokens=total_cache_read_tokens,
                )
                db.add(final_msg)
                logger.info(
                    f"[SSE] Saved final message (token stats) to conversation {conversation_id} "
                    f"with {total_input_tokens + total_output_tokens} tokens"
                )

            await db.commit()

            # ✨ 更新使用量统计（使用真实的 Anthropic API token 数据）
            actual_tokens = total_input_tokens + total_output_tokens

            # 💰 计算真实成本（Anthropic 定价，< 200K tokens）
            # 参考: https://www.anthropic.com/pricing
            regular_input_tokens = (
                total_input_tokens - total_cache_creation_tokens - total_cache_read_tokens
            )
            regular_input_cost = regular_input_tokens * 3 / 1_000_000  # $3/MTok
            cache_creation_cost = (
                total_cache_creation_tokens * 3.75 / 1_000_000
            )  # $3.75/MTok (1.25×)
            cache_read_cost = total_cache_read_tokens * 0.30 / 1_000_000  # $0.30/MTok (节省90%)
            output_cost = total_output_tokens * 15 / 1_000_000  # $15/MTok

            actual_cost = regular_input_cost + cache_creation_cost + cache_read_cost + output_cost

            # 计算无缓存的成本（对比）
            no_cache_input_cost = (
                (regular_input_tokens + total_cache_creation_tokens + total_cache_read_tokens)
                * 3
                / 1_000_000
            )
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

                # 🔍 完成并保存所有追踪记录到数据库
                for trace in api_traces:
                    trace.finalize()
                    # 使用异步保存（当前在 async 上下文中，db 是异步会话）
                    await api_trace_service.save_trace_async(trace, db)

                logger.info(
                    f"[API Trace] Saved {len(api_traces)} trace records to database for conversation {conversation_id}"
                )

            except Exception as e:
                # 使用量更新失败不应该影响主流程
                logger.warning(f"[SSE] Failed to update usage: {e}")

        # Send completion signal
        yield f"data: {json.dumps({'type': 'done', 'content': '', 'metadata': {}}, ensure_ascii=False)}\n\n"

    except asyncio.CancelledError:
        # 用户主动取消了streaming
        logger.info(f"[SSE] Streaming cancelled by user for conversation {conversation_id}")
        cancel_data = json.dumps(
            {
                "type": "cancelled",
                "content": "用户已终止响应",
                "metadata": {"reason": "user_cancelled"},
            },
            ensure_ascii=False,
        )
        yield f"data: {cancel_data}\n\n"

    except Exception as e:
        from kode.utils.logger import safe_log_exception

        error_message = str(e)
        safe_log_exception(logger, f"Error in SSE stream: {error_message}", e)

        error_data = json.dumps(
            {
                "type": "error",
                "content": f"Error: {error_message}",
                "metadata": {"error": error_message},
            },
            ensure_ascii=False,
        )
        yield f"data: {error_data}\n\n"

    finally:
        # 清理会话
        streaming_session_manager.remove_session(conversation_id)
        logger.info(f"[SSE] Removed streaming session for conversation {conversation_id}")


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
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Task parameter is required"
        )

    # Load conversation history (last 100 messages for context, to include tool calls)
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sequence)
        .limit(100)
    )
    messages = messages_result.scalars().all()

    # Convert to Anthropic API chat history format
    # 需要重建包含 tool_use 和 tool_result 的完整消息流
    # Convert to Anthropic API chat history format
    # 需要重建包含 tool_use 和 tool_result 的完整消息流
    chat_history = []
    current_assistant_content = []  # List of blocks for current assistant message

    for msg in messages:
        msg_type = msg.message_metadata.get("type") if msg.message_metadata else None

        # 1. Handle Tool Result (User Role)
        if msg_type == "tool_result":
            # Flush pending assistant content first
            if current_assistant_content:
                chat_history.append({"role": "assistant", "content": current_assistant_content})
                current_assistant_content = []

            # Add tool result message
            tool_use_id = msg.message_metadata.get("tool_use_id")
            if tool_use_id and isinstance(tool_use_id, str):
                chat_history.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": msg.content or "",
                            }
                        ],
                    }
                )
            else:
                logger.warning(
                    f"Invalid tool_use_id in tool_result message {msg.id}: {tool_use_id}, skipping"
                )

        # 2. Handle Assistant Messages (Text or Tool Use)
        elif msg.role == "assistant":
            if msg_type == "tool_use":
                # Tool Use Block
                tool_use_id = msg.message_metadata.get("tool_use_id")
                if tool_use_id and isinstance(tool_use_id, str):
                    current_assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": tool_use_id,
                            "name": msg.message_metadata.get("tool_name"),
                            "input": msg.message_metadata.get("tool_args", {}),
                        }
                    )
                else:
                    logger.warning(
                        f"Invalid tool_use_id in message {msg.id}: {tool_use_id}, skipping tool_use block"
                    )
            elif msg_type == "final":
                # Skip final stats message (it has no content)
                pass
            else:
                # Text Block (default)
                if msg.content:
                    current_assistant_content.append({"type": "text", "text": msg.content})

        # 3. Handle User Messages (Text)
        elif msg.role == "user":
            # Flush pending assistant content first
            if current_assistant_content:
                chat_history.append({"role": "assistant", "content": current_assistant_content})
                current_assistant_content = []

            if msg.content:
                chat_history.append({"role": "user", "content": msg.content})

    # Flush remaining assistant content
    if current_assistant_content:
        chat_history.append({"role": "assistant", "content": current_assistant_content})

    logger.info(
        f"Loaded {len(messages)} raw messages, converted to {len(chat_history)} Anthropic API messages"
    )

    # Create conversation service
    conversation_service = AsyncConversationService()

    # Get current max sequence for this conversation
    max_seq_result = await db.execute(
        select(func.max(Message.sequence)).where(Message.conversation_id == conversation_id)
    )
    max_seq = max_seq_result.scalar() or -1  # Start from 0 if no messages
    next_seq = max_seq + 1

    # Save user message to database
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=task,
        sequence=next_seq,
        message_metadata={"database_name": database_name} if database_name else None,
    )
    db.add(user_message)
    await db.commit()

    # Generate conversation title if this is the first message
    new_title = None
    is_first_message = len(chat_history) == 0
    if is_first_message and conversation.title in ("New Conversation", "New chat", "新对话"):
        try:
            # Generate title asynchronously (don't block the stream)
            new_title = await conversation_service.generate_conversation_title(task)
            conversation.title = new_title
            db.add(conversation)
            await db.commit()
            logger.info(f"Updated conversation {conversation_id} title to: {new_title}")
        except Exception as e:
            logger.warning(f"Failed to generate conversation title: {e}")

    # Return SSE stream (with history)
    return StreamingResponse(
        event_generator(
            conversation_id,
            task,
            conversation_service,
            current_user.id,
            database_name,
            chat_history,  # ← 传入历史消息
            new_title,  # ← 传入新标题（如果有）
            next_seq,  # ← 传入 user 消息的序列号
        ),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
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
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    if not task:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is required")

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
        },
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
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    # TODO: Verify user owns this conversation (add owner_id to Conversation model)

    # Submit response to session manager
    logger.info(f"[User Response] Received for conversation {conversation_id}: {response.dict()}")

    success = await user_input_session_manager.submit_user_response(
        conversation_id, response.dict()
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending user input found for this conversation. The question may have already timed out.",
        )

    logger.info(f"[User Response] Successfully submitted for conversation {conversation_id}")

    return {
        "success": True,
        "message": "用户响应已提交",
        "conversation_id": conversation_id,
    }


@router.post("/chat/{conversation_id}/cancel")
async def cancel_streaming(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    终止正在进行的streaming响应。

    **使用场景**:
    - 用户不想等待完整的AI响应
    - 用户发现AI执行错误的任务
    - 用户想要重新开始对话

    **Returns**:
    ```json
    {
      "success": true,
      "message": "已终止streaming会话"
    }
    ```
    """
    # Verify conversation exists and user has access
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    # Cancel the streaming session
    success = streaming_session_manager.cancel_session(conversation_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="没有找到活跃的streaming会话"
        )

    logger.info(f"[Cancel] Successfully cancelled streaming for conversation {conversation_id}")

    return {
        "success": True,
        "message": "已终止streaming会话",
        "conversation_id": conversation_id,
    }


class AppendMessageRequest(BaseModel):
    """追加消息请求模型"""

    content: str = Field(..., description="要追加的消息内容")


@router.post("/chat/{conversation_id}/append")
async def append_message_to_stream(
    conversation_id: str,
    request: AppendMessageRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    向正在进行的streaming会话追加新消息。

    **使用场景**:
    - AI正在执行任务,用户想要补充指令
    - AI询问了问题,用户提供额外信息
    - 多轮交互中的实时补充

    **Request Body**:
    ```json
    {
      "content": "补充的指令或信息"
    }
    ```

    **Returns**:
    ```json
    {
      "success": true,
      "message": "消息已追加到streaming会话"
    }
    ```

    **注意**: 追加的消息会在AI完成当前工具调用后被处理
    """
    # Verify conversation exists and user has access
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    # Append message to the streaming session
    success = await streaming_session_manager.append_message(conversation_id, request.content)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="没有找到活跃的streaming会话"
        )

    # Save appended message to database
    appended_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=request.content,
        message_metadata={"appended": True},
    )
    db.add(appended_message)
    await db.commit()

    logger.info(f"[Append] Successfully appended message to conversation {conversation_id}")

    return {
        "success": True,
        "message": "消息已追加到streaming会话",
        "conversation_id": conversation_id,
    }
