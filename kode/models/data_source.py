"""
DataSource Model - 统一数据源模型（文件+数据库）
"""

from datetime import datetime
from uuid import uuid4
from enum import Enum as PyEnum
from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    JSON,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from kode.database.session import Base


class DataSourceType(str, PyEnum):
    FILE = "file"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    MONGODB = "mongodb"


class DataSourceStatus(str, PyEnum):
    PENDING = "pending"
    READY = "ready"
    ERROR = "error"
    ARCHIVED = "archived"


class DataSource(Base):
    """Unified data source model for files and databases"""

    __tablename__ = "data_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id = Column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )

    name = Column(String(100), nullable=False)
    source_type = Column(Enum(DataSourceType), nullable=False)
    status = Column(Enum(DataSourceStatus), default=DataSourceStatus.PENDING)

    # 文件类型字段
    file_path = Column(String(500))
    original_filename = Column(String(255))
    file_size = Column(BigInteger)
    file_mime_type = Column(String(100))

    # 数据库类型字段
    host = Column(String(255))
    port = Column(Integer)
    database = Column(String(255))
    username = Column(String(100))
    encrypted_password = Column(Text)
    db_schema = Column(String(100))
    ssl_enabled = Column(Boolean, default=False)

    # 通用
    config = Column(JSON)
    schema_cache = Column(JSON)
    schema_cached_at = Column(DateTime)
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    organization = relationship("Organization", back_populates="data_sources")
    project_associations = relationship(
        "ProjectDataSource", back_populates="data_source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_org_datasource_name"),
    )

    def to_dict(self):
        """转为字典（不含密码）"""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "source_type": self.source_type.value if self.source_type else None,
            "status": self.status.value if self.status else None,
            "file_path": self.file_path,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "db_schema": self.db_schema,
            "ssl_enabled": self.ssl_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<DataSource(id={self.id}, name={self.name}, type={self.source_type})>"
