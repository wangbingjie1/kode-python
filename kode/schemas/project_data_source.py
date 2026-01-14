"""
ProjectDataSource Schemas

Pydantic models for project-data source association API request/response validation.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class ProjectDataSourceStatus(str, Enum):
    """Project data source association status"""

    LINKED = "linked"
    MERGED = "merged"
    PENDING_MERGE = "pending_merge"


class ProjectDataSourceCreate(BaseModel):
    """Associate data source to project"""

    data_source_id: str


class ProjectDataSourceResponse(BaseModel):
    """Project data source association response"""

    id: str
    project_id: str
    data_source_id: str
    data_source_name: Optional[str] = None
    data_source_type: Optional[str] = None
    status: ProjectDataSourceStatus
    merged_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectDataSourceListResponse(BaseModel):
    """Project data source list response"""

    items: List[ProjectDataSourceResponse]
    total: int


class LinkDataSourceResponse(BaseModel):
    """Link data source response"""

    success: bool
    message: str
    prompt_merge: bool = True  # Whether to prompt user for merge


class UnlinkDataSourceResponse(BaseModel):
    """Unlink data source response"""

    success: bool
    message: str
