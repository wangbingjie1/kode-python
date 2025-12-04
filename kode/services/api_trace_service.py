"""
API Call Trace Service - Database Version

记录和管理 Anthropic API 调用的详细信息到MySQL数据库。
用于上下文工程优化和成本分析。
"""

import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import logging

from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


def make_serializable(obj: Any) -> Any:
    """
    递归转换对象为可JSON序列化的格式
    处理 Anthropic SDK 的特殊对象类型（如 ThinkingBlock, ToolUseBlock 等）
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]

    # 处理 Anthropic SDK 对象（有 model_dump 或 dict 方法）
    if hasattr(obj, 'model_dump'):
        try:
            return make_serializable(obj.model_dump())
        except Exception:
            pass

    if hasattr(obj, 'dict'):
        try:
            return make_serializable(obj.dict())
        except Exception:
            pass

    # 处理有 __dict__ 的对象
    if hasattr(obj, '__dict__'):
        try:
            return make_serializable(vars(obj))
        except Exception:
            pass

    # 最后尝试转换为字符串
    try:
        return str(obj)
    except Exception:
        return f"<non-serializable: {type(obj).__name__}>"


class APICallTraceRecord:
    """API调用追踪记录（纯数据类，用于构建）"""

    def __init__(
        self,
        conversation_id: str,
        user_id: str,
        model_name: str,
        iteration: int = 1,
    ):
        self.id = f"{conversation_id}_{iteration}_{int(time.time() * 1000)}"
        self.conversation_id = conversation_id
        self.message_id = None  # 可选：关联到assistant消息
        self.user_id = user_id
        self.model_name = model_name
        self.iteration = iteration

        # Token 使用量
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0

        # 成本计算（美元）
        self.regular_input_cost = 0.0
        self.cache_creation_cost = 0.0
        self.cache_read_cost = 0.0
        self.output_cost = 0.0
        self.total_cost = 0.0

        # 完整内容
        self.request_content = {}   # 完整请求：{system, messages, tools, ...}
        self.response_content = {}  # 完整响应：{content, stop_reason, ...}
        self.tool_calls = []
        self.context_summary = {}

        # 性能
        self.latency_ms = 0
        self.start_time = time.time()

        # 错误信息
        self.error_message = None

        # 时间戳
        self.created_at = datetime.utcnow()

    def set_token_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
    ):
        """设置token使用量并计算成本

        ⚠️ 关键说明：Anthropic API 的 input_tokens 只包含常规输入，不包含缓存
        """
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_creation_input_tokens = cache_creation_tokens
        self.cache_read_input_tokens = cache_read_tokens

        # 计算成本（Anthropic Claude Sonnet 4.5 定价）
        # ✅ input_tokens 本身就是常规输入（非缓存）
        regular_input = input_tokens
        self.regular_input_cost = regular_input * 3.0 / 1_000_000  # $3/MTok
        self.cache_creation_cost = cache_creation_tokens * 3.75 / 1_000_000  # $3.75/MTok
        self.cache_read_cost = cache_read_tokens * 0.30 / 1_000_000  # $0.30/MTok
        self.output_cost = output_tokens * 15.0 / 1_000_000  # $15/MTok

        self.total_cost = (
            self.regular_input_cost
            + self.cache_creation_cost
            + self.cache_read_cost
            + self.output_cost
        )

    def set_request_content(self, system_prompt: str, messages: list, tools: list):
        """设置完整请求内容"""
        self.request_content = {
            "system": system_prompt,
            "messages": messages,
            "tools": [{"name": t.get("name"), "description": t.get("description")} for t in tools] if tools else [],
            "model": self.model_name,
        }

    def set_response_content(self, content: str, stop_reason: str, usage: dict):
        """设置完整响应内容"""
        self.response_content = {
            "content": content,
            "stop_reason": stop_reason,
            "usage": usage,
        }

    def add_tool_call(self, tool_name: str, tool_input: dict, tool_output: str, duration_ms: int):
        """添加工具调用记录（完整参数和结果）"""
        self.tool_calls.append({
            "tool_name": tool_name,
            "input": tool_input,     # 完整输入参数
            "output": tool_output,   # 完整输出结果
            "duration_ms": duration_ms,
        })

    def set_context_summary(self, history_count: int, total_context_chars: int):
        """设置上下文摘要"""
        self.context_summary = {
            "history_message_count": history_count,
            "total_context_chars": total_context_chars,
        }

    def finalize(self):
        """完成记录，计算延迟"""
        self.latency_ms = int((time.time() - self.start_time) * 1000)

    def to_db_dict(self) -> Dict[str, Any]:
        """转换为数据库字段字典"""
        # 先清理对象,确保可序列化
        clean_request = make_serializable(self.request_content) if self.request_content else None
        clean_response = make_serializable(self.response_content) if self.response_content else None
        clean_tool_calls = make_serializable(self.tool_calls) if self.tool_calls else None
        clean_context = make_serializable(self.context_summary) if self.context_summary else None

        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "model_name": self.model_name,
            "iteration": self.iteration,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "regular_input_cost": round(self.regular_input_cost, 8),
            "cache_creation_cost": round(self.cache_creation_cost, 8),
            "cache_read_cost": round(self.cache_read_cost, 8),
            "output_cost": round(self.output_cost, 8),
            "total_cost": round(self.total_cost, 8),
            "request_content": json.dumps(clean_request, ensure_ascii=False) if clean_request else None,
            "response_content": json.dumps(clean_response, ensure_ascii=False) if clean_response else None,
            "tool_calls": json.dumps(clean_tool_calls, ensure_ascii=False) if clean_tool_calls else None,
            "latency_ms": self.latency_ms,
            "context_summary": json.dumps(clean_context, ensure_ascii=False) if clean_context else None,
            "error_message": self.error_message,
            "created_at": self.created_at,
        }


class APITraceService:
    """API调用追踪服务（数据库存储）"""

    def __init__(self):
        logger.info("API Trace Service initialized (Database mode)")

    def create_trace(
        self,
        conversation_id: str,
        user_id: str,
        model_name: str,
        iteration: int = 1,
    ) -> APICallTraceRecord:
        """创建新的追踪记录"""
        trace = APICallTraceRecord(
            conversation_id=conversation_id,
            user_id=user_id,
            model_name=model_name,
            iteration=iteration,
        )
        return trace

    def save_trace(self, trace: APICallTraceRecord, db_session):
        """
        保存追踪记录到数据库（同步版本，用于SessionLocal）

        Args:
            trace: 追踪记录对象
            db_session: SQLAlchemy 同步会话（SessionLocal）
        """
        try:
            from sqlalchemy import text

            sql = text("""
                INSERT INTO api_call_traces (
                    id, conversation_id, message_id, user_id,
                    model_name, iteration,
                    input_tokens, output_tokens,
                    cache_creation_input_tokens, cache_read_input_tokens,
                    regular_input_cost, cache_creation_cost, cache_read_cost,
                    output_cost, total_cost,
                    request_content, response_content, tool_calls,
                    latency_ms, context_summary, error_message, created_at
                ) VALUES (
                    :id, :conversation_id, :message_id, :user_id,
                    :model_name, :iteration,
                    :input_tokens, :output_tokens,
                    :cache_creation_input_tokens, :cache_read_input_tokens,
                    :regular_input_cost, :cache_creation_cost, :cache_read_cost,
                    :output_cost, :total_cost,
                    :request_content, :response_content, :tool_calls,
                    :latency_ms, :context_summary, :error_message, :created_at
                )
            """)

            db_session.execute(sql, trace.to_db_dict())
            db_session.commit()

            logger.info(
                f"[API Trace] Saved to DB: {trace.id}, "
                f"cost=${trace.total_cost:.6f}, "
                f"tokens={trace.input_tokens + trace.output_tokens}"
            )

        except Exception as e:
            logger.error(f"[API Trace] Failed to save to database: {e}", exc_info=True)
            db_session.rollback()

    async def save_trace_async(self, trace: APICallTraceRecord, async_db_session):
        """
        保存追踪记录到数据库（异步版本，用于AsyncSession）

        Args:
            trace: 追踪记录对象
            async_db_session: SQLAlchemy 异步会话
        """
        try:
            from sqlalchemy import text

            sql = text("""
                INSERT INTO api_call_traces (
                    id, conversation_id, message_id, user_id,
                    model_name, iteration,
                    input_tokens, output_tokens,
                    cache_creation_input_tokens, cache_read_input_tokens,
                    regular_input_cost, cache_creation_cost, cache_read_cost,
                    output_cost, total_cost,
                    request_content, response_content, tool_calls,
                    latency_ms, context_summary, error_message, created_at
                ) VALUES (
                    :id, :conversation_id, :message_id, :user_id,
                    :model_name, :iteration,
                    :input_tokens, :output_tokens,
                    :cache_creation_input_tokens, :cache_read_input_tokens,
                    :regular_input_cost, :cache_creation_cost, :cache_read_cost,
                    :output_cost, :total_cost,
                    :request_content, :response_content, :tool_calls,
                    :latency_ms, :context_summary, :error_message, :created_at
                )
            """)

            await async_db_session.execute(sql, trace.to_db_dict())
            await async_db_session.commit()

            logger.info(
                f"[API Trace] Saved to DB (async): {trace.id}, "
                f"cost=${trace.total_cost:.6f}, "
                f"tokens={trace.input_tokens + trace.output_tokens}"
            )

        except Exception as e:
            logger.error(f"[API Trace] Failed to save to database (async): {e}", exc_info=True)
            await async_db_session.rollback()


# 全局实例
api_trace_service = APITraceService()
