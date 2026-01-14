"""
ProjectDataSource Model - 项目与数据源多对多关联
"""

from datetime import datetime
from uuid import uuid4
from enum import Enum as PyEnum
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from kode.database.session import Base


class ProjectDataSourceStatus(str, PyEnum):
    LINKED = "linked"
    MERGED = "merged"
    PENDING_MERGE = "pending_merge"


class ProjectDataSource(Base):
    """Many-to-many association between projects and data sources"""

    __tablename__ = "project_data_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    data_source_id = Column(
        String(36),
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        index=True,
    )

    status = Column(
        Enum(ProjectDataSourceStatus), default=ProjectDataSourceStatus.LINKED
    )
    merged_at = Column(DateTime)
    merged_by_conversation_id = Column(String(36))

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    project = relationship("Project", back_populates="data_source_associations")
    data_source = relationship("DataSource", back_populates="project_associations")

    __table_args__ = (
        UniqueConstraint("project_id", "data_source_id", name="uq_project_datasource"),
    )

    def __repr__(self):
        return f"<ProjectDataSource(project={self.project_id}, data_source={self.data_source_id})>"
