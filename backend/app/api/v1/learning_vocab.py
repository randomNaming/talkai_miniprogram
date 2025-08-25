"""
Learning Vocabulary API - Complete replication of talkai_py learning_vocab.json functionality
This creates individual learning vocabulary database for each user, equivalent to Python version
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.vocab import VocabItem
from app.services.vocabulary import vocabulary_service

router = APIRouter()


class LearningVocabItem(BaseModel):
    """Learning vocabulary item - matches talkai_py format"""
    word: str
    level: Optional[str] = "none"
    source: str  # "level_vocab", "lookup", "wrong_use", "right_use", "user_input"
    added_date: str
    is_mastered: bool = False
    right_use_count: int = 0
    wrong_use_count: int = 0
    last_used: Optional[str] = None


class LearningVocabStats(BaseModel):
    """Learning vocabulary statistics"""
    total_words: int
    mastered_words: int
    unmastered_words: int
    mastery_percentage: float
    sources_breakdown: Dict[str, int]
    levels_breakdown: Dict[str, int]


@router.get("/", response_model=List[LearningVocabItem])
async def get_learning_vocabulary(
    is_mastered: Optional[bool] = Query(None, description="Filter by mastery status"),
    level: Optional[str] = Query(None, description="Filter by level"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's learning vocabulary - equivalent to reading learning_vocab.json in Python version
    
    This returns the user's personal vocabulary database with all the same fields:
    - word, level, source, added_date, is_mastered, right_use_count, wrong_use_count, last_used
    """
    try:
        user_id = current_user["sub"]
        
        # Build query
        query = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        )
        
        # Apply filters
        if is_mastered is not None:
            query = query.filter(VocabItem.is_mastered == is_mastered)
        
        if level:
            query = query.filter(VocabItem.level == level)
            
        if source:
            query = query.filter(VocabItem.source == source)
        
        # Order by last update
        query = query.order_by(VocabItem.updated_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        vocab_items = query.all()
        
        # Convert to learning vocab format (matching talkai_py)
        learning_vocab = []
        for item in vocab_items:
            learning_vocab_item = LearningVocabItem(
                word=item.word,
                level=item.level or "none",
                source=item.source or "level_vocab",
                added_date=item.created_at.strftime("%Y-%m-%d") if item.created_at else date.today().strftime("%Y-%m-%d"),
                is_mastered=item.is_mastered,
                right_use_count=item.correct_count,
                wrong_use_count=max(0, item.encounter_count - item.correct_count),
                last_used=item.last_reviewed.strftime("%Y-%m-%d") if item.last_reviewed else None
            )
            learning_vocab.append(learning_vocab_item)
        
        logger.info(f"Retrieved {len(learning_vocab)} learning vocabulary items for user {user_id}")
        return learning_vocab
        
    except Exception as e:
        logger.error(f"Get learning vocabulary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve learning vocabulary"
        )


@router.get("/stats", response_model=LearningVocabStats)
async def get_learning_vocabulary_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get learning vocabulary statistics - equivalent to analyzing learning_vocab.json
    """
    try:
        user_id = current_user["sub"]
        
        # Total and mastered counts
        total_count = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).count()
        
        mastered_count = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True,
            VocabItem.is_mastered == True
        ).count()
        
        # Sources breakdown
        sources = db.query(
            VocabItem.source,
            func.count(VocabItem.id).label("count")
        ).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).group_by(VocabItem.source).all()
        
        sources_breakdown = {}
        for source, count in sources:
            sources_breakdown[source or "level_vocab"] = count
        
        # Levels breakdown
        levels = db.query(
            VocabItem.level,
            func.count(VocabItem.id).label("count")
        ).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).group_by(VocabItem.level).all()
        
        levels_breakdown = {}
        for level, count in levels:
            levels_breakdown[level or "none"] = count
        
        return LearningVocabStats(
            total_words=total_count,
            mastered_words=mastered_count,
            unmastered_words=total_count - mastered_count,
            mastery_percentage=(mastered_count / total_count * 100) if total_count > 0 else 0,
            sources_breakdown=sources_breakdown,
            levels_breakdown=levels_breakdown
        )
        
    except Exception as e:
        logger.error(f"Get learning vocabulary stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get learning vocabulary statistics"
        )


@router.post("/update-usage")
async def update_vocabulary_usage(
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update vocabulary usage - equivalent to Python version's update_learning_vocab_async
    
    Usage types:
    - "right_use": Increase right_use_count
    - "wrong_use", "lookup", "user_input": Increase wrong_use_count
    
    Mastery logic: right_use_count - wrong_use_count >= 3
    """
    try:
        user_id = current_user["sub"]
        word = request.get("word", "").strip().lower()
        source = request.get("source", "user_input")
        
        if not word:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Word is required"
            )
        
        # Update vocabulary usage using the service
        success = await vocabulary_service.update_vocabulary_usage(
            user_id=user_id,
            word=word,
            usage_type=source,
            db=db
        )
        
        if success:
            return {"message": f"Updated vocabulary usage for '{word}'", "word": word, "source": source}
        else:
            return {"message": f"Failed to update vocabulary usage for '{word}'", "word": word, "source": source}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update vocabulary usage failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update vocabulary usage"
        )


