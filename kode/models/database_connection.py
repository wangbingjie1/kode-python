"""
Database Connection Model

SQLAlchemy model for persisting database connection configurations.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from datetime import datetime
import uuid

from kode.database.session import Base


class DatabaseConnectionModel(Base):
    """Database connection configuration model for persistence"""

    __tablename__ = "database_connections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    db_type = Column(String(50), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    database = Column(String(255), nullable=False)
    username = Column(String(100), nullable=False)
    # Encrypted password storage - should use encryption in production
    password = Column(Text, nullable=False)
    db_schema = Column(String(100), nullable=True)
    ssl = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<DatabaseConnection(id={self.id}, name={self.name}, db_type={self.db_type})>"

    def to_dict(self):
        """Convert to dictionary (without sensitive password data)"""
        return {
            "id": self.id,
            "name": self.name,
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "db_schema": self.db_schema,
            "ssl": self.ssl,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
