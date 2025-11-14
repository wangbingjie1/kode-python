"""
Conversation Model

Database model for chat conversations.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from kode.database.session import Base


class Conversation(Base):
    """Conversation model for chat sessions"""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False, default="New Conversation")
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    # Note: Access user through conversation.project.user
    # 不要使用 secondary="projects" 的错误定义，因为 projects 不是多对多中间表

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title})>"
