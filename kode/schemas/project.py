"""
Project Schemas

Pydantic models for project API request/response validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .project_data_source import ProjectDataSourceResponse


class ProjectBase(BaseModel):
    """Base project schema"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    config: Optional[Dict[str, Any]] = None


class ProjectCreate(ProjectBase):
    """Schema for creating a project"""

    user_id: str
    organization_id: Optional[str] = None
    data_source_ids: Optional[List[str]] = []  # Optional data sources to link on creation


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    config: Optional[Dict[str, Any]] = None


class ProjectResponse(ProjectBase):
    """Schema for project response"""

    id: str
    user_id: str
    organization_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    data_sources: List[ProjectDataSourceResponse] = []  # Associated data sources

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for project list response"""

    items: List[ProjectResponse]
    total: int
