"""
Chat Schemas

Pydantic schemas for chat-related API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ConversationCreate(BaseModel):
    """Request schema for creating conversation"""

    title: Optional[str] = Field(None, max_length=200)
    project_id: str = Field(..., description="ID of the project this conversation belongs to")


class ConversationResponse(BaseModel):
    """Response schema for conversation"""

    id: str
    title: str
    project_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic V2 (was orm_mode in V1)


class MessageResponse(BaseModel):
    """Response schema for message"""

    id: str
    conversation_id: str
    role: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


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
