"""
Vocabulary management API endpoints
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.vocab import VocabItem
from app.services.dictionary import dictionary_service
from app.services.vocabulary import vocabulary_service

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
            .order_by(VocabItem.last_used.desc())
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
        
        vocab_item.last_used = datetime.utcnow()
        
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
        vocab_item.last_used = datetime.utcnow()
        
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
        avg_mastery = db.query(func.avg(VocabItem.mastery_score)).filter(
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


@router.post("/load-level")
async def load_vocabulary_by_level(
    level_request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Load vocabulary words based on user's learning level
    
    This mimics the talkai_py vocab_loader functionality that automatically
    loads appropriate vocabulary based on the user's grade/level.
    """
    try:
        user_id = current_user["sub"]
        level = level_request.get("level", "").strip()
        
        if not level:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Level is required"
            )
        
        # Get user to check if level already loaded
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if vocabulary for this level has already been loaded
        added_vocab_levels = user.added_vocab_levels or []
        if level in added_vocab_levels:
            return {
                "message": f"Vocabulary for {level} level has already been loaded",
                "level": level,
                "already_loaded": True,
                "words_added": 0
            }
        
        # Define level to word mappings (simulated from talkai_py)
        level_words = {
            "Primary School": [
                "apple", "book", "cat", "dog", "eat", "fish", "good", "house", 
                "like", "water", "school", "friend", "family", "happy", "play"
            ],
            "Middle School": [
                "achieve", "adventure", "beautiful", "computer", "different", "education",
                "environment", "friendship", "important", "knowledge", "library", "music",
                "nature", "opportunity", "question", "science", "technology", "understand"
            ],
            "High School": [
                "accomplish", "analyze", "comprehensive", "demonstrate", "efficient",
                "fundamental", "generation", "hypothesis", "implement", "justify",
                "knowledge", "literature", "mathematics", "necessary", "organization"
            ],
            "CET4": [
                "abandon", "accurate", "adequate", "alternative", "assumption", "attribute",
                "benefit", "category", "concept", "considerable", "consistent", "contribute",
                "definitely", "efficient", "equivalent", "evaluation", "fundamental", "hypothesis"
            ],
            "CET6": [
                "abundant", "accommodate", "acknowledge", "aesthetic", "apparatus", "articulate",
                "autonomous", "coherent", "compatible", "contemplate", "controversy", "criterion",
                "demonstrate", "elaborate", "explicit", "hierarchy", "inevitable", "preliminary"
            ],
            "TOEFL": [
                "comprehensive", "demonstrate", "distribute", "establish", "evidence", "factor",
                "identify", "interpret", "method", "obtain", "occur", "percent", "period",
                "policy", "principle", "procedure", "process", "require", "research", "structure"
            ],
            "IELTS": [
                "analyze", "approach", "area", "assessment", "concept", "consistent", "constitute",
                "context", "contract", "create", "data", "derive", "distribution", "economic",
                "environment", "estimate", "function", "indicate", "interpret", "source"
            ],
            "GRE": [
                "aberration", "abscond", "abstemious", "admonish", "aesthetic", "altruistic",
                "amalgamate", "ambiguous", "anomaly", "antipathy", "apathy", "appease",
                "arbitrary", "arduous", "articulate", "ascetic", "audacious", "austere"
            ]
        }
        
        words_to_add = level_words.get(level, [])
        if not words_to_add:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported level: {level}"
            )
        
        # Add words to user's vocabulary
        added_count = 0
        updated_count = 0
        
        for word in words_to_add:
            # Check if word already exists
            existing = db.query(VocabItem).filter(
                VocabItem.user_id == user_id,
                VocabItem.word == word.lower(),
                VocabItem.is_active == True
            ).first()
            
            if existing:
                # Update existing word with level information
                existing.level = level
                existing.source = "level_vocab"
                existing.last_used = datetime.utcnow()
                updated_count += 1
            else:
                # Auto-lookup word details
                word_info = dictionary_service.query_word(word.lower())
                definition = ""
                phonetic = ""
                translation = ""
                
                if word_info:
                    definition = word_info.get("definition", "")
                    phonetic = word_info.get("phonetic", "")
                    translation = word_info.get("translation", "")
                
                # Create new vocabulary item
                vocab_item = VocabItem(
                    user_id=user_id,
                    word=word.lower(),
                    definition=definition,
                    phonetic=phonetic,
                    translation=translation,
                    source="level_vocab",
                    level=level,
                    familiarity=0.0,
                    encounter_count=0,
                    correct_count=0,
                    mastery_score=0.0,
                    created_at=datetime.utcnow(),
                    
                    is_active=True,
                    is_mastered=False
                )
                
                db.add(vocab_item)
                added_count += 1
        
        # Update user's added_vocab_levels
        if level not in added_vocab_levels:
            added_vocab_levels.append(level)
            user.added_vocab_levels = added_vocab_levels
        
        db.commit()
        
        return {
            "message": f"Successfully loaded vocabulary for {level} level",
            "level": level,
            "words_added": added_count,
            "words_updated": updated_count,
            "total_words": len(words_to_add),
            "already_loaded": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Load vocabulary by level failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load vocabulary by level"
        )


