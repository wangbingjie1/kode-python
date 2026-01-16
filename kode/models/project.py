"""
Project Model

Database model for user projects.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from kode.database.session import Base


class Project(Base):
    """Project model for organizing conversations"""

    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(
        String(36), ForeignKey("organizations.id"), index=True, nullable=True
    )
    config = Column(JSON, default=dict)  # Project-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # UI 相关字段
    icon = Column(String(10), default="📊")  # 项目图标（emoji）
    business_type = Column(String(50), nullable=True)  # 业务类型：ecommerce, finance, hr 等
    status = Column(String(20), default="active")  # 状态：active, archived, deleted
    is_pinned = Column(Boolean, default=False)  # 是否置顶
    needs_etl = Column(Boolean, default=True)  # 是否需要 ETL 处理
    ontology_built = Column(Boolean, default=False)  # 本体是否已构建

    # Relationships
    user = relationship("User", back_populates="projects")
    organization = relationship("Organization", back_populates="projects")
    conversations = relationship(
        "Conversation", back_populates="project", cascade="all, delete-orphan"
    )
    data_source_associations = relationship(
        "ProjectDataSource", back_populates="project", cascade="all, delete-orphan"
    )
    ontology = relationship(
        "ProjectOntology",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name})>"
