"""
Organization Schemas

Pydantic models for organization API request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    """Base organization schema"""

    name: str = Field(..., min_length=1, max_length=100)


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization"""

    pass


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)


class OrganizationResponse(OrganizationBase):
    """Schema for organization response"""

    id: str
    owner_id: str
    max_projects: int
    max_data_sources: int
    max_storage_bytes: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
