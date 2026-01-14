"""
ProjectOntology Schemas

Pydantic models for project ontology API request/response validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectOntologyResponse(BaseModel):
    """Project ontology response"""

    id: str
    project_id: str
    version: int
    ontology_hash: Optional[str] = None
    vector_index_status: str
    merged_data_source_ids: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OntologyDataResponse(BaseModel):
    """Ontology data response"""

    ontology: Dict[str, Any]
    version: int
    merged_sources: List[str] = []


class OntologySearchRequest(BaseModel):
    """Ontology search request"""

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)


class OntologySearchResult(BaseModel):
    """Search result"""

    entity_type: str  # class, property, relationship
    name: str
    description: Optional[str] = None
    score: float
    metadata: Dict[str, Any] = {}


class OntologySearchResponse(BaseModel):
    """Ontology search response"""

    results: List[OntologySearchResult]
    query: str


class OntologyMergeRequest(BaseModel):
    """Ontology merge request"""

    data_source_ids: List[str] = Field(..., min_length=1)
    force_rebuild: bool = False


class OntologyMergeResponse(BaseModel):
    """Ontology merge response"""

    success: bool
    message: str
    version: Optional[int] = None
    merged_sources: List[str] = []
