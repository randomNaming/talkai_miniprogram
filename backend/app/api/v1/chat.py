"""
Chat API endpoints for conversation and grammar correction
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.auth import get_current_user
from app.services.ai import ai_service
from app.models.user import User
from app.models.chat import ChatRecord

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request"""
    message: str
    include_history: bool = True


class VocabItem(BaseModel):
    """Vocabulary item for learning"""
    original: str
    corrected: str
    explanation: str = ""


class GrammarCheckResult(BaseModel):
    """Grammar check result"""
    corrected_input: str
    has_error: bool
    vocab_to_learn: List[VocabItem]


class ChatResponse(BaseModel):
    """Chat response"""
    response: str
    grammar_check: Optional[GrammarCheckResult] = None
    suggested_vocab: List[str] = []


class ConversationHistory(BaseModel):
    """Conversation history item"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str


@router.post("/send", response_model=ChatResponse)
async def send_message(
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message and get AI response with grammar correction
    
    This endpoint:
    1. Checks grammar and identifies vocabulary to learn
    2. Generates an AI response for conversation practice
    3. Records the interaction for learning analysis
    """
    try:
        user_id = current_user["sub"]
        user_input = chat_request.message.strip()
        
        if not user_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        # Get user profile
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_profile = {
            "age": user.age,
            "gender": user.gender,
            "grade": user.grade,
            "preferred_ai_model": user.preferred_ai_model
        }
        
        # Check grammar and identify vocabulary
        grammar_result = await ai_service.check_grammar_and_vocabulary(user_input)
        
        # Get conversation history if requested
        conversation_history = []
        if chat_request.include_history:
            recent_records = (
                db.query(ChatRecord)
                .filter(ChatRecord.user_id == user_id)
                .order_by(ChatRecord.created_at.desc())
                .limit(settings.max_memory_turns * 2)  # Get recent conversation turns
                .all()
            )
            
            # Convert to conversation format (reverse to chronological order)
            for record in reversed(recent_records):
                conversation_history.append({
                    "role": "user",
                    "content": record.user_input
                })
                # Note: We don't include AI responses in history to avoid confusion
                # The AI will generate appropriate responses based on user inputs
        
        # Generate AI response
        ai_response = await ai_service.generate_chat_response(
            user_input=user_input,
            user_profile=user_profile,
            conversation_history=conversation_history
        )
        
        # Save chat record for learning analysis
        chat_record = ChatRecord(
            user_id=user_id,
            user_input=user_input,
            ai_correction=grammar_result.get("corrected_input") if grammar_result.get("has_error") else None,
            correction_type="grammar" if grammar_result.get("has_error") else None,
            grammar_errors=grammar_result.get("vocab_to_learn", []),
            difficulty_score=0.5,  # TODO: Calculate based on complexity
            conversation_context="general",  # TODO: Detect topic
            is_processed=False
        )
        
        db.add(chat_record)
        
        # Update user chat count
        user.chat_history_count = (user.chat_history_count or 0) + 1
        
        db.commit()
        
        # Prepare response
        grammar_check = None
        if grammar_result.get("has_error"):
            vocab_items = []
            for item in grammar_result.get("vocab_to_learn", []):
                vocab_items.append(VocabItem(
                    original=item.get("original", ""),
                    corrected=item.get("corrected", ""),
                    explanation=item.get("explanation", "")
                ))
            
            grammar_check = GrammarCheckResult(
                corrected_input=grammar_result.get("corrected_input", user_input),
                has_error=grammar_result.get("has_error", False),
                vocab_to_learn=vocab_items
            )
        
        return ChatResponse(
            response=ai_response,
            grammar_check=grammar_check,
            suggested_vocab=[]  # TODO: Implement vocabulary suggestions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat send failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


@router.get("/history")
async def get_conversation_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get conversation history for the current user
    
    Returns recent conversation records for display purposes.
    Note: This is different from chat records used for learning analysis.
    """
    try:
        user_id = current_user["sub"]
        
        # Get recent chat records
        records = (
            db.query(ChatRecord)
            .filter(ChatRecord.user_id == user_id)
            .order_by(ChatRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        
        # Convert to conversation history format
        history = []
        for record in reversed(records):  # Reverse to chronological order
            # Add user message
            history.append(ConversationHistory(
                role="user",
                content=record.user_input,
                timestamp=record.created_at.isoformat()
            ))
            
            # Add AI response (simulated since we don't store it)
            # In a real implementation, you might store AI responses separately
            history.append(ConversationHistory(
                role="assistant", 
                content="[AI Response]",  # Placeholder
                timestamp=record.created_at.isoformat()
            ))
        
        return {
            "history": history,
            "total": len(history),
            "message": f"Retrieved {len(records)} conversation records"
        }
        
    except Exception as e:
        logger.error(f"Get conversation history failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation history"
        )


@router.post("/grammar-check", response_model=GrammarCheckResult)
async def check_grammar_only(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Check grammar and vocabulary without generating chat response
    
    Useful for quick grammar checks without full conversation context.
    """
    try:
        text = request.get("text", "").strip()
        
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text is required"
            )
        
        # Check grammar and identify vocabulary
        result = await ai_service.check_grammar_and_vocabulary(text)
        
        # Format vocabulary items
        vocab_items = []
        for item in result.get("vocab_to_learn", []):
            vocab_items.append(VocabItem(
                original=item.get("original", ""),
                corrected=item.get("corrected", ""),
                explanation=item.get("explanation", "")
            ))
        
        return GrammarCheckResult(
            corrected_input=result.get("corrected_input", text),
            has_error=result.get("has_error", False),
            vocab_to_learn=vocab_items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Grammar check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Grammar check failed"
        )


@router.get("/greeting")
async def get_initial_greeting():
    """
    Get initial greeting message for new conversations
    """
    return {
        "message": ai_service.get_initial_greeting(),
        "timestamp": datetime.utcnow().isoformat()
    }