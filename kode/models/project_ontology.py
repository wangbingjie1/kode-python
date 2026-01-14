"""
ProjectOntology Model - 项目本体（与项目1:1）
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import relationship

from kode.database.session import Base


class ProjectOntology(Base):
    """Project ontology model - one-to-one with project"""

    __tablename__ = "project_ontologies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    ontology_data = Column(JSON)
    ontology_hash = Column(String(64), index=True)
    version = Column(Integer, default=1)

    # 向量索引
    vector_index_status = Column(String(20), default="pending")
    vector_index_path = Column(String(500))
    vector_index_built_at = Column(DateTime)
    vector_index_error = Column(Text)

    # 融合追踪
    merged_data_source_ids = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    project = relationship("Project", back_populates="ontology")

    def __repr__(self):
        return f"<ProjectOntology(id={self.id}, project={self.project_id}, version={self.version})>"
