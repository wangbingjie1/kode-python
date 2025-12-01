"""
Direct Anthropic API streaming implementation without LangChain.

This module provides streaming chat functionality using the native Anthropic SDK.
"""

import os
import asyncio
from typing import AsyncGenerator, Dict, List, Any, Optional
import anthropic
import httpx
from anthropic.types import (
    Message,
    MessageStreamEvent,
    ContentBlock,
    TextBlock,
    ToolUseBlock,
    ThinkingBlock,
    ThinkingDelta,
)

from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnthropicStreamingAgent:
    """
    Streaming agent using native Anthropic API.

    Provides real-time streaming responses without LangChain overhead.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: Optional[List[Any]] = None,
        system_prompt: str = "",
        verbose: bool = False,
        on_tool_start: Optional[callable] = None,
        on_tool_end: Optional[callable] = None,
        on_iteration: Optional[callable] = None,
        cancel_event: Optional[asyncio.Event] = None,
        message_queue: Optional[asyncio.Queue] = None,
    ):
        """
        Initialize streaming agent.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model ID to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            tools: List of tool instances
            system_prompt: System prompt
            verbose: Enable verbose logging
            on_tool_start: Callback when tool execution starts
            on_tool_end: Callback when tool execution ends
            on_iteration: Callback at iteration start
            cancel_event: Optional asyncio.Event to signal cancellation
            message_queue: Optional asyncio.Queue for appending messages
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")

        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.verbose = verbose
        self.on_tool_start = on_tool_start
        self.on_tool_end = on_tool_end
        self.on_iteration = on_iteration
        self.cancel_event = cancel_event
        self.message_queue = message_queue

        # Build tool map
        self.tool_map = {tool.name: tool for tool in self.tools}

        # Prepare tools in Anthropic format
        self.anthropic_tools = self._prepare_tools()

    def _prepare_tools(self) -> List[Dict]:
        """Convert Kode tools to Anthropic tool format."""
        anthropic_tools = []
        for tool in self.tools:
            tool_schema = {
                "name": tool.name,
                "description": tool.description,
            }
            # Add input schema if available
            if hasattr(tool, "args_schema") and tool.args_schema:
                schema = tool.args_schema.schema()
                tool_schema["input_schema"] = {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                }
            anthropic_tools.append(tool_schema)

        return anthropic_tools

    def _build_context_budget_info(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int,
        cache_read_tokens: int,
        iteration: int,
    ) -> str:
        """
        Build context budget information for the agent.

        This provides the agent with awareness of its token usage and remaining capacity.
        Also includes current time (dynamic info that should not be cached).

        Args:
            input_tokens: Total input tokens used so far
            output_tokens: Total output tokens used so far
            cache_creation_tokens: Total cache creation tokens
            cache_read_tokens: Total cache read tokens
            iteration: Current iteration number

        Returns:
            Formatted budget information string (including time)
        """
        from kode.utils.system_info import format_system_info_dynamic

        # Get current time (dynamic info)
        time_info = format_system_info_dynamic()

        # Calculate totals
        total_tokens_used = input_tokens + output_tokens
        context_limit = 2000000  # Anthropic's context window for Claude Sonnet 4.5
        remaining_tokens = context_limit - total_tokens_used

        # Calculate percentage used
        usage_percentage = (total_tokens_used / context_limit) * 100 if context_limit > 0 else 0

        # Build budget info message
        budget_lines = [time_info, "", f"## 🔋你的剩余注意力百分比：{100 - usage_percentage:.1f}%"]

        # Add warnings based on usage
        if usage_percentage >= 70:
            budget_lines.append("⚠️ **注意**: 注意力上下文使用已超过70%，你的注意力已经开始涣散。")

        budget_lines.append("")
        budget_lines.append("**重要**: 你需要自主管理自己的上下文使用情况，并在必要时采取措施：")
        budget_lines.append("- 剩余30%时候，调用上下文工具压缩上下文")
        budget_lines.append("- 剩余10%时候，提醒用户开启新对话")
        budget_lines.append("")

        return "\n".join(budget_lines)

    def _trim_messages_for_context(
        self, messages: List[Dict], max_context_tokens: int = 150000
    ) -> List[Dict]:
        """
        Trim messages to fit within token limit.

        Strategy:
        1. Keep system messages and first user message
        2. Keep last N messages that fit within limit
        3. Truncate long tool results (keep only first/last parts)
        4. CRITICAL: Maintain tool_use/tool_result pairing integrity

        Args:
            messages: List of message dicts
            max_context_tokens: Maximum tokens to allow in context

        Returns:
            Trimmed list of messages
        """

        # Rough token estimation: 1 token ~= 4 characters
        def estimate_tokens(text: str) -> int:
            return len(str(text)) // 4

        def estimate_message_tokens(msg: Dict) -> int:
            """Estimate tokens in a message."""
            content = msg.get("content", "")
            if isinstance(content, str):
                return estimate_tokens(content)
            elif isinstance(content, list):
                # Handle list of content blocks (tool results, etc.)
                total = 0
                for item in content:
                    if isinstance(item, dict):
                        total += estimate_tokens(str(item))
                    else:
                        total += estimate_tokens(str(item))
                return total
            return estimate_tokens(str(content))

        def has_tool_use(msg: Dict) -> bool:
            """Check if message contains tool_use blocks."""
            content = msg.get("content", "")
            if isinstance(content, list):
                return any(
                    isinstance(item, dict) and item.get("type") == "tool_use" for item in content
                )
            return False

        def has_tool_result(msg: Dict) -> bool:
            """Check if message contains tool_result blocks."""
            content = msg.get("content", "")
            if isinstance(content, list):
                return any(
                    isinstance(item, dict) and item.get("type") == "tool_result" for item in content
                )
            return False

        # Calculate total tokens
        total_tokens = sum(estimate_message_tokens(msg) for msg in messages)

        if total_tokens <= max_context_tokens:
            return messages

        logger.warning(
            f"Context too large ({total_tokens} tokens), trimming to {max_context_tokens}"
        )

        # Strategy: Keep recent messages, maintain tool_use/tool_result pairing
        trimmed = []
        current_tokens = 0
        skip_next_tool_result = False

        # Process messages in reverse (keep most recent)
        for i, msg in enumerate(reversed(messages)):
            msg_tokens = estimate_message_tokens(msg)

            # Always keep the last user message
            if not trimmed:
                # If it's a tool_result without corresponding tool_use, we need to skip it
                if has_tool_result(msg):
                    logger.warning("Last message contains tool_result without tool_use, skipping")
                    continue
                trimmed.append(msg)
                current_tokens += msg_tokens
                continue

            # Check if this is a tool_result that should be skipped
            if skip_next_tool_result and has_tool_result(msg):
                logger.info(f"Skipping tool_result message (no corresponding tool_use)")
                skip_next_tool_result = False
                continue

            # Trim tool results if too large
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                # This is a tool result message
                trimmed_content = []
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        result_text = item.get("content", "")

                        # Aggressive trimming for schema/ontology results
                        # These are large JSON objects that should be summarized
                        try:
                            import json

                            result_data = json.loads(result_text)

                            # Check if this is a schema/ontology/uncertainty result
                            is_large_data = any(
                                key in result_data
                                for key in [
                                    "schema",
                                    "ontology",
                                    "entities",
                                    "concepts",
                                    "relationships",
                                    "uncertainties",
                                    "domains",
                                ]
                            )

                            if is_large_data:
                                # Create a summary instead of full content
                                summary = {"status": result_data.get("status", "success")}

                                # Add metadata only
                                if "metadata" in result_data:
                                    summary["metadata"] = result_data["metadata"]

                                # Add counts instead of full lists
                                for key in [
                                    "entities",
                                    "concepts",
                                    "relationships",
                                    "uncertainties",
                                ]:
                                    if key in result_data:
                                        data = result_data[key]
                                        if isinstance(data, list):
                                            summary[f"{key}_count"] = len(data)
                                        elif isinstance(data, dict):
                                            summary[f"{key}_count"] = len(data)

                                # Keep small important fields
                                for key in ["message", "file_path", "cache_hit"]:
                                    if key in result_data:
                                        summary[key] = result_data[key]

                                # Replace with summary
                                item["content"] = json.dumps(summary, ensure_ascii=False, indent=2)
                                logger.info(
                                    f"Trimmed large data result: {len(result_text)} -> {len(item['content'])} chars"
                                )
                            elif len(result_text) > 2000:
                                # Standard truncation for other long results
                                item["content"] = (
                                    result_text[:1000]
                                    + "\n...[truncated]...\n"
                                    + result_text[-500:]
                                )
                        except (json.JSONDecodeError, Exception):
                            # Not JSON or error parsing, use standard truncation
                            if len(result_text) > 2000:
                                item["content"] = (
                                    result_text[:1000]
                                    + "\n...[truncated]...\n"
                                    + result_text[-500:]
                                )

                        trimmed_content.append(item)
                    else:
                        trimmed_content.append(item)
                msg = {**msg, "content": trimmed_content}
                msg_tokens = estimate_message_tokens(msg)

            if current_tokens + msg_tokens > max_context_tokens:
                # If skipping a tool_use message, mark to skip corresponding tool_result
                if has_tool_use(msg):
                    skip_next_tool_result = True
                    logger.info(
                        f"Skipping tool_use message (would exceed limit), will skip corresponding tool_result"
                    )
                else:
                    logger.info(
                        f"Skipping message (would exceed limit): role={msg.get('role')}, tokens={msg_tokens}"
                    )
                continue

            trimmed.append(msg)
            current_tokens += msg_tokens

        # Reverse back to original order
        trimmed.reverse()

        # Final validation: ensure no orphaned tool_results or tool_uses
        validated = []
        last_had_tool_use = False

        for i, msg in enumerate(trimmed):
            # Check if this tool_result has a corresponding tool_use
            if has_tool_result(msg):
                if not last_had_tool_use:
                    logger.warning(
                        f"Removing orphaned tool_result message at position {len(validated)}"
                    )
                    continue  # Skip orphaned tool_result

            # Check if this tool_use will have a corresponding tool_result
            if has_tool_use(msg):
                # Look ahead to see if next message has tool_result
                has_following_result = False
                if i + 1 < len(trimmed):
                    next_msg = trimmed[i + 1]
                    if has_tool_result(next_msg):
                        has_following_result = True

                if not has_following_result:
                    logger.warning(
                        f"Removing orphaned tool_use message at position {len(validated)}"
                    )
                    continue  # Skip orphaned tool_use

            validated.append(msg)
            last_had_tool_use = has_tool_use(msg)

        logger.info(
            f"Trimmed context: {len(messages)} -> {len(validated)} messages, {total_tokens} -> {current_tokens} tokens"
        )
        return validated

    async def stream_response(
        self,
        task: str,
        chat_history: Optional[List[Dict]] = None,
        max_iterations: int = 15,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response from model with tool calling support.

        Args:
            task: User task/message
            chat_history: Previous conversation history
            max_iterations: Maximum number of tool-calling iterations

        Yields:
            Dict with 'type', 'content', and 'metadata'
        """
        # Prepare messages
        messages = []
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": task})

        # Trim messages if context is too large
        messages = self._trim_messages_for_context(messages)

        iteration = 0
        tool_calls_history = []

        # Token usage tracking
        total_input_tokens = 0
        total_output_tokens = 0
        total_cache_creation_tokens = 0
        total_cache_read_tokens = 0

        while iteration < max_iterations:
            # 检查是否被取消
            if self.cancel_event and self.cancel_event.is_set():
                logger.info(f"[Cancel] Stream cancelled by user at iteration {iteration}")
                yield {
                    "type": "cancelled",
                    "content": "用户已终止响应",
                    "metadata": {"iteration": iteration},
                }
                raise asyncio.CancelledError("User cancelled the stream")

            # 检查是否有追加的消息
            if self.message_queue and not self.message_queue.empty():
                try:
                    appended_msg = self.message_queue.get_nowait()
                    messages.append(appended_msg)
                    logger.info(
                        f"[Append] Appended user message: {appended_msg.get('content', '')[:50]}..."
                    )
                    yield {
                        "type": "message_appended",
                        "content": appended_msg.get("content", ""),
                        "metadata": {"iteration": iteration},
                    }
                except asyncio.QueueEmpty:
                    pass

            iteration += 1

            if self.verbose:
                logger.info(f"Iteration {iteration}")

            # Callback: iteration start
            if self.on_iteration:
                import inspect

                if inspect.iscoroutinefunction(self.on_iteration):
                    await self.on_iteration(iteration)
                else:
                    self.on_iteration(iteration)

            # Calculate and inject context budget information
            # ⚠️ IMPORTANT: 不要修改 system prompt，否则会破坏缓存
            # 将 budget info 作为独立的 user message 注入
            context_budget_info = self._build_context_budget_info(
                total_input_tokens,
                total_output_tokens,
                total_cache_creation_tokens,
                total_cache_read_tokens,
                iteration,
            )

            # 在对话历史的最后插入 budget info（作为 user message）
            if context_budget_info.strip():
                messages.append(
                    {
                        "role": "user",
                        "content": f"<system_info>\n{context_budget_info}\n</system_info>",
                    }
                )

            # ===== Prompt Caching Support =====
            # 使用 Anthropic 的 Prompt Caching 功能来缓存系统提示词和工具定义
            # 参考: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching

            # 将 system prompt 转换为支持缓存的格式（保持静态）
            system_with_cache = [
                {
                    "type": "text",
                    "text": self.system_prompt,  # ← 保持静态，不注入动态内容
                    "cache_control": {"type": "ephemeral"},  # 标记为可缓存
                }
            ]

            # Stream response from Anthropic (with retry for network errors)
            full_text = ""
            content_blocks = []
            max_retries = 3
            retry_delay_base = 2  # 指数退避基数

            for retry_attempt in range(max_retries):
                if retry_attempt > 0:
                    delay = retry_delay_base**retry_attempt
                    logger.warning(
                        f"[重试] 第 {retry_attempt}/{max_retries-1} 次重试，等待 {delay} 秒..."
                    )
                    await asyncio.sleep(delay)

                try:
                    # Enable Extended Thinking if supported by the model
                    # Note: temperature must be 1.0 when thinking is enabled
                    # Note: max_tokens must be greater than thinking.budget_tokens
                    thinking_budget = 5000  # Budget for thinking tokens
                    output_tokens = max(
                        self.max_tokens, thinking_budget + 4096
                    )  # Ensure enough for output

                    # ===== 请求内容日志 =====
                    logger.info(f"\n{'='*80}")
                    logger.info(f"[API 请求] 迭代 {iteration}")
                    logger.info(f"{'='*80}")

                    # 显示用户最新输入
                    if messages:
                        last_user_msg = None
                        for msg in reversed(messages):
                            if msg.get("role") == "user":
                                last_user_msg = msg
                                break
                        if last_user_msg:
                            user_content = str(last_user_msg.get("content", ""))
                            logger.info(f"\n[用户输入]")
                            if len(user_content) > 200:
                                logger.info(f"{user_content[:200]}...")
                            else:
                                logger.info(f"{user_content}")

                    # Token 组成估算
                    system_tokens = len(self.system_prompt) // 4
                    tools_tokens = sum(len(str(t)) for t in self.anthropic_tools) // 4
                    history_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4

                    logger.info(f"\n[Token 组成估算]")
                    logger.info(f"  系统提示词: ~{system_tokens:,} tokens")
                    logger.info(f"  工具定义:   ~{tools_tokens:,} tokens")
                    logger.info(f"  对话历史:   ~{history_tokens:,} tokens")
                    logger.info(
                        f"  预计输入:   ~{system_tokens + tools_tokens + history_tokens:,} tokens"
                    )

                    async with self.client.messages.stream(
                        model=self.model,
                        max_tokens=output_tokens,
                        temperature=1.0,  # Required for Extended Thinking
                        system=system_with_cache,  # ← 使用缓存优化的系统提示词
                        messages=messages,
                        tools=self.anthropic_tools if self.anthropic_tools else anthropic.NOT_GIVEN,
                        thinking={"type": "enabled", "budget_tokens": thinking_budget},
                    ) as stream:
                        thinking_content = ""
                        is_thinking = False

                        # Process streaming events
                        async for event in stream:
                            # Handle thinking blocks (Extended Thinking feature)
                            if hasattr(event, "type"):
                                if event.type == "content_block_start":
                                    block = getattr(event, "content_block", None)
                                    if block and isinstance(block, ThinkingBlock):
                                        is_thinking = True
                                        thinking_content = ""
                                        logger.info("[Thinking] Extended thinking started")
                                elif event.type == "content_block_delta":
                                    delta = getattr(event, "delta", None)
                                    if delta and isinstance(delta, ThinkingDelta):
                                        # Accumulate thinking content
                                        thinking_text = getattr(delta, "thinking", "")
                                        thinking_content += thinking_text
                                        # Yield thinking chunks
                                        yield {
                                            "type": "thinking",
                                            "content": thinking_text,
                                            "metadata": {"iteration": iteration, "is_delta": True},
                                        }
                                    elif (
                                        delta
                                        and hasattr(delta, "type")
                                        and delta.type == "text_delta"
                                    ):
                                        # Regular text content
                                        text = getattr(delta, "text", "")
                                        if text:
                                            full_text += text
                                            yield {
                                                "type": "chunk",
                                                "content": text,
                                                "metadata": {"iteration": iteration},
                                            }
                                elif event.type == "content_block_stop":
                                    if is_thinking:
                                        # Thinking block completed
                                        is_thinking = False
                                        logger.info(
                                            f"[Thinking] Completed: {len(thinking_content)} chars"
                                        )

                        # Get final message
                        final_message = await stream.get_final_message()
                        content_blocks = final_message.content

                        # Extract token usage from response
                        usage = getattr(final_message, "usage", None)
                        if usage:
                            input_tokens = getattr(usage, "input_tokens", 0)
                            output_tokens = getattr(usage, "output_tokens", 0)
                            cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
                            cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

                            # Accumulate totals
                            total_input_tokens += input_tokens
                            total_output_tokens += output_tokens
                            total_cache_creation_tokens += cache_creation
                            total_cache_read_tokens += cache_read

                            # ===== 实际 Token 使用统计 =====
                            logger.info(f"\n{'='*80}")
                            logger.info(f"[Token 使用] 迭代 {iteration}")
                            logger.info(f"{'='*80}")

                            # 本次调用
                            logger.info(f"\n本次 API 调用:")
                            logger.info(f"  输入 tokens:  {input_tokens:,}")
                            if cache_creation > 0:
                                logger.info(
                                    f"    ├─ 缓存创建: {cache_creation:,} tokens (首次，1.25× 价格)"
                                )
                            if cache_read > 0:
                                logger.info(f"    ├─ 缓存读取: {cache_read:,} tokens (节省 90%!)")
                            regular_input = input_tokens - cache_creation - cache_read
                            if regular_input > 0:
                                logger.info(f"    └─ 常规输入: {regular_input:,} tokens")
                            logger.info(f"  输出 tokens:  {output_tokens:,}")
                            logger.info(f"  本次总计:     {input_tokens + output_tokens:,} tokens")

                            # 累计统计
                            logger.info(f"\n对话累计:")
                            logger.info(f"  累计输入:  {total_input_tokens:,} tokens")
                            logger.info(f"  累计输出:  {total_output_tokens:,} tokens")
                            logger.info(
                                f"  总计:      {total_input_tokens + total_output_tokens:,} tokens"
                            )

                            # 缓存效果
                            if cache_read > 0:
                                savings_pct = (cache_read / input_tokens) * 90  # 90% 节省
                                logger.info(
                                    f"\n缓存节省: ~{savings_pct:.1f}% (读取了 {cache_read:,} tokens)"
                                )

                            logger.info(f"{'='*80}\n")

                            # 🔍 准备完整的请求和响应内容（用于追踪）
                            request_data = {
                                "system": self.system_prompt,
                                "messages": messages,
                                "tools": self.anthropic_tools,
                                "model": self.model,
                            }

                            response_data = {
                                "content": full_text,
                                "content_blocks": [
                                    {
                                        "type": block.type,
                                        "text": (
                                            getattr(block, "text", None)
                                            if hasattr(block, "text")
                                            else None
                                        ),
                                        "tool_use": (
                                            {
                                                "id": block.id,
                                                "name": block.name,
                                                "input": block.input,
                                            }
                                            if isinstance(block, ToolUseBlock)
                                            else None
                                        ),
                                    }
                                    for block in content_blocks
                                ],
                                "stop_reason": getattr(final_message, "stop_reason", None),
                                "usage": {
                                    "input_tokens": input_tokens,
                                    "output_tokens": output_tokens,
                                    "cache_creation_input_tokens": cache_creation,
                                    "cache_read_input_tokens": cache_read,
                                },
                            }

                            # Yield token usage event for this iteration
                            yield {
                                "type": "token_usage",
                                "content": "",
                                "metadata": {
                                    "iteration": iteration,
                                    "input_tokens": input_tokens,
                                    "output_tokens": output_tokens,
                                    "total_tokens": input_tokens + output_tokens,
                                    "cache_creation_input_tokens": cache_creation,
                                    "cache_read_input_tokens": cache_read,
                                    # 🔍 添加完整的请求和响应数据
                                    "request_data": request_data,
                                    "response_data": response_data,
                                },
                            }

                    # 成功完成，跳出重试循环
                    break

                except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError) as e:
                    # 网络错误：连接中断、读取错误等
                    from kode.utils.logger import safe_log_exception

                    error_message = str(e)
                    safe_log_exception(
                        logger,
                        f"Network error on attempt {retry_attempt + 1}/{max_retries}: {error_message}",
                        e,
                    )

                    # 如果还有重试次数，继续重试
                    if retry_attempt < max_retries - 1:
                        logger.warning(
                            f"[网络错误] 将在 {retry_delay_base ** (retry_attempt + 1)} 秒后重试..."
                        )
                        continue
                    else:
                        # 最后一次重试也失败，返回错误
                        logger.error(f"[网络错误] 已重试 {max_retries} 次，全部失败")
                        yield {
                            "type": "error",
                            "content": f"网络连接失败（已重试 {max_retries} 次）: {error_message}",
                            "metadata": {"error": error_message, "retries": max_retries, "error_type": "network_error"},
                        }
                        return

                except Exception as e:
                    # 识别 Anthropic API 特定错误类型
                    from anthropic import AuthenticationError, PermissionDeniedError, RateLimitError, BadRequestError, APIError
                    from kode.utils.logger import safe_log_exception

                    error_message = str(e)
                    error_type = type(e).__name__

                    # 区分不同错误类型，提供清晰提示
                    if isinstance(e, AuthenticationError):
                        # ⚠️ Token 无效或过期，不重试
                        safe_log_exception(
                            logger, f"[认证失败] API Token 无效或已过期: {error_message}", e
                        )
                        yield {
                            "type": "error",
                            "content": f"认证失败：API Token 无效或已过期。请检查 .kode.json 中的 apiKeys.anthropic 配置或 ANTHROPIC_API_KEY 环境变量。\n\n错误详情: {error_message}",
                            "metadata": {
                                "error": error_message,
                                "error_type": "authentication_error",
                                "suggestion": "请更新您的 API Token 并重新启动服务",
                            },
                        }
                        return

                    elif isinstance(e, RateLimitError):
                        # ⚠️ 超出速率限制，建议稍后重试
                        safe_log_exception(
                            logger, f"[速率限制] API 请求频率过高: {error_message}", e
                        )
                        yield {
                            "type": "error",
                            "content": f"速率限制：API 请求频率过高，请稍后再试。\n\n错误详情: {error_message}",
                            "metadata": {
                                "error": error_message,
                                "error_type": "rate_limit_error",
                                "suggestion": "请等待几分钟后重新发送消息",
                            },
                        }
                        return

                    elif isinstance(e, PermissionDeniedError):
                        # ⚠️ 权限不足
                        safe_log_exception(
                            logger, f"[权限不足] API Token 权限不足: {error_message}", e
                        )
                        yield {
                            "type": "error",
                            "content": f"权限不足：当前 API Token 无权访问该资源。\n\n错误详情: {error_message}",
                            "metadata": {
                                "error": error_message,
                                "error_type": "permission_denied",
                                "suggestion": "请检查 API Token 的权限设置",
                            },
                        }
                        return

                    elif isinstance(e, BadRequestError):
                        # ⚠️ 请求参数错误
                        safe_log_exception(
                            logger, f"[请求错误] API 请求参数有误: {error_message}", e
                        )
                        yield {
                            "type": "error",
                            "content": f"请求错误：发送给 AI 的请求格式有误，这可能是系统配置问题。\n\n错误详情: {error_message}",
                            "metadata": {
                                "error": error_message,
                                "error_type": "bad_request",
                                "suggestion": "请联系技术支持并提供此错误信息",
                            },
                        }
                        return

                    else:
                        # 其他未知错误
                        safe_log_exception(
                            logger, f"Error streaming from Anthropic: {error_message}", e
                        )
                        yield {
                            "type": "error",
                            "content": f"系统错误: {error_message}",
                            "metadata": {
                                "error": error_message,
                                "error_type": error_type,
                            },
                        }
                        return

            # Add assistant message to history
            messages.append({"role": "assistant", "content": content_blocks})

            # ✨ 按照 content_blocks 的原始顺序发送事件（保持文本和工具调用的顺序）
            tool_uses = []
            for block in content_blocks:
                if isinstance(block, TextBlock):
                    # 发送文本块事件
                    text_content = block.text
                    if text_content:
                        yield {
                            "type": "text_block",
                            "content": text_content,
                            "metadata": {"iteration": iteration},
                        }
                elif isinstance(block, ToolUseBlock):
                    # 记录工具调用，稍后执行
                    tool_uses.append(block)
                    # 立即发送 tool_call 事件（保持顺序）
                    yield {
                        "type": "tool_call",
                        "content": f"Executing: {block.name}",
                        "metadata": {
                            "tool_name": block.name,
                            "tool_use_id": block.id,
                            "status": "started",
                            "args": block.input,
                        },
                    }

            if not tool_uses:
                # No tool calls, we're done
                yield {
                    "type": "complete",
                    "content": full_text,
                    "metadata": {
                        "iterations": iteration,
                        "tool_calls": tool_calls_history,
                        "token_usage": {
                            "total_input_tokens": total_input_tokens,
                            "total_output_tokens": total_output_tokens,
                            "total_tokens": total_input_tokens + total_output_tokens,
                            "cache_creation_input_tokens": total_cache_creation_tokens,
                            "cache_read_input_tokens": total_cache_read_tokens,
                        },
                    },
                }
                return

            # Execute tools
            tool_results = []
            for tool_use in tool_uses:
                tool_name = tool_use.name
                tool_args = tool_use.input
                tool_use_id = tool_use.id

                if self.verbose:
                    logger.info(f"Tool call: {tool_name}({tool_args})")

                # ✅ tool_call 事件已经在上面按顺序发送了，这里不需要再发送

                # Callback: tool start
                if self.on_tool_start:
                    import inspect

                    if inspect.iscoroutinefunction(self.on_tool_start):
                        await self.on_tool_start(tool_name, tool_args)
                    else:
                        self.on_tool_start(tool_name, tool_args)

                # Execute tool
                if tool_name in self.tool_map:
                    try:
                        tool = self.tool_map[tool_name]

                        # Execute tool (async if available)
                        if hasattr(tool, "ainvoke"):
                            result = await tool.ainvoke(tool_args)
                        else:
                            result = tool.invoke(tool_args)

                        if self.verbose:
                            logger.info(f"Tool result: {str(result)[:200]}")

                        # Check if tool requires user input
                        requires_user_input = False
                        result_data = None
                        try:
                            import json

                            result_data = json.loads(str(result))
                            if isinstance(result_data, dict) and result_data.get(
                                "requires_user_input"
                            ):
                                requires_user_input = True
                                logger.info(
                                    f"[Tool '{tool_name}'] Requires user input - Agent will pause after this iteration"
                                )
                        except (json.JSONDecodeError, ValueError):
                            pass  # Result is not JSON, continue normally

                        # Yield tool_result event immediately
                        yield {
                            "type": "tool_result",
                            "content": str(result),
                            "metadata": {
                                "tool_name": tool_name,
                                "tool_use_id": tool_use_id,  # ← 必须包含以便前端配对
                                "status": "completed",
                                "tool_args": tool_args,
                                "result": str(result),
                                "requires_user_input": requires_user_input,  # Pass to frontend
                            },
                        }

                        # ✨ 特殊处理：ChartGenerator 和 InsightGenerator 额外发送可视化事件
                        if result_data and isinstance(result_data, dict):
                            # ChartGenerator 工具返回格式: {"success": true, "chart_type": "...", "config": {...}}
                            if tool_name == "ChartGenerator" and result_data.get("success"):
                                chart_config = result_data.get("config")
                                if chart_config:
                                    yield {
                                        "type": "chart",
                                        "content": chart_config,  # ECharts 配置对象
                                        "metadata": {
                                            "chart_type": result_data.get("chart_type"),
                                            "data_summary": result_data.get("data_summary"),
                                        },
                                    }
                                    logger.info(
                                        f"[Chart] Generated {result_data.get('chart_type')} chart"
                                    )

                            # InsightGenerator 工具返回格式: {"success": true, "insights": [...]}
                            elif tool_name == "InsightGenerator" and result_data.get("success"):
                                insights_list = result_data.get("insights")
                                if insights_list:
                                    yield {
                                        "type": "insight",
                                        "content": insights_list,  # 洞察列表
                                        "metadata": {
                                            "total_count": (
                                                len(insights_list)
                                                if isinstance(insights_list, list)
                                                else 0
                                            ),
                                            "data_summary": result_data.get("data_summary"),
                                        },
                                    }
                                    logger.info(
                                        f"[Insight] Generated {len(insights_list)} insights"
                                    )

                        # Callback: tool end
                        if self.on_tool_end:
                            import inspect

                            if inspect.iscoroutinefunction(self.on_tool_end):
                                await self.on_tool_end(tool_name, tool_args, result)
                            else:
                                self.on_tool_end(tool_name, tool_args, result)

                        # Add tool result
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": str(result),
                            }
                        )

                        # Track tool call
                        tool_calls_history.append(
                            {
                                "name": tool_name,
                                "args": tool_args,
                                "result": str(result)[:500],
                            }
                        )

                    except Exception as e:
                        # Special handling for UserInputRequired exception
                        from kode.exceptions import UserInputRequired

                        if isinstance(e, UserInputRequired):
                            logger.info(f"[User Input Required] {e.question}")

                            # IMPORTANT: Register tool instance in global session manager
                            # This allows POST /api/sse/chat/{conversation_id}/user-response to find it
                            try:
                                from kode.web.api.sse import user_input_session_manager

                                # conversation_id is passed via _current_conversation_id attribute
                                conversation_id = getattr(self, "_current_conversation_id", None)
                                if conversation_id:
                                    user_input_session_manager.register_pending_input(
                                        conversation_id, e.tool_instance
                                    )
                                    logger.info(
                                        f"[User Input] Registered pending input for conversation {conversation_id}"
                                    )
                                else:
                                    logger.warning(
                                        "[User Input] No conversation_id available for registration"
                                    )
                            except ImportError:
                                logger.warning(
                                    "[User Input] Could not import user_input_session_manager"
                                )

                            # Yield special SSE event for user input
                            yield {
                                "type": "user_input_required",
                                "content": e.question,
                                "metadata": {
                                    "tool_name": tool_name,
                                    "tool_use_id": tool_use_id,
                                    "question_data": e.to_dict(),
                                },
                            }

                            # Wait for user response (tool instance has _wait_for_response method)
                            if hasattr(e.tool_instance, "_wait_for_response"):
                                try:
                                    user_answer = await e.tool_instance._wait_for_response()
                                    logger.info(f"[User Input Received] {user_answer}")

                                    # Yield user response event
                                    yield {
                                        "type": "user_input_received",
                                        "content": user_answer,
                                        "metadata": {
                                            "tool_name": tool_name,
                                            "question": e.question,
                                        },
                                    }

                                    # Add user answer as tool result
                                    tool_results.append(
                                        {
                                            "type": "tool_result",
                                            "tool_use_id": tool_use_id,
                                            "content": user_answer,
                                        }
                                    )

                                    # Track in history
                                    tool_calls_history.append(
                                        {
                                            "name": tool_name,
                                            "args": tool_args,
                                            "result": user_answer[:500],
                                            "user_interaction": True,
                                        }
                                    )

                                    # Continue to next tool
                                    continue

                                except Exception as wait_error:
                                    logger.error(f"Error waiting for user response: {wait_error}")
                                    error_msg = f"Failed to get user response: {str(wait_error)}"

                                    yield {
                                        "type": "tool_result",
                                        "content": error_msg,
                                        "metadata": {
                                            "tool_name": tool_name,
                                            "tool_use_id": tool_use_id,
                                            "status": "error",
                                            "error": error_msg,
                                        },
                                    }

                                    tool_results.append(
                                        {
                                            "type": "tool_result",
                                            "tool_use_id": tool_use_id,
                                            "content": error_msg,
                                            "is_error": True,
                                        }
                                    )

                                    tool_calls_history.append(
                                        {
                                            "name": tool_name,
                                            "args": tool_args,
                                            "error": error_msg,
                                        }
                                    )
                                    continue

                        # Regular exception handling
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        logger.error(error_msg, exc_info=True)

                        # Yield error result
                        yield {
                            "type": "tool_result",
                            "content": error_msg,
                            "metadata": {
                                "tool_name": tool_name,
                                "tool_use_id": tool_use_id,
                                "status": "error",
                                "tool_args": tool_args,
                                "error": str(e),
                            },
                        }

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": error_msg,
                                "is_error": True,
                            }
                        )

                        tool_calls_history.append(
                            {
                                "name": tool_name,
                                "args": tool_args,
                                "error": str(e),
                            }
                        )
                else:
                    error_msg = f"Tool '{tool_name}' not found"
                    logger.error(error_msg)

                    # Yield error result
                    yield {
                        "type": "tool_result",
                        "content": error_msg,
                        "metadata": {
                            "tool_name": tool_name,
                            "tool_use_id": tool_use_id,
                            "status": "error",
                            "error": error_msg,
                        },
                    }

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": error_msg,
                            "is_error": True,
                        }
                    )

            # Add tool results to messages
            messages.append({"role": "user", "content": tool_results})

            # 🔥 不需要检查 requires_user_input，让工具循环继续
            # Agent 会自动等待用户提交答案（前端会发送新消息）
            # 这样避免了暂停循环导致的复杂性

            # Trim messages after each iteration to prevent token overflow
            messages = self._trim_messages_for_context(messages)

        # Max iterations reached
        yield {
            "type": "complete",
            "content": "Maximum iterations reached without completion",
            "metadata": {
                "iterations": iteration,
                "tool_calls": tool_calls_history,
                "token_usage": {
                    "total_input_tokens": total_input_tokens,
                    "total_output_tokens": total_output_tokens,
                    "total_tokens": total_input_tokens + total_output_tokens,
                    "cache_creation_input_tokens": total_cache_creation_tokens,
                    "cache_read_input_tokens": total_cache_read_tokens,
                },
            },
        }
