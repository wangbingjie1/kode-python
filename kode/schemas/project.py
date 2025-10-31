"""
Project Schemas

Pydantic models for project API request/response validation.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any


class ProjectBase(BaseModel):
    """Base project schema"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    config: Dict[str, Any] | None = None


class ProjectCreate(ProjectBase):
    """Schema for creating a project"""

    user_id: str


class ProjectResponse(ProjectBase):
    """Schema for project response"""

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
