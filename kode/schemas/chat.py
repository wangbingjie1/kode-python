"""
Chat Schemas

Pydantic schemas for chat-related API endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime


class ConversationCreate(BaseModel):
    """Request schema for creating conversation"""

    title: Optional[str] = Field(None, max_length=200)
    project_id: Optional[str] = Field(None, description="ID of the project this conversation belongs to (optional, will use default project if not provided)")


class ConversationResponse(BaseModel):
    """Response schema for conversation"""

    id: str
    title: str
    project_id: str
    created_at: datetime
    updated_at: datetime
    # 搜索时可能包含匹配的消息片段
    matched_message: Optional[str] = Field(None, description="搜索匹配到的消息片段")

    class Config:
        from_attributes = True  # Pydantic V2 (was orm_mode in V1)


class ConversationListResponse(BaseModel):
    """分页列表响应"""

    items: list[ConversationResponse]
    total: int = Field(..., description="总数量")
    limit: int
    offset: int
    has_more: bool = Field(..., description="是否有更多数据")


class MessageResponse(BaseModel):
    """Response schema for message"""

    id: str
    conversation_id: str
    role: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="message_metadata")
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True  # Allow using both 'metadata' and 'message_metadata'
        by_alias = False  # 序列化时使用字段名 'metadata' 而不是别名 'message_metadata'

    @field_validator('metadata', mode='before')
    @classmethod
    def ensure_metadata_dict(cls, v):
        """确保 metadata 不为 None，自动转换为空 dict"""
        return v if v is not None else {}


class WebSocketMessage(BaseModel):
    """WebSocket message schema"""

    type: str = Field(..., description="Message type: task, ping, etc.")
    content: str = Field(default="")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StreamingChunk(BaseModel):
    """Streaming response chunk schema"""

    type: str = Field(
        ..., description="Chunk type: thinking, tool_call, chunk, complete, error"
    )
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
