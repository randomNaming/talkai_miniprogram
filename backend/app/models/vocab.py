"""
Vocabulary models
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class VocabItem(Base):
    """Vocabulary item model - stores user's learning vocabulary"""
    __tablename__ = "vocab_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    
    # Vocabulary data (from learning_vocab.json)
    word = Column(String, index=True, nullable=False)
    definition = Column(Text, nullable=True)
    phonetic = Column(String, nullable=True)
    translation = Column(Text, nullable=True)
    
    # Learning metadata
    source = Column(String, nullable=True)  # CET4, TOEFL, etc.
    level = Column(String, nullable=True)   # difficulty level
    familiarity = Column(Float, default=0.0)  # 0-1 scale
    
    # Learning statistics
    encounter_count = Column(Integer, default=1)
    correct_count = Column(Integer, default=0)
    last_reviewed = Column(DateTime, nullable=True)
    mastery_score = Column(Float, default=0.0)
    
    # Semantic data
    embedding_vector = Column(Text, nullable=True)  # JSON string of vector
    related_words = Column(JSON, nullable=True)     # List of related words
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_mastered = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="vocab_items")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "word": self.word,
            "definition": self.definition,
            "phonetic": self.phonetic,
            "translation": self.translation,
            "source": self.source,
            "level": self.level,
            "familiarity": self.familiarity,
            "encounter_count": self.encounter_count,
            "correct_count": self.correct_count,
            "last_reviewed": self.last_reviewed.isoformat() if self.last_reviewed else None,
            "mastery_score": self.mastery_score,
            "related_words": self.related_words or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "is_mastered": self.is_mastered
        }