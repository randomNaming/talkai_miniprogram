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
    explanation: str = ""


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
    LEGACY API: 发送消息并获取完整响应 (保持向后兼容)
    建议使用新的流式API: /send-stream
    """
    return await _send_message_complete(chat_request, current_user, db)


@router.post("/send-stream")
async def send_message_stream(
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    流式消息发送 - 分线程独立输出减少用户等待时间
    复制 talkai_py 中 MessageProcessingThread 的逻辑
    
    返回格式：
    1. 立即返回 AI 对话响应
    2. 后台异步处理语法纠正和词汇建议
    3. 支持分步骤接收结果
    """
    import asyncio
    from fastapi.responses import StreamingResponse
    import json
    
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
        
        async def stream_generator():
            """生成器函数，依次返回各个处理步骤的结果"""
            
            # 步骤1: 立即生成AI对话响应
            logger.info(f"Stream Step 1: Generating natural dialogue response for user {user_id}")
            response_result = ai_service.generate_response_natural(
                user_input=user_input,
                user_profile=user_profile,
                user_id=user_id
            )
            ai_response = response_result.get("text", "")
            
            # 立即返回AI响应
            yield f"data: {json.dumps({'type': 'ai_response', 'content': ai_response})}\n\n"
            
            # 步骤2: 异步语法检查
            logger.info(f"Stream Step 2: Starting grammar check")
            try:
                grammar_result = ai_service.check_vocab_from_input(user_input)
                yield f"data: {json.dumps({'type': 'grammar_check', 'content': grammar_result})}\n\n"
            except Exception as e:
                logger.error(f"Grammar check failed: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Grammar check failed: {str(e)}'})}\n\n"
            
            # 步骤3: 异步词汇建议
            logger.info(f"Stream Step 3: Starting vocabulary suggestions")
            try:
                suggested_vocab = await ai_service.suggest_vocabulary(
                    user_id=user_id,
                    user_input=user_input,
                    ai_response=ai_response,
                    db=db
                )
                yield f"data: {json.dumps({'type': 'vocabulary_suggestions', 'content': suggested_vocab})}\n\n"
            except Exception as e:
                logger.error(f"Vocabulary suggestion failed: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Vocabulary suggestion failed: {str(e)}'})}\n\n"
            
            # 步骤4: 取消自动词汇更新 - 只在用户点击"+"号时手动添加
            # 异步词汇更新 (如果有语法纠正结果) - 已注释，改为手动添加模式
            # if 'grammar_result' in locals() and grammar_result:
            #     logger.info(f"Stream Step 4: Starting vocabulary update")
            #     try:
            #         await ai_service.update_vocabulary_from_correction(
            #             grammar_result=grammar_result,
            #             user_input=user_input,
            #             user_id=user_id,
            #             db=db
            #         )
            #         yield f"data: {json.dumps({'type': 'vocab_update_complete', 'content': 'success'})}\n\n"
            #     except Exception as e:
            #         logger.error(f"Vocabulary update failed: {e}")
            #         yield f"data: {json.dumps({'type': 'error', 'content': f'Vocabulary update failed: {str(e)}'})}\n\n"
            
            # 步骤5: 保存聊天记录
            try:
                chat_record = ChatRecord(
                    user_id=user_id,
                    user_input=user_input,
                    ai_response=ai_response,
                    ai_correction=grammar_result.get("corrected_input") if 'grammar_result' in locals() and grammar_result.get("has_error") else None,
                    created_at=datetime.utcnow()
                )
                db.add(chat_record)
                db.commit()
                
                yield f"data: {json.dumps({'type': 'chat_saved', 'content': 'success'})}\n\n"
            except Exception as e:
                logger.error(f"Chat record save failed: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Chat record save failed: {str(e)}'})}\n\n"
            
            # 完成信号
            yield f"data: {json.dumps({'type': 'complete', 'content': 'all_tasks_completed'})}\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"Stream chat failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


async def _send_message_complete(
    chat_request: ChatRequest,
    current_user: dict,
    db: Session
) -> ChatResponse:
    """
    Send a message and get IMMEDIATE AI response only (like talkai_py pattern)
    
    Following talkai_py MessageProcessingThread pattern:
    1. IMMEDIATE: Generate and return AI dialogue response only
    2. Grammar correction and vocabulary suggestions will be called separately by frontend
    
    This enables true progressive display like talkai_py where:
    - AI response shows immediately (~1s)
    - Grammar correction shows separately (~1s later) 
    - Vocabulary suggestions show separately (~1s later)
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
            "user_id": user_id,
            "age": user.age,
            "gender": user.gender,
            "grade": user.grade,
            "preferred_ai_model": user.preferred_ai_model
        }
        
        # STEP 1: IMMEDIATE AI DIALOGUE RESPONSE ONLY
        # Just like talkai_py - return AI response immediately, everything else is separate
        logger.info(f"Immediate AI response for user {user_id}")
        response_result = ai_service.generate_response_natural(
            user_input=user_input,
            user_profile=user_profile,
            user_id=user_id
        )
        ai_response = response_result.get("text", "")
        
        # STEP 2: SAVE CHAT RECORD (basic record, no corrections yet)
        chat_record = ChatRecord(
            user_id=user_id,
            user_input=user_input,
            ai_correction=None,  # Will be updated later if needed
            correction_type=None,
            grammar_errors=[],
            difficulty_score=0.5,
            conversation_context="general",
            is_processed=False
        )
        
        db.add(chat_record)
        user.chat_history_count = (user.chat_history_count or 0) + 1
        db.commit()
        
        logger.info(f"Immediate AI response completed for user {user_id}: {len(ai_response)} chars")
        
        # Return ONLY AI response - no grammar check, no vocab suggestions
        # Frontend will call separate endpoints for those
        return ChatResponse(
            response=ai_response,
            grammar_check=None,
            suggested_vocab=[]
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check grammar and vocabulary for progressive display (like talkai_py correction_ready signal)
    
    This endpoint is called separately after AI response to provide grammar correction.
    Implements the same logic as talkai_py MessageProcessingThread Step 3.
    """
    try:
        text = request.get("text", "").strip()
        
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text is required"
            )
        
        user_id = current_user["sub"]
        logger.info(f"Grammar check for user {user_id}: {text[:50]}...")
        
        # Use the same grammar check method as talkai_py
        result = ai_service.check_vocab_from_input(text)
        
        # Format vocabulary items
        vocab_items = []
        words_deserve_to_learn = result.get("words_deserve_to_learn", [])
        for item in words_deserve_to_learn:
            vocab_items.append(VocabItem(
                original=item.get("original", ""),
                corrected=item.get("corrected", ""),
                explanation=item.get("explanation", "")
            ))
        
        corrected_input = result.get("corrected_input")
        
        # 根据talkai_py逻辑，只有实质性语法/词汇错误才显示纠错
        # 忽略纯标点符号差异(如缺少句号、逗号、问号等)
        if corrected_input and corrected_input != text:
            # 检查是否只是标点符号差异
            import re
            text_no_punct = re.sub(r'[.,!?;:\s]+$', '', text)
            corrected_no_punct = re.sub(r'[.,!?;:\s]+$', '', corrected_input)
            is_just_punctuation = text_no_punct.lower() == corrected_no_punct.lower()
            
            # 只有非标点差异的实质性错误才算has_error
            has_error = not is_just_punctuation
        else:
            has_error = False
        
        # 注释掉自动词汇更新：错词不再自动添加到词汇库，只有用户点击"+"号时才手动添加
        # Background vocabulary update (like talkai_py)
        # if has_error and result:
        #     import asyncio
        #     asyncio.create_task(
        #         ai_service.update_vocabulary_from_correction(
        #             grammar_result=result,
        #             user_input=text,
        #             user_id=user_id,
        #             db=db
        #         )
        #     )
        
        return GrammarCheckResult(
            corrected_input=corrected_input or text,
            has_error=has_error,
            vocab_to_learn=vocab_items,
            explanation=result.get("explanation", "")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Grammar check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Grammar check failed"
        )


@router.post("/vocabulary-suggestions")
async def get_vocabulary_suggestions(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get vocabulary suggestions for progressive display (like talkai_py vocabulary_ready signal)
    
    This endpoint is called separately after grammar check to provide vocabulary suggestions.
    Implements the same logic as talkai_py MessageProcessingThread Step 4.
    """
    try:
        user_input = request.get("user_input", "").strip()
        ai_response = request.get("ai_response", "").strip()
        
        if not user_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_input is required"
            )
        
        user_id = current_user["sub"]
        logger.info(f"Vocabulary suggestions for user {user_id}")
        
        # Use the same vocabulary suggestion method as talkai_py
        suggested_vocab = await ai_service.suggest_vocabulary(
            user_id=user_id,
            user_input=user_input,
            ai_response=ai_response,
            db=db
        )
        
        return {
            "suggested_vocab": suggested_vocab or [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vocabulary suggestions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vocabulary suggestions failed"
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