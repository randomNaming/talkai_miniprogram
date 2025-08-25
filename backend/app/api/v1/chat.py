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
    
    Following talkai_py pattern:
    1. FIRST: Generate AI dialogue response using conversation memory (fast response to UI)
    2. SECOND: Check grammar/correction in parallel (separate AI call, different prompt)
    3. THIRD: Generate vocabulary suggestions based on conversation context
    
    Key differences from previous implementation:
    - AI dialogue and grammar correction are separate AI model calls
    - Only natural conversation is saved in memory (not corrections)
    - Faster response by immediately returning dialogue, processing corrections async
    """
    import asyncio
    
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
            "user_id": user_id,
            "age": user.age,
            "gender": user.gender,
            "grade": user.grade,
            "preferred_ai_model": user.preferred_ai_model
        }
        
        # STEP 1: IMMEDIATE AI DIALOGUE RESPONSE (using conversation memory)
        # This uses LangChain ConversationBufferWindowMemory and saves to memory
        logger.info(f"Step 1: Generating natural dialogue response for user {user_id}")
        response_result = ai_service.generate_response_natural(
            user_input=user_input,
            user_profile=user_profile,
            user_id=user_id  # This will use user-specific memory
        )
        ai_response = response_result.get("text", "")
        
        # STEP 2 & 3: PARALLEL PROCESSING (grammar check + vocabulary suggestions)
        # These run separately and don't affect conversation memory
        logger.info(f"Step 2&3: Starting parallel grammar check and vocabulary suggestions")
        
        async def grammar_check_task():
            """Separate grammar check task - does NOT affect conversation memory"""
            return ai_service.check_vocab_from_input(user_input)  # Different AI call, different prompt
        
        async def vocab_suggestion_task():
            """Vocabulary suggestion task based on conversation context"""
            return await ai_service.suggest_vocabulary(
                user_id=user_id,
                user_input=user_input,
                ai_response=ai_response,
                db=db
            )
        
        # Run grammar check and vocabulary suggestions in parallel
        grammar_result, suggested_vocab = await asyncio.gather(
            grammar_check_task(),
            vocab_suggestion_task(),
            return_exceptions=True
        )
        
        # Handle potential exceptions from parallel tasks
        if isinstance(grammar_result, Exception):
            logger.error(f"Grammar check failed: {grammar_result}")
            grammar_result = {"corrected_input": None, "words_deserve_to_learn": []}
        
        if isinstance(suggested_vocab, Exception):
            logger.error(f"Vocabulary suggestion failed: {suggested_vocab}")
            suggested_vocab = []
        
        # STEP 4: SAVE CHAT RECORD (only natural conversation, not corrections)
        chat_record = ChatRecord(
            user_id=user_id,
            user_input=user_input,
            ai_correction=grammar_result.get("corrected_input") if grammar_result.get("has_error") else None,
            correction_type="grammar" if grammar_result.get("has_error") else None,
            grammar_errors=grammar_result.get("vocab_to_learn", []),
            difficulty_score=0.5,
            conversation_context="general",
            is_processed=False
        )
        
        db.add(chat_record)
        user.chat_history_count = (user.chat_history_count or 0) + 1
        db.commit()
        
        # STEP 5: PREPARE RESPONSE FORMAT
        grammar_check = None
        corrected_input = grammar_result.get("corrected_input")
        words_deserve_to_learn = grammar_result.get("words_deserve_to_learn", [])
        
        # Only show correction if corrected_input exists AND is different from user input
        if corrected_input and corrected_input != user_input:
            vocab_items = []
            for item in words_deserve_to_learn:
                vocab_items.append(VocabItem(
                    original=item.get("original", ""),
                    corrected=item.get("corrected", ""),
                    explanation=item.get("explanation", "")
                ))
            
            grammar_check = GrammarCheckResult(
                corrected_input=corrected_input,
                has_error=True,
                vocab_to_learn=vocab_items
            )
        
        # STEP 6: ASYNCHRONOUS VOCABULARY DATABASE UPDATE (background task)
        if grammar_result.get("corrected_input") is not None:
            # Run in background - don't wait for this
            asyncio.create_task(
                ai_service.update_vocabulary_from_correction(
                    grammar_result=grammar_result,
                    user_input=user_input,
                    user_id=user_id,
                    db=db
                )
            )
        
        logger.info(f"Chat response completed for user {user_id}: dialogue={len(ai_response)} chars, corrections={len(words_deserve_to_learn)}, vocab_suggestions={len(suggested_vocab or [])}")
        
        return ChatResponse(
            response=ai_response,
            grammar_check=grammar_check,
            suggested_vocab=suggested_vocab or []
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


@router.post("/auto-message")
async def generate_auto_message(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate automatic conversation starter when user is inactive
    
    This mimics the auto-message feature from talkai_py where the AI
    proactively suggests new conversation topics.
    """
    try:
        user_id = current_user["sub"]
        
        # Get user profile
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_profile = {
            "user_id": user_id,  # Add user_id for vocabulary suggestions
            "age": user.age,
            "gender": user.gender,
            "grade": user.grade,
            "preferred_ai_model": user.preferred_ai_model
        }
        
        # Get recent conversation context
        recent_records = (
            db.query(ChatRecord)
            .filter(ChatRecord.user_id == user_id)
            .order_by(ChatRecord.created_at.desc())
            .limit(5)  # Last few messages for context
            .all()
        )
        
        conversation_context = []
        for record in reversed(recent_records):
            conversation_context.append({
                "role": "user", 
                "content": record.user_input
            })
        
        # Generate auto message based on user profile and recent context
        auto_message = await ai_service.generate_auto_message(
            user_profile=user_profile,
            conversation_history=conversation_context
        )
        
        return {
            "message": auto_message,
            "timestamp": datetime.utcnow().isoformat(),
            "is_auto_generated": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auto message generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate auto message"
        )