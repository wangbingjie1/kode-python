"""
API Call Trace Model

记录每次 Anthropic API 调用的详细信息，用于上下文工程优化和成本分析。
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from kode.database.session import Base


class APICallTrace(Base):
    """API调用追踪记录"""

    __tablename__ = "api_call_traces"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String(36), ForeignKey("conversations.id"), nullable=False, index=True
    )
    message_id = Column(
        String(36), ForeignKey("messages.id"), nullable=True, index=True
    )  # 关联到 assistant 消息
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 调用元数据
    model_name = Column(String(100), nullable=False)  # claude-sonnet-4-5-20250929
    iteration = Column(Integer, default=1)  # 第几次迭代（Agent可能多次调用）

    # Token 使用量（来自 Anthropic API 响应）
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    cache_creation_input_tokens = Column(Integer, default=0, nullable=False)
    cache_read_input_tokens = Column(Integer, default=0, nullable=False)

    # 成本计算（美元，精确到小数点后8位）
    regular_input_cost = Column(Float, default=0.0)  # 常规输入成本
    cache_creation_cost = Column(Float, default=0.0)  # 缓存创建成本
    cache_read_cost = Column(Float, default=0.0)  # 缓存读取成本
    output_cost = Column(Float, default=0.0)  # 输出成本
    total_cost = Column(Float, default=0.0)  # 总成本（美元）

    # 请求和响应内容（存储完整内容用于调试和分析）
    request_content = Column(Text, nullable=True)  # JSON string: {system, messages, tools, model}
    response_content = Column(Text, nullable=True)  # JSON string: {content, stop_reason, usage}

    # 工具调用记录
    tool_calls = Column(JSON, default=list)  # [{tool_name, args_summary, result_summary, duration_ms}, ...]

    # 性能指标
    latency_ms = Column(Integer, default=0)  # API调用延迟（毫秒）

    # 上下文信息（用于优化分析）
    context_summary = Column(JSON, default=dict)  # {history_message_count, total_context_chars, ...}

    # 错误信息（如果有）
    error_message = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="api_traces")
    message = relationship("Message", backref="api_traces")
    user = relationship("User", backref="api_traces")

    def __repr__(self):
        return f"<APICallTrace(id={self.id}, model={self.model_name}, iteration={self.iteration}, cost=${self.total_cost:.6f})>"

    @property
    def total_tokens(self) -> int:
        """总token数"""
        return self.input_tokens + self.output_tokens

    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率（百分比）"""
        if self.input_tokens == 0:
            return 0.0
        return (self.cache_read_input_tokens / self.input_tokens) * 100

    @property
    def cost_savings(self) -> float:
        """缓存节省的成本（美元）"""
        # 如果缓存读取的token按标准价格计算的成本
        no_cache_cost = (self.cache_read_input_tokens / 1_000_000) * 3.0
        # 实际缓存读取成本
        actual_cache_cost = self.cache_read_cost
        return no_cache_cost - actual_cache_cost

    def to_dict(self):
        """转换为字典，用于API响应"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "model_name": self.model_name,
            "iteration": self.iteration,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "cache_creation": self.cache_creation_input_tokens,
                "cache_read": self.cache_read_input_tokens,
                "total": self.total_tokens,
            },
            "costs": {
                "regular_input": self.regular_input_cost,
                "cache_creation": self.cache_creation_cost,
                "cache_read": self.cache_read_cost,
                "output": self.output_cost,
                "total": self.total_cost,
                "savings": self.cost_savings,
            },
            "performance": {
                "latency_ms": self.latency_ms,
                "cache_hit_rate": self.cache_hit_rate,
            },
            "request_content": self.request_content,
            "response_content": self.response_content,
            "tool_calls": self.tool_calls,
            "context_summary": self.context_summary,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
