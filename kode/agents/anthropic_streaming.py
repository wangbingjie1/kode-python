"""
Direct Anthropic API streaming implementation without LangChain.

This module provides streaming chat functionality using the native Anthropic SDK.
"""

import os
import asyncio
from typing import AsyncGenerator, Dict, List, Any, Optional
import anthropic
from anthropic.types import (
    Message,
    MessageStreamEvent,
    ContentBlock,
    TextBlock,
    ToolUseBlock,
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
            if hasattr(tool, 'args_schema') and tool.args_schema:
                schema = tool.args_schema.schema()
                tool_schema["input_schema"] = {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", [])
                }
            anthropic_tools.append(tool_schema)

        return anthropic_tools

    def _trim_messages_for_context(self, messages: List[Dict], max_context_tokens: int = 150000) -> List[Dict]:
        """
        Trim messages to fit within token limit.

        Strategy:
        1. Keep system messages and first user message
        2. Keep last N messages that fit within limit
        3. Truncate long tool results (keep only first/last parts)

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

        # Calculate total tokens
        total_tokens = sum(estimate_message_tokens(msg) for msg in messages)

        if total_tokens <= max_context_tokens:
            return messages

        logger.warning(f"Context too large ({total_tokens} tokens), trimming to {max_context_tokens}")

        # Strategy: Keep recent messages, trim oldest tool results
        trimmed = []
        current_tokens = 0

        # Process messages in reverse (keep most recent)
        for msg in reversed(messages):
            msg_tokens = estimate_message_tokens(msg)

            # Always keep the last user message
            if not trimmed:
                trimmed.append(msg)
                current_tokens += msg_tokens
                continue

            # Trim tool results if too large
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                # This is a tool result message
                trimmed_content = []
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        result_text = item.get("content", "")
                        if len(result_text) > 2000:
                            # Truncate long results (keep first 1000 + last 500 chars)
                            item["content"] = result_text[:1000] + "\n...[truncated]...\n" + result_text[-500:]
                        trimmed_content.append(item)
                    else:
                        trimmed_content.append(item)
                msg = {**msg, "content": trimmed_content}
                msg_tokens = estimate_message_tokens(msg)

            if current_tokens + msg_tokens > max_context_tokens:
                # Skip this message
                logger.info(f"Skipping message (would exceed limit): role={msg.get('role')}, tokens={msg_tokens}")
                continue

            trimmed.append(msg)
            current_tokens += msg_tokens

        # Reverse back to original order
        trimmed.reverse()

        logger.info(f"Trimmed context: {len(messages)} -> {len(trimmed)} messages, {total_tokens} -> {current_tokens} tokens")
        return trimmed

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

        while iteration < max_iterations:
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

            # Stream response from Anthropic
            full_text = ""
            content_blocks = []

            try:
                async with self.client.messages.stream(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=self.system_prompt,
                    messages=messages,
                    tools=self.anthropic_tools if self.anthropic_tools else anthropic.NOT_GIVEN,
                ) as stream:
                    # Stream text chunks
                    async for text in stream.text_stream:
                        if text:
                            full_text += text
                            # Yield chunk immediately
                            yield {
                                "type": "chunk",
                                "content": text,
                                "metadata": {"iteration": iteration}
                            }

                    # Get final message
                    final_message = await stream.get_final_message()
                    content_blocks = final_message.content

            except Exception as e:
                logger.error(f"Error streaming from Anthropic: {e}", exc_info=True)
                yield {
                    "type": "error",
                    "content": f"Error: {str(e)}",
                    "metadata": {"error": str(e)}
                }
                return

            # Add assistant message to history
            messages.append({
                "role": "assistant",
                "content": content_blocks
            })

            # Check for tool uses
            tool_uses = [block for block in content_blocks if isinstance(block, ToolUseBlock)]

            if not tool_uses:
                # No tool calls, we're done
                yield {
                    "type": "complete",
                    "content": full_text,
                    "metadata": {
                        "iterations": iteration,
                        "tool_calls": tool_calls_history,
                    }
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

                # Yield tool_call event immediately
                yield {
                    "type": "tool_call",
                    "content": f"Executing: {tool_name}",
                    "metadata": {
                        "tool_name": tool_name,
                        "status": "started",
                        "args": tool_args
                    }
                }

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

                        # Yield tool_result event immediately
                        yield {
                            "type": "tool_result",
                            "content": str(result),
                            "metadata": {
                                "tool_name": tool_name,
                                "status": "completed",
                                "tool_args": tool_args,
                                "result": str(result)
                            }
                        }

                        # Callback: tool end
                        if self.on_tool_end:
                            import inspect
                            if inspect.iscoroutinefunction(self.on_tool_end):
                                await self.on_tool_end(tool_name, tool_args, result)
                            else:
                                self.on_tool_end(tool_name, tool_args, result)

                        # Add tool result
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": str(result),
                        })

                        # Track tool call
                        tool_calls_history.append({
                            "name": tool_name,
                            "args": tool_args,
                            "result": str(result)[:500],
                        })

                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        logger.error(error_msg, exc_info=True)

                        # Yield error result
                        yield {
                            "type": "tool_result",
                            "content": error_msg,
                            "metadata": {
                                "tool_name": tool_name,
                                "status": "error",
                                "tool_args": tool_args,
                                "error": str(e)
                            }
                        }

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": error_msg,
                            "is_error": True,
                        })

                        tool_calls_history.append({
                            "name": tool_name,
                            "args": tool_args,
                            "error": str(e),
                        })
                else:
                    error_msg = f"Tool '{tool_name}' not found"
                    logger.error(error_msg)

                    # Yield error result
                    yield {
                        "type": "tool_result",
                        "content": error_msg,
                        "metadata": {
                            "tool_name": tool_name,
                            "status": "error",
                            "error": error_msg
                        }
                    }

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": error_msg,
                        "is_error": True,
                    })

            # Add tool results to messages
            messages.append({
                "role": "user",
                "content": tool_results
            })

            # Trim messages after each iteration to prevent token overflow
            messages = self._trim_messages_for_context(messages)

        # Max iterations reached
        yield {
            "type": "complete",
            "content": "Maximum iterations reached without completion",
            "metadata": {
                "iterations": iteration,
                "tool_calls": tool_calls_history,
            }
        }
