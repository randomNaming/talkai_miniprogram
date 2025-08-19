"""
Chat and learning models
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class ChatRecord(Base):
    """Chat record model - stores user conversation data for learning analysis"""
    __tablename__ = "chat_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    
    # Chat data
    user_input = Column(Text, nullable=False)
    ai_correction = Column(Text, nullable=True)  # Grammar correction info
    correction_type = Column(String, nullable=True)  # grammar, spelling, etc.
    
    # Analysis data
    grammar_errors = Column(JSON, nullable=True)    # List of grammar errors
    vocab_suggestions = Column(JSON, nullable=True)  # Suggested vocabulary
    difficulty_score = Column(Float, nullable=True)  # 0-1 scale
    
    # Learning context
    conversation_context = Column(Text, nullable=True)  # Topic/context
    user_level_estimate = Column(String, nullable=True)  # Estimated user level
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Status
    is_processed = Column(Boolean, default=False)  # For batch analysis
    analysis_batch_id = Column(String, nullable=True)  # Group for 100-record analysis
    
    # Relationships
    user = relationship("User", back_populates="chat_records")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_input": self.user_input,
            "ai_correction": self.ai_correction,
            "correction_type": self.correction_type,
            "grammar_errors": self.grammar_errors or [],
            "vocab_suggestions": self.vocab_suggestions or [],
            "difficulty_score": self.difficulty_score,
            "conversation_context": self.conversation_context,
            "user_level_estimate": self.user_level_estimate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_processed": self.is_processed,
            "analysis_batch_id": self.analysis_batch_id
        }


class LearningSummary(Base):
    """Learning summary model - stores AI-generated learning reports"""
    __tablename__ = "learning_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    
    # Summary data
    summary_content = Column(Text, nullable=False)  # AI-generated learning summary
    analysis_period = Column(String, nullable=True)  # e.g., "2024-01-01 to 2024-01-07"
    record_count = Column(Integer, nullable=False)   # Number of chat records analyzed
    
    # Learning insights
    strengths = Column(JSON, nullable=True)          # List of user strengths
    weaknesses = Column(JSON, nullable=True)         # List of areas for improvement
    recommendations = Column(JSON, nullable=True)    # List of recommendations
    progress_score = Column(Float, nullable=True)    # Overall progress score 0-100
    
    # Analysis metadata
    analysis_model = Column(String, nullable=True)   # AI model used for analysis
    analysis_version = Column(String, nullable=True) # Analysis algorithm version
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Status
    is_sent = Column(Boolean, default=False)         # Whether sent to user
    sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="learning_summaries")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "summary_content": self.summary_content,
            "analysis_period": self.analysis_period,
            "record_count": self.record_count,
            "strengths": self.strengths or [],
            "weaknesses": self.weaknesses or [],
            "recommendations": self.recommendations or [],
            "progress_score": self.progress_score,
            "analysis_model": self.analysis_model,
            "analysis_version": self.analysis_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_sent": self.is_sent,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None
        }