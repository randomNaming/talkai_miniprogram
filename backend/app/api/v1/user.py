"""
User management API endpoints
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()


class UserProfileResponse(BaseModel):
    """User profile response"""
    id: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    grade: Optional[str] = None
    added_vocab_levels: List[str] = []
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None
    total_usage_time: int = 0
    chat_history_count: int = 0
    preferred_ai_model: str = "moonshot-v1-8k"
    vocab_sync_interval: int = 24
    is_active: bool = True
    is_premium: bool = False


class UserProfileUpdateRequest(BaseModel):
    """User profile update request"""
    nickname: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    grade: Optional[str] = None
    added_vocab_levels: Optional[List[str]] = None
    preferred_ai_model: Optional[str] = None
    vocab_sync_interval: Optional[int] = None


class UsageTimeUpdateRequest(BaseModel):
    """Usage time update request"""
    session_duration: int  # seconds


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile information
    """
    try:
        user_id = current_user["sub"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserProfileResponse(
            id=user.id,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            age=user.age,
            gender=user.gender,
            grade=user.grade,
            added_vocab_levels=user.added_vocab_levels or [],
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
            total_usage_time=user.total_usage_time or 0,
            chat_history_count=user.chat_history_count or 0,
            preferred_ai_model=user.preferred_ai_model or "moonshot-v1-8k",
            vocab_sync_interval=user.vocab_sync_interval or 24,
            is_active=user.is_active,
            is_premium=user.is_premium
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user profile failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_update: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information
    """
    try:
        user_id = current_user["sub"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields if provided
        if profile_update.nickname is not None:
            user.nickname = profile_update.nickname
        if profile_update.age is not None:
            user.age = profile_update.age
        if profile_update.gender is not None:
            user.gender = profile_update.gender
        if profile_update.grade is not None:
            user.grade = profile_update.grade
        if profile_update.added_vocab_levels is not None:
            user.added_vocab_levels = profile_update.added_vocab_levels
        if profile_update.preferred_ai_model is not None:
            user.preferred_ai_model = profile_update.preferred_ai_model
        if profile_update.vocab_sync_interval is not None:
            user.vocab_sync_interval = profile_update.vocab_sync_interval
        
        db.commit()
        db.refresh(user)
        
        return UserProfileResponse(
            id=user.id,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            age=user.age,
            gender=user.gender,
            grade=user.grade,
            added_vocab_levels=user.added_vocab_levels or [],
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
            total_usage_time=user.total_usage_time or 0,
            chat_history_count=user.chat_history_count or 0,
            preferred_ai_model=user.preferred_ai_model or "moonshot-v1-8k",
            vocab_sync_interval=user.vocab_sync_interval or 24,
            is_active=user.is_active,
            is_premium=user.is_premium
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user profile failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.post("/usage-time")
async def update_usage_time(
    usage_update: UsageTimeUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's total usage time
    
    This endpoint is called when a user session ends to track learning time.
    """
    try:
        user_id = current_user["sub"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Add session duration to total usage time
        user.total_usage_time = (user.total_usage_time or 0) + usage_update.session_duration
        user.last_login_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "message": "Usage time updated successfully",
            "total_usage_time": user.total_usage_time,
            "session_duration": usage_update.session_duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update usage time failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update usage time"
        )


@router.get("/stats")
async def get_user_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's learning statistics
    """
    try:
        user_id = current_user["sub"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get vocabulary count
        from app.models.vocab import VocabItem
        vocab_count = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).count()
        
        # Get learning summary count
        from app.models.chat import LearningSummary
        summary_count = db.query(LearningSummary).filter(
            LearningSummary.user_id == user_id
        ).count()
        
        # Calculate days since registration
        days_since_registration = 0
        if user.created_at:
            days_since_registration = (datetime.utcnow() - user.created_at).days
        
        return {
            "user_id": user.id,
            "total_usage_time": user.total_usage_time or 0,
            "chat_history_count": user.chat_history_count or 0,
            "vocab_count": vocab_count,
            "learning_summaries": summary_count,
            "days_since_registration": days_since_registration,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "is_premium": user.is_premium,
            "grade": user.grade,
            "preferred_ai_model": user.preferred_ai_model
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user statistics"
        )


@router.delete("/account")
async def delete_user_account(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account and all associated data
    
    This is a soft delete - marks the user as inactive.
    """
    try:
        user_id = current_user["sub"]
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Soft delete - mark as inactive
        user.is_active = False
        
        # Also mark vocabulary items as inactive
        from app.models.vocab import VocabItem
        db.query(VocabItem).filter(VocabItem.user_id == user_id).update(
            {"is_active": False}
        )
        
        db.commit()
        
        return {"message": "Account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user account failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user account"
        )