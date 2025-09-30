"""SQLAlchemy models."""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from src.database import Base


class Snippet(Base):
    """Snippet model."""
    __tablename__ = "snippets"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(Text, nullable=False, default='[]')
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    deleted_at = Column(DateTime, nullable=True)
    content_hash = Column(String(64), nullable=False, unique=True)
    
    __table_args__ = (
        Index('idx_snippets_deleted_at', 'deleted_at'),
        Index('idx_snippets_content_hash', 'content_hash'),
        Index('idx_snippets_created_at', 'created_at'),
    )
