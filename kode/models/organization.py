"""
Organization Model - 组织模型，与用户1:1关系
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from kode.database.session import Base


class Organization(Base):
    """Organization model - each user has one organization"""

    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    owner_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # 配额
    max_projects = Column(Integer, default=3)
    max_data_sources = Column(Integer, default=5)
    max_storage_bytes = Column(BigInteger, default=500 * 1024 * 1024)  # 500MB

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    owner = relationship("User", back_populates="organization")
    projects = relationship(
        "Project", back_populates="organization", cascade="all, delete-orphan"
    )
    data_sources = relationship(
        "DataSource", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name})>"
