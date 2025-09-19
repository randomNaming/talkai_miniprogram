"""
Vocabulary models
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class VocabItem(Base):
    """Vocabulary item model - stores user's learning vocabulary (talkai_py compatible format)"""
    __tablename__ = "vocab_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    
    # Vocabulary data (from learning_vocab.json)
    word = Column(String, index=True, nullable=False)
    definition = Column(Text, nullable=True)
    phonetic = Column(String, nullable=True)
    translation = Column(Text, nullable=True)
    
    # Learning metadata (talkai_py compatible)
    source = Column(String, nullable=True)  # "lookup", "wrong_use", "right_use", "level_vocab"
    level = Column(String, nullable=True)   # difficulty level
    
    # Learning statistics (talkai_py compatible field names)
    wrong_use_count = Column(Integer, default=0)    # encounter_count - correct_count
    right_use_count = Column(Integer, default=0)    # correct_count
    last_used = Column(DateTime, nullable=True)      # last_reviewed
    added_date = Column(DateTime, default=datetime.utcnow)  # created_at
    
    # Computed fields for backward compatibility
    @property
    def encounter_count(self):
        """计算总遇到次数（兼容性属性）"""
        return (self.wrong_use_count or 0) + (self.right_use_count or 0)
    
    @property  
    def correct_count(self):
        """正确使用次数（兼容性属性）"""
        return self.right_use_count or 0
    
    # Additional fields
    familiarity = Column(Float, default=0.0)  # 0-1 scale
    mastery_score = Column(Float, default=0.0)
    
    # Semantic data
    embedding_vector = Column(Text, nullable=True)  # JSON string of vector
    related_words = Column(JSON, nullable=True)     # List of related words
    
    # Timestamps - using only last_used (removed updated_at redundancy)
    
    # Status (talkai_py compatible)
    is_active = Column(Boolean, default=True)
    isMastered = Column(Boolean, default=False)    # talkai_py compatible field name
    
    @property
    def is_mastered(self):
        """向后兼容属性"""
        return self.isMastered
    
    # Relationships
    user = relationship("User", back_populates="vocab_items")
    
    def to_dict(self):
        """Convert to dictionary (talkai_py compatible format)"""
        return {
            "id": self.id,
            "word": self.word,
            "definition": self.definition,
            "phonetic": self.phonetic,
            "translation": self.translation,
            "source": self.source,
            "level": self.level,
            # talkai_py compatible field names
            "wrong_use_count": self.wrong_use_count or 0,
            "right_use_count": self.right_use_count or 0,
            "last_used": self.last_used.isoformat() if self.last_used else "",
            "added_date": self.added_date.isoformat() if self.added_date else "",
            "isMastered": self.isMastered,
            # Additional fields
            "familiarity": self.familiarity,
            "mastery_score": self.mastery_score,
            "related_words": self.related_words or [],
            "is_active": self.is_active,
            # Computed fields for backward compatibility
            "encounter_count": self.encounter_count,
            "correct_count": self.correct_count,
            "is_mastered": self.is_mastered
        }