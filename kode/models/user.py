"""
User Model

Database model for user accounts.
"""

from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from kode.database.session import Base


class User(Base):
    """User account model"""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # OAuth登录时可为空
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default="user", nullable=False)  # user, admin

    # OAuth相关字段
    auth_provider = Column(String(20), default="local")  # local, google, github等
    google_id = Column(String(255), unique=True, nullable=True, index=True)  # Google唯一标识
    avatar_url = Column(String(500), nullable=True)  # 用户头像URL

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    # Note: Access conversations through user.projects[i].conversations
    # 不要使用 secondary="projects" 的错误定义，因为 projects 不是多对多中间表

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"
