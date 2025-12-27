"""
Database Management Schemas

Pydantic schemas for database connection and ontology management.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatabaseConnectionCreate(BaseModel):
    """Schema for creating a database connection"""

    name: str = Field(..., description="Unique connection identifier")
    db_type: str = Field(
        ...,
        description="Database type (postgresql, mysql, sqlserver, oracle, sqlite)",
    )
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    db_schema: Optional[str] = Field(None, description="Default schema")
    ssl: bool = Field(False, description="Use SSL connection")


class DatabaseConnectionUpdate(BaseModel):
    """Schema for updating a database connection"""

    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    db_schema: Optional[str] = None
    ssl: Optional[bool] = None


class DatabaseConnectionResponse(BaseModel):
    """Schema for database connection response (without password)"""

    name: str
    db_type: str
    host: str
    port: int
    database: str
    username: str
    db_schema: Optional[str] = None
    ssl: bool

    class Config:
        from_attributes = True


class DatabaseTestResult(BaseModel):
    """Schema for database connection test result"""

    status: str = Field(..., description="success or error")
    message: str = Field(..., description="Test result message")
    connection: Optional[DatabaseConnectionResponse] = None
    error: Optional[str] = None


class TableSchema(BaseModel):
    """Schema for database table metadata"""

    name: str
    columns: List[Dict[str, Any]]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]


class DatabaseSchemaResponse(BaseModel):
    """Schema for complete database schema"""

    connection_name: str
    tables: List[TableSchema]
    relationships: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class OntologyEntity(BaseModel):
    """Schema for ontology entity"""

    name: str
    type: str = Field(..., description="entity, attribute, relationship")
    description: Optional[str] = None
    source_table: Optional[str] = None
    source_column: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OntologyRelationship(BaseModel):
    """Schema for ontology relationship"""

    from_entity: str
    to_entity: str
    relationship_type: str
    cardinality: Optional[str] = None
    description: Optional[str] = None


class OntologyResponse(BaseModel):
    """Schema for ontology response"""

    name: str
    version: str
    entities: List[OntologyEntity]
    relationships: List[OntologyRelationship]
    created_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OntologySearchQuery(BaseModel):
    """Schema for ontology search query"""

    query: str = Field(..., description="Search query text")
    entity_types: Optional[List[str]] = Field(
        None, description="Filter by entity types"
    )
    limit: int = Field(10, description="Maximum results to return")


class OntologySearchResult(BaseModel):
    """Schema for ontology search result"""

    entity: OntologyEntity
    score: float = Field(..., description="Relevance score")
    matched_field: str = Field(..., description="Field that matched the query")


class OntologyExportRequest(BaseModel):
    """Schema for ontology export request"""

    format: str = Field(
        "json",
        description="Export format: json, csv, markdown"
    )
    include_concepts: bool = Field(True, description="Include concepts/entities")
    include_relationships: bool = Field(True, description="Include relationships")
    include_business_rules: bool = Field(True, description="Include business rules")
    include_uncertainties: bool = Field(False, description="Include uncertainty questions")
    selected_domains: Optional[List[str]] = Field(
        None,
        description="Filter by specific domains (None = all domains)"
    )