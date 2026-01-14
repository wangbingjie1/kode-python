"""
Ontology Change Model

Tracks all changes made to database ontologies for audit and reflection purposes.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from kode.database.session import Base
import enum


class ChangeType(enum.Enum):
    """本体变更类型枚举"""
    # Layer 1: 元数据层变更（直接JSON操作）
    ADD_ENUM_VALUE = "add_enum_value"              # 添加枚举值
    UPDATE_PROPERTY_DESC = "update_property_desc"  # 更新属性描述
    UPDATE_CLASS_DESC = "update_class_desc"        # 更新类描述
    UPDATE_CLASS_MAPPING = "update_class_mapping"  # 更新类的表映射（修正查错表问题）
    UPDATE_COLUMN_MAPPING = "update_column_mapping"  # 更新属性的字段映射（修正字段错误）

    # Layer 2: 领域重建变更
    ADD_CLASS = "add_class"                        # 添加新类
    ADD_PROPERTY = "add_property"                  # 添加新属性
    ADD_RELATIONSHIP = "add_relationship"          # 添加新关系

    # Layer 2.5: Domain 重新聚类变更
    MOVE_TABLE_DOMAIN = "move_table_domain"        # 将表从一个 Domain 移动到另一个 Domain

    # Layer 3: 全局一致性变更
    MERGE_CLASSES = "merge_classes"                # 合并类
    SPLIT_CLASS = "split_class"                    # 拆分类


class ChangeStatus(enum.Enum):
    """变更状态"""
    PENDING = "pending"      # 待应用
    APPLIED = "applied"      # 已应用
    REVERTED = "reverted"    # 已回滚
    FAILED = "failed"        # 应用失败


class OntologyChange(Base):
    """
    本体变更记录表

    记录所有对本体的修改，用于：
    1. 审计跟踪
    2. 变更回滚
    3. 反思时的冲突检测
    4. 高频修改的批量优化
    """
    __tablename__ = "ontology_changes"

    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 关联信息（用户隔离）
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    connection_name = Column(String(100), nullable=False, index=True, comment="数据库连接名称")
    conversation_id = Column(Integer, nullable=True, index=True, comment="对话ID（如果通过对话触发）")
    ontology_version_id = Column(String(36), ForeignKey("ontology_versions.id", ondelete="SET NULL"), nullable=True, index=True, comment="关联的本体版本ID")

    # 变更元数据
    change_type = Column(SQLEnum(ChangeType), nullable=False, index=True, comment="变更类型")
    target_path = Column(String(500), nullable=False, comment="目标路径（JSON path，如 classes.User.properties.age）")

    # 变更内容
    old_value = Column(JSON, nullable=True, comment="旧值（JSON格式）")
    new_value = Column(JSON, nullable=False, comment="新值（JSON格式）")

    # 用户意图与上下文
    user_intent = Column(Text, nullable=True, comment="用户意图描述")
    context = Column(JSON, nullable=True, comment="变更上下文（相关实体、依赖项等）")

    # 影响分析
    impact_score = Column(Integer, default=0, comment="影响分数（0-100，用于决定更新策略）")
    affected_entities = Column(JSON, nullable=True, comment="受影响的实体列表")

    # 状态管理
    status = Column(SQLEnum(ChangeStatus), nullable=False, default=ChangeStatus.PENDING, index=True, comment="变更状态")
    error_message = Column(Text, nullable=True, comment="错误信息（如果状态为FAILED）")

    # 时间戳
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    applied_at = Column(DateTime, nullable=True, comment="应用时间")

    # 批次管理（用于批量优化）
    batch_id = Column(String(50), nullable=True, index=True, comment="批次ID（高频修改时使用）")

    # Relationships
    user = relationship("User")
    ontology_version = relationship("OntologyVersion", back_populates="changes")

    def __repr__(self):
        return (
            f"<OntologyChange("
            f"id={self.id}, "
            f"connection={self.connection_name}, "
            f"type={self.change_type.value}, "
            f"path={self.target_path}, "
            f"status={self.status.value}"
            f")>"
        )

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "connection_name": self.connection_name,
            "conversation_id": self.conversation_id,
            "ontology_version_id": self.ontology_version_id,
            "change_type": self.change_type.value,
            "target_path": self.target_path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "user_intent": self.user_intent,
            "context": self.context,
            "impact_score": self.impact_score,
            "affected_entities": self.affected_entities,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "batch_id": self.batch_id,
        }
