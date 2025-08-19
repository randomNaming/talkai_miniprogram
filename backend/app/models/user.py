"""
User model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    openid = Column(String, unique=True, index=True, nullable=False)
    nickname = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    
    # User profile data (from original user_profiles.json)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    grade = Column(String, nullable=True)  # Primary School, etc.
    added_vocab_levels = Column(JSON, nullable=True)  # List of added levels
    
    # New fields for online version
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, default=datetime.utcnow)
    total_usage_time = Column(Integer, default=0)  # in seconds
    chat_history_count = Column(Integer, default=0)
    
    # Learning preferences
    preferred_ai_model = Column(String, default="moonshot-v1-8k")
    vocab_sync_interval = Column(Integer, default=24)  # hours
    
    # Status
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    
    # Relationships
    vocab_items = relationship("VocabItem", back_populates="user", cascade="all, delete-orphan")
    chat_records = relationship("ChatRecord", back_populates="user", cascade="all, delete-orphan")
    learning_summaries = relationship("LearningSummary", back_populates="user", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "openid": self.openid,
            "nickname": self.nickname,
            "avatar_url": self.avatar_url,
            "age": self.age,
            "gender": self.gender,
            "grade": self.grade,
            "added_vocab_levels": self.added_vocab_levels or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "total_usage_time": self.total_usage_time,
            "chat_history_count": self.chat_history_count,
            "preferred_ai_model": self.preferred_ai_model,
            "vocab_sync_interval": self.vocab_sync_interval,
            "is_active": self.is_active,
            "is_premium": self.is_premium
        }