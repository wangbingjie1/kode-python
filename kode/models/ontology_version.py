"""
Ontology Version Model

管理本体文件的版本控制，支持用户隔离和向量索引管理。
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from kode.database.session import Base
import uuid


class OntologyVersion(Base):
    """
    本体版本表

    存储每个用户的本体文件版本历史，支持：
    1. 多租户隔离（user_id）
    2. 版本管理和回滚
    3. 向量索引状态追踪
    4. 内容去重（SHA256）
    """
    __tablename__ = "ontology_versions"

    # 主键
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 用户隔离
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")

    # 连接标识
    connection_name = Column(String(100), nullable=False, index=True, comment="数据库连接名称")

    # 版本信息
    version_number = Column(Integer, nullable=False, comment="版本号（自增）")
    version_tag = Column(String(100), nullable=True, comment="版本标签（可选，如 'v1.0.0'）")
    is_snapshot = Column(Boolean, default=False, comment="是否为快照版本")
    parent_version_id = Column(String(36), ForeignKey("ontology_versions.id"), nullable=True, comment="父版本ID")

    # 存储策略
    storage_type = Column(String(20), default="file", comment="存储类型：file/db")
    file_path = Column(String(500), nullable=True, comment="文件路径（相对于 ontology_store/）")
    ontology_data = Column(JSON, nullable=True, comment="本体数据（小版本存DB，大版本存文件）")
    ontology_hash = Column(String(64), nullable=False, index=True, comment="本体内容SHA256哈希（去重用）")

    # 向量索引状态（新增）
    vector_index_status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
        comment="向量索引状态：pending/building/ready/failed"
    )
    vector_index_path = Column(String(500), nullable=True, comment="向量索引目录路径")
    vector_index_built_at = Column(DateTime, nullable=True, comment="向量索引构建完成时间")
    vector_index_error = Column(Text, nullable=True, comment="向量索引构建错误信息")

    # 元数据
    size_bytes = Column(Integer, comment="本体文件大小（字节）")
    change_summary = Column(Text, comment="变更摘要")
    created_by_conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=True, comment="创建该版本的对话ID")

    # 状态管理
    status = Column(String(20), default="active", comment="状态：active/archived/deleted")
    is_current = Column(Boolean, default=True, comment="是否为当前活跃版本")

    # 时间戳
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="创建时间")
    archived_at = Column(DateTime, nullable=True, comment="归档时间")

    # Relationships
    user = relationship("User", back_populates="ontology_versions")
    conversation = relationship("Conversation", foreign_keys=[created_by_conversation_id])
    parent_version = relationship("OntologyVersion", remote_side=[id], backref="child_versions")
    changes = relationship("OntologyChange", back_populates="ontology_version", cascade="all, delete-orphan")

    # Unique constraint: 每个用户的每个连接只能有一个 version_number
    __table_args__ = (
        {"schema": None},
    )

    def __repr__(self):
        return (
            f"<OntologyVersion("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"connection={self.connection_name}, "
            f"v{self.version_number}, "
            f"status={self.status}, "
            f"vector_index={self.vector_index_status}"
            f")>"
        )

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "connection_name": self.connection_name,
            "version_number": self.version_number,
            "version_tag": self.version_tag,
            "is_snapshot": self.is_snapshot,
            "parent_version_id": self.parent_version_id,
            "storage_type": self.storage_type,
            "file_path": self.file_path,
            "ontology_hash": self.ontology_hash,
            "vector_index_status": self.vector_index_status,
            "vector_index_path": self.vector_index_path,
            "vector_index_built_at": self.vector_index_built_at.isoformat() if self.vector_index_built_at else None,
            "vector_index_error": self.vector_index_error,
            "size_bytes": self.size_bytes,
            "change_summary": self.change_summary,
            "created_by_conversation_id": self.created_by_conversation_id,
            "status": self.status,
            "is_current": self.is_current,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }

    @property
    def full_file_path(self) -> str:
        """完整文件路径"""
        if self.storage_type == "file" and self.file_path:
            return f"ontology_store/{self.user_id}/{self.connection_name}/versions/v{self.version_number}/{self.file_path}"
        return None

    @property
    def full_vector_index_path(self) -> str:
        """完整向量索引路径"""
        if self.vector_index_path:
            return f"ontology_store/{self.user_id}/{self.connection_name}/vectors/v{self.version_number}/"
        return None