@router.get("/unmastered", response_model=List[LearningVocabItem])
async def get_unmastered_vocabulary(
    limit: Optional[int] = Query(50, description="Limit number of results"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get unmastered vocabulary - equivalent to filtering learning_vocab.json for isMastered=false
    This is used for semantic similarity recommendations in talkai_py
    """
    try:
        user_id = current_user["sub"]
        
        # Get unmastered vocabulary
        vocab_items = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True,
            VocabItem.is_mastered == False
        ).order_by(VocabItem.updated_at.desc()).limit(limit).all()
        
        # Convert to learning vocab format
        unmastered_vocab = []
        for item in vocab_items:
            learning_vocab_item = LearningVocabItem(
                word=item.word,
                level=item.level or "none",
                source=item.source or "level_vocab",
                added_date=item.created_at.strftime("%Y-%m-%d") if item.created_at else date.today().strftime("%Y-%m-%d"),
                is_mastered=item.is_mastered,
                right_use_count=item.correct_count,
                wrong_use_count=max(0, item.encounter_count - item.correct_count),
                last_used=item.last_reviewed.strftime("%Y-%m-%d") if item.last_reviewed else None
            )
            unmastered_vocab.append(learning_vocab_item)
        
        logger.info(f"Retrieved {len(unmastered_vocab)} unmastered vocabulary items for user {user_id}")
        return unmastered_vocab
        
    except Exception as e:
        logger.error(f"Get unmastered vocabulary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve unmastered vocabulary"
        )


@router.post("/add-word")
async def add_learning_vocabulary_word(
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add word to learning vocabulary - equivalent to adding to learning_vocab.json
    """
    try:
        user_id = current_user["sub"]
        word = request.get("word", "").strip().lower()
        level = request.get("level", "none")
        source = request.get("source", "user_input")
        
        if not word:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Word is required"
            )
        
        # Add word using vocabulary service
        success = await vocabulary_service.add_vocabulary_item(
            user_id=user_id,
            word=word,
            level=level,
            source=source,
            db=db
        )
        
        if success:
            return {"message": f"Added '{word}' to learning vocabulary", "word": word}
        else:
            return {"message": f"Word '{word}' already exists in learning vocabulary", "word": word}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add learning vocabulary word failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add word to learning vocabulary"
        )


@router.get("/export", response_model=List[LearningVocabItem])
async def export_learning_vocabulary(
    format: str = Query("json", description="Export format (json)"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export learning vocabulary - equivalent to downloading learning_vocab.json
    """
    try:
        user_id = current_user["sub"]
        
        # Get all vocabulary items
        vocab_items = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).order_by(VocabItem.created_at.desc()).all()
        
        # Convert to learning vocab format (matching talkai_py exactly)
        learning_vocab = []
        for item in vocab_items:
            learning_vocab_item = LearningVocabItem(
                word=item.word,
                level=item.level or "none",
                source=item.source or "level_vocab",
                added_date=item.created_at.strftime("%Y-%m-%d") if item.created_at else date.today().strftime("%Y-%m-%d"),
                is_mastered=item.is_mastered,
                right_use_count=item.correct_count,
                wrong_use_count=max(0, item.encounter_count - item.correct_count),
                last_used=item.last_reviewed.strftime("%Y-%m-%d") if item.last_reviewed else None
            )
            learning_vocab.append(learning_vocab_item)
        
        logger.info(f"Exported {len(learning_vocab)} vocabulary items for user {user_id}")
        return learning_vocab
        
    except Exception as e:
        logger.error(f"Export learning vocabulary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export learning vocabulary"
        )