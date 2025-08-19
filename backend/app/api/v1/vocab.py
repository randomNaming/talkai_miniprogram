"""
Vocabulary management API endpoints
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.vocab import VocabItem
from app.services.dictionary import dictionary_service

router = APIRouter()


class VocabItemResponse(BaseModel):
    """Vocabulary item response"""
    id: int
    word: str
    definition: Optional[str] = ""
    phonetic: Optional[str] = ""
    translation: Optional[str] = ""
    source: Optional[str] = ""
    level: Optional[str] = ""
    familiarity: float = 0.0
    encounter_count: int = 1
    correct_count: int = 0
    last_reviewed: Optional[str] = None
    mastery_score: float = 0.0
    related_words: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_active: bool = True
    is_mastered: bool = False


class VocabItemCreateRequest(BaseModel):
    """Create vocabulary item request"""
    word: str
    definition: Optional[str] = None
    phonetic: Optional[str] = None
    translation: Optional[str] = None
    source: Optional[str] = None
    level: Optional[str] = None
    auto_lookup: bool = True  # Whether to auto-lookup word details


class VocabItemUpdateRequest(BaseModel):
    """Update vocabulary item request"""
    definition: Optional[str] = None
    phonetic: Optional[str] = None
    translation: Optional[str] = None
    source: Optional[str] = None
    level: Optional[str] = None
    familiarity: Optional[float] = None
    mastery_score: Optional[float] = None
    is_mastered: Optional[bool] = None


class VocabBulkCreateRequest(BaseModel):
    """Bulk create vocabulary items request"""
    words: List[str]
    source: Optional[str] = None
    level: Optional[str] = None
    auto_lookup: bool = True


@router.get("/", response_model=List[VocabItemResponse])
async def get_vocabulary_list(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    is_mastered: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's vocabulary list with filtering and pagination
    """
    try:
        user_id = current_user["sub"]
        
        # Build query
        query = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        )
        
        # Apply filters
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                VocabItem.word.ilike(search_term) |
                VocabItem.definition.ilike(search_term) |
                VocabItem.translation.ilike(search_term)
            )
        
        if level:
            query = query.filter(VocabItem.level == level)
        
        if is_mastered is not None:
            query = query.filter(VocabItem.is_mastered == is_mastered)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        vocab_items = (
            query
            .order_by(VocabItem.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        # Convert to response format
        results = []
        for item in vocab_items:
            results.append(VocabItemResponse(
                id=item.id,
                word=item.word,
                definition=item.definition or "",
                phonetic=item.phonetic or "",
                translation=item.translation or "",
                source=item.source or "",
                level=item.level or "",
                familiarity=item.familiarity,
                encounter_count=item.encounter_count,
                correct_count=item.correct_count,
                last_reviewed=item.last_reviewed.isoformat() if item.last_reviewed else None,
                mastery_score=item.mastery_score,
                related_words=item.related_words or [],
                created_at=item.created_at.isoformat() if item.created_at else None,
                updated_at=item.updated_at.isoformat() if item.updated_at else None,
                is_active=item.is_active,
                is_mastered=item.is_mastered
            ))
        
        return results
        
    except Exception as e:
        logger.error(f"Get vocabulary list failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get vocabulary list"
        )


@router.post("/", response_model=VocabItemResponse)
async def create_vocabulary_item(
    vocab_request: VocabItemCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new vocabulary item for the user
    """
    try:
        user_id = current_user["sub"]
        word = vocab_request.word.strip().lower()
        
        if not word:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Word is required"
            )
        
        # Check if word already exists for this user
        existing = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.word == word,
            VocabItem.is_active == True
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Word already exists in vocabulary"
            )
        
        # Auto-lookup word details if requested
        definition = vocab_request.definition
        phonetic = vocab_request.phonetic
        translation = vocab_request.translation
        
        if vocab_request.auto_lookup:
            word_info = dictionary_service.query_word(word)
            if word_info:
                definition = definition or word_info.get("definition", "")
                phonetic = phonetic or word_info.get("phonetic", "")
                translation = translation or word_info.get("translation", "")
        
        # Create vocabulary item
        vocab_item = VocabItem(
            user_id=user_id,
            word=word,
            definition=definition,
            phonetic=phonetic,
            translation=translation,
            source=vocab_request.source,
            level=vocab_request.level,
            familiarity=0.0,
            encounter_count=1,
            correct_count=0,
            mastery_score=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
            is_mastered=False
        )
        
        db.add(vocab_item)
        db.commit()
        db.refresh(vocab_item)
        
        return VocabItemResponse(
            id=vocab_item.id,
            word=vocab_item.word,
            definition=vocab_item.definition or "",
            phonetic=vocab_item.phonetic or "",
            translation=vocab_item.translation or "",
            source=vocab_item.source or "",
            level=vocab_item.level or "",
            familiarity=vocab_item.familiarity,
            encounter_count=vocab_item.encounter_count,
            correct_count=vocab_item.correct_count,
            last_reviewed=vocab_item.last_reviewed.isoformat() if vocab_item.last_reviewed else None,
            mastery_score=vocab_item.mastery_score,
            related_words=vocab_item.related_words or [],
            created_at=vocab_item.created_at.isoformat() if vocab_item.created_at else None,
            updated_at=vocab_item.updated_at.isoformat() if vocab_item.updated_at else None,
            is_active=vocab_item.is_active,
            is_mastered=vocab_item.is_mastered
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create vocabulary item failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create vocabulary item"
        )


@router.put("/{vocab_id}", response_model=VocabItemResponse)
async def update_vocabulary_item(
    vocab_id: int,
    vocab_update: VocabItemUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing vocabulary item
    """
    try:
        user_id = current_user["sub"]
        
        vocab_item = db.query(VocabItem).filter(
            VocabItem.id == vocab_id,
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).first()
        
        if not vocab_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vocabulary item not found"
            )
        
        # Update fields if provided
        if vocab_update.definition is not None:
            vocab_item.definition = vocab_update.definition
        if vocab_update.phonetic is not None:
            vocab_item.phonetic = vocab_update.phonetic
        if vocab_update.translation is not None:
            vocab_item.translation = vocab_update.translation
        if vocab_update.source is not None:
            vocab_item.source = vocab_update.source
        if vocab_update.level is not None:
            vocab_item.level = vocab_update.level
        if vocab_update.familiarity is not None:
            vocab_item.familiarity = vocab_update.familiarity
        if vocab_update.mastery_score is not None:
            vocab_item.mastery_score = vocab_update.mastery_score
        if vocab_update.is_mastered is not None:
            vocab_item.is_mastered = vocab_update.is_mastered
        
        vocab_item.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(vocab_item)
        
        return VocabItemResponse(
            id=vocab_item.id,
            word=vocab_item.word,
            definition=vocab_item.definition or "",
            phonetic=vocab_item.phonetic or "",
            translation=vocab_item.translation or "",
            source=vocab_item.source or "",
            level=vocab_item.level or "",
            familiarity=vocab_item.familiarity,
            encounter_count=vocab_item.encounter_count,
            correct_count=vocab_item.correct_count,
            last_reviewed=vocab_item.last_reviewed.isoformat() if vocab_item.last_reviewed else None,
            mastery_score=vocab_item.mastery_score,
            related_words=vocab_item.related_words or [],
            created_at=vocab_item.created_at.isoformat() if vocab_item.created_at else None,
            updated_at=vocab_item.updated_at.isoformat() if vocab_item.updated_at else None,
            is_active=vocab_item.is_active,
            is_mastered=vocab_item.is_mastered
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update vocabulary item failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update vocabulary item"
        )


@router.delete("/{vocab_id}")
async def delete_vocabulary_item(
    vocab_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a vocabulary item (soft delete)
    """
    try:
        user_id = current_user["sub"]
        
        vocab_item = db.query(VocabItem).filter(
            VocabItem.id == vocab_id,
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).first()
        
        if not vocab_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vocabulary item not found"
            )
        
        # Soft delete
        vocab_item.is_active = False
        vocab_item.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "Vocabulary item deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete vocabulary item failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete vocabulary item"
        )


@router.post("/bulk", response_model=List[VocabItemResponse])
async def bulk_create_vocabulary(
    bulk_request: VocabBulkCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create multiple vocabulary items at once
    """
    try:
        user_id = current_user["sub"]
        
        if not bulk_request.words:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No words provided"
            )
        
        if len(bulk_request.words) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 50 words allowed per bulk request"
            )
        
        created_items = []
        skipped_words = []
        
        for word in bulk_request.words:
            word = word.strip().lower()
            if not word:
                continue
            
            # Check if word already exists
            existing = db.query(VocabItem).filter(
                VocabItem.user_id == user_id,
                VocabItem.word == word,
                VocabItem.is_active == True
            ).first()
            
            if existing:
                skipped_words.append(word)
                continue
            
            # Auto-lookup word details if requested
            definition = ""
            phonetic = ""
            translation = ""
            
            if bulk_request.auto_lookup:
                word_info = dictionary_service.query_word(word)
                if word_info:
                    definition = word_info.get("definition", "")
                    phonetic = word_info.get("phonetic", "")
                    translation = word_info.get("translation", "")
            
            # Create vocabulary item
            vocab_item = VocabItem(
                user_id=user_id,
                word=word,
                definition=definition,
                phonetic=phonetic,
                translation=translation,
                source=bulk_request.source,
                level=bulk_request.level,
                familiarity=0.0,
                encounter_count=1,
                correct_count=0,
                mastery_score=0.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_active=True,
                is_mastered=False
            )
            
            db.add(vocab_item)
            created_items.append(vocab_item)
        
        db.commit()
        
        # Refresh and format response
        results = []
        for item in created_items:
            db.refresh(item)
            results.append(VocabItemResponse(
                id=item.id,
                word=item.word,
                definition=item.definition or "",
                phonetic=item.phonetic or "",
                translation=item.translation or "",
                source=item.source or "",
                level=item.level or "",
                familiarity=item.familiarity,
                encounter_count=item.encounter_count,
                correct_count=item.correct_count,
                last_reviewed=item.last_reviewed.isoformat() if item.last_reviewed else None,
                mastery_score=item.mastery_score,
                related_words=item.related_words or [],
                created_at=item.created_at.isoformat() if item.created_at else None,
                updated_at=item.updated_at.isoformat() if item.updated_at else None,
                is_active=item.is_active,
                is_mastered=item.is_mastered
            ))
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk create vocabulary failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk create vocabulary items"
        )


@router.get("/stats")
async def get_vocabulary_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get vocabulary learning statistics
    """
    try:
        user_id = current_user["sub"]
        
        # Total vocabulary count
        total_count = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).count()
        
        # Mastered count
        mastered_count = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True,
            VocabItem.is_mastered == True
        ).count()
        
        # Count by level
        level_counts = {}
        levels = db.query(VocabItem.level).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True,
            VocabItem.level.isnot(None)
        ).distinct().all()
        
        for (level,) in levels:
            count = db.query(VocabItem).filter(
                VocabItem.user_id == user_id,
                VocabItem.is_active == True,
                VocabItem.level == level
            ).count()
            level_counts[level] = count
        
        # Average mastery score
        avg_mastery = db.query(db.func.avg(VocabItem.mastery_score)).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).scalar() or 0.0
        
        return {
            "total_words": total_count,
            "mastered_words": mastered_count,
            "learning_words": total_count - mastered_count,
            "mastery_percentage": (mastered_count / total_count * 100) if total_count > 0 else 0,
            "average_mastery_score": round(avg_mastery, 2),
            "level_distribution": level_counts
        }
        
    except Exception as e:
        logger.error(f"Get vocabulary stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get vocabulary statistics"
        )