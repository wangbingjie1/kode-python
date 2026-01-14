"""
DataSource Schemas

Pydantic models for data source API request/response validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class DataSourceType(str, Enum):
    """Data source type enumeration"""

    FILE = "file"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    MONGODB = "mongodb"


class DataSourceStatus(str, Enum):
    """Data source status enumeration"""

    PENDING = "pending"
    READY = "ready"
    ERROR = "error"
    ARCHIVED = "archived"


# === Create Requests ===


class FileDataSourceCreate(BaseModel):
    """File data source creation (for creating record after upload)"""

    name: str = Field(..., min_length=1, max_length=100)
    file_path: str
    original_filename: str
    file_size: int
    file_mime_type: Optional[str] = None


class DatabaseConnectionCreate(BaseModel):
    """Database connection creation"""

    name: str = Field(..., min_length=1, max_length=100)
    source_type: DataSourceType
    host: str = Field(..., min_length=1)
    port: int = Field(..., gt=0, lt=65536)
    database: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    db_schema: Optional[str] = None
    ssl_enabled: bool = False
    config: Optional[Dict[str, Any]] = None

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: DataSourceType) -> DataSourceType:
        if v == DataSourceType.FILE:
            raise ValueError("File type should use the upload API")
        return v


# === Update Requests ===


class DataSourceUpdate(BaseModel):
    """Data source update"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    host: Optional[str] = None
    port: Optional[int] = Field(None, gt=0, lt=65536)
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    db_schema: Optional[str] = None
    ssl_enabled: Optional[bool] = None


# === Responses ===


class DataSourceResponse(BaseModel):
    """Data source response"""

    id: str
    organization_id: str
    name: str
    source_type: DataSourceType
    status: DataSourceStatus

    # File information
    file_path: Optional[str] = None
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    file_mime_type: Optional[str] = None

    # Database information (password excluded)
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    db_schema: Optional[str] = None
    ssl_enabled: Optional[bool] = None

    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DataSourceListResponse(BaseModel):
    """Data source list response"""

    items: List[DataSourceResponse]
    total: int


# === Test Connection ===


class TestConnectionRequest(BaseModel):
    """Test connection request (for testing before creating)"""

    source_type: DataSourceType
    host: str = Field(..., min_length=1)
    port: int = Field(..., gt=0, lt=65536)
    database: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    db_schema: Optional[str] = None
    ssl_enabled: bool = False

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: DataSourceType) -> DataSourceType:
        if v == DataSourceType.FILE:
            raise ValueError("File type does not support connection testing")
        return v


class TestConnectionResponse(BaseModel):
    """Test connection response"""

    success: bool
    message: str
    latency_ms: Optional[float] = None


# === Schema Extraction ===


class SchemaResponse(BaseModel):
    """Schema response"""

    tables: List[Dict[str, Any]]
    cached: bool = False
    cached_at: Optional[datetime] = None