@router.post("/update-usage")
async def update_word_usage(
    usage_request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update word usage statistics and check for mastery
    
    This mimics the talkai_py vocabulary manager's mastery detection
    where mastery is achieved when right_use_count - wrong_use_count >= 3
    """
    try:
        user_id = current_user["sub"]
        word = usage_request.get("word", "").strip().lower()
        usage_type = usage_request.get("usage_type", "").strip()  # "right_use" or "wrong_use"
        
        if not word or not usage_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Word and usage_type are required"
            )
        
        if usage_type not in ["right_use", "wrong_use"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="usage_type must be 'right_use' or 'wrong_use'"
            )
        
        # Find the vocabulary item
        vocab_item = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.word == word,
            VocabItem.is_active == True
        ).first()
        
        if not vocab_item:
            # If word doesn't exist, create it with initial usage
            word_info = dictionary_service.query_word(word)
            definition = ""
            phonetic = ""
            translation = ""
            
            if word_info:
                definition = word_info.get("definition", "")
                phonetic = word_info.get("phonetic", "")
                translation = word_info.get("translation", "")
            
            vocab_item = VocabItem(
                user_id=user_id,
                word=word,
                definition=definition,
                phonetic=phonetic,
                translation=translation,
                source="wrong_use" if usage_type == "wrong_use" else "right_use",
                level="",
                familiarity=0.0,
                encounter_count=1,
                correct_count=1 if usage_type == "right_use" else 0,
                mastery_score=0.0,
                created_at=datetime.utcnow(),
                
                is_active=True,
                is_mastered=False
            )
            
            db.add(vocab_item)
        else:
            # Update existing vocabulary item
            vocab_item.encounter_count = (vocab_item.encounter_count or 0) + 1
            
            if usage_type == "right_use":
                vocab_item.correct_count = (vocab_item.correct_count or 0) + 1
            
            vocab_item.last_used = datetime.utcnow()
        
        # Calculate wrong_use_count (encounter_count - correct_count)
        right_use_count = vocab_item.correct_count or 0
        wrong_use_count = (vocab_item.encounter_count or 0) - right_use_count
        
        # Check for mastery (talkai_py logic: right_use_count - wrong_use_count >= 3)
        mastery_threshold = right_use_count - wrong_use_count
        is_mastered = mastery_threshold >= 3
        
        if is_mastered and not vocab_item.is_mastered:
            vocab_item.is_mastered = True
            vocab_item.mastery_score = 1.0
        elif not is_mastered:
            vocab_item.is_mastered = False
            # Calculate mastery score as a percentage
            vocab_item.mastery_score = max(0.0, min(1.0, mastery_threshold / 3.0))
        
        db.commit()
        db.refresh(vocab_item)
        
        return {
            "word": vocab_item.word,
            "right_use_count": right_use_count,
            "wrong_use_count": wrong_use_count,
            "encounter_count": vocab_item.encounter_count,
            "mastery_score": vocab_item.mastery_score,
            "is_mastered": vocab_item.is_mastered,
            "mastery_threshold": mastery_threshold,
            "message": "Congratulations! You've mastered this word!" if (is_mastered and not vocab_item.is_mastered) else "Usage updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update word usage failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update word usage"
        )