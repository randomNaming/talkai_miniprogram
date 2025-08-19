"""
Data synchronization API endpoints
"""
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.vocab import VocabItem
from app.models.user import User

router = APIRouter()


class VocabSyncItem(BaseModel):
    """Vocabulary item for sync"""
    word: str
    definition: str = ""
    phonetic: str = ""
    translation: str = ""
    source: str = ""
    level: str = ""
    familiarity: float = 0.0
    encounter_count: int = 1
    correct_count: int = 0
    mastery_score: float = 0.0
    is_mastered: bool = False
    last_reviewed: str = None
    updated_at: str


class VocabSyncRequest(BaseModel):
    """Vocabulary sync request"""
    vocabulary: List[VocabSyncItem]
    last_sync_time: str = None


class VocabSyncResponse(BaseModel):
    """Vocabulary sync response"""
    vocabulary: List[VocabSyncItem]
    last_sync_time: str
    server_time: str
    conflicts_resolved: int = 0


@router.post("/vocab", response_model=VocabSyncResponse)
async def sync_vocabulary(
    sync_request: VocabSyncRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Synchronize vocabulary between client and server
    
    This endpoint handles bi-directional sync:
    1. Updates server with client changes
    2. Returns server changes to client
    3. Resolves conflicts (server wins for now)
    """
    try:
        user_id = current_user["sub"]
        current_time = datetime.utcnow()
        
        # Parse last sync time
        last_sync_dt = None
        if sync_request.last_sync_time:
            try:
                last_sync_dt = datetime.fromisoformat(sync_request.last_sync_time.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid last_sync_time format: {sync_request.last_sync_time}")
        
        conflicts_resolved = 0
        
        # Process client vocabulary updates
        for client_item in sync_request.vocabulary:
            try:
                # Find existing vocabulary item
                existing = db.query(VocabItem).filter(
                    VocabItem.user_id == user_id,
                    VocabItem.word == client_item.word.lower(),
                    VocabItem.is_active == True
                ).first()
                
                client_updated_at = datetime.fromisoformat(client_item.updated_at.replace('Z', '+00:00'))
                
                if existing:
                    # Check for conflict (server was updated after client's last sync)
                    if last_sync_dt and existing.updated_at > last_sync_dt:
                        # Conflict detected - server wins
                        conflicts_resolved += 1
                        logger.info(f"Conflict resolved for word '{client_item.word}' - server version kept")
                        continue
                    
                    # Update existing item with client data
                    existing.definition = client_item.definition
                    existing.phonetic = client_item.phonetic
                    existing.translation = client_item.translation
                    existing.source = client_item.source
                    existing.level = client_item.level
                    existing.familiarity = client_item.familiarity
                    existing.encounter_count = client_item.encounter_count
                    existing.correct_count = client_item.correct_count
                    existing.mastery_score = client_item.mastery_score
                    existing.is_mastered = client_item.is_mastered
                    
                    if client_item.last_reviewed:
                        existing.last_reviewed = datetime.fromisoformat(client_item.last_reviewed.replace('Z', '+00:00'))
                    
                    existing.updated_at = client_updated_at
                    
                else:
                    # Create new vocabulary item
                    new_item = VocabItem(
                        user_id=user_id,
                        word=client_item.word.lower(),
                        definition=client_item.definition,
                        phonetic=client_item.phonetic,
                        translation=client_item.translation,
                        source=client_item.source,
                        level=client_item.level,
                        familiarity=client_item.familiarity,
                        encounter_count=client_item.encounter_count,
                        correct_count=client_item.correct_count,
                        mastery_score=client_item.mastery_score,
                        is_mastered=client_item.is_mastered,
                        last_reviewed=datetime.fromisoformat(client_item.last_reviewed.replace('Z', '+00:00')) if client_item.last_reviewed else None,
                        created_at=client_updated_at,
                        updated_at=client_updated_at,
                        is_active=True
                    )
                    db.add(new_item)
                    
            except Exception as e:
                logger.error(f"Error processing vocab item '{client_item.word}': {e}")
                continue
        
        # Get all server vocabulary items updated after last sync
        query = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        )
        
        if last_sync_dt:
            query = query.filter(VocabItem.updated_at > last_sync_dt)
        
        server_items = query.order_by(VocabItem.updated_at.desc()).all()
        
        # Format server vocabulary for response
        vocabulary_response = []
        for item in server_items:
            vocabulary_response.append(VocabSyncItem(
                word=item.word,
                definition=item.definition or "",
                phonetic=item.phonetic or "",
                translation=item.translation or "",
                source=item.source or "",
                level=item.level or "",
                familiarity=item.familiarity,
                encounter_count=item.encounter_count,
                correct_count=item.correct_count,
                mastery_score=item.mastery_score,
                is_mastered=item.is_mastered,
                last_reviewed=item.last_reviewed.isoformat() if item.last_reviewed else None,
                updated_at=item.updated_at.isoformat()
            ))
        
        # Update user's last sync time
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login_at = current_time
        
        db.commit()
        
        return VocabSyncResponse(
            vocabulary=vocabulary_response,
            last_sync_time=sync_request.last_sync_time or "",
            server_time=current_time.isoformat(),
            conflicts_resolved=conflicts_resolved
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vocabulary sync failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vocabulary synchronization failed"
        )


@router.get("/status")
async def get_sync_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get synchronization status for the user
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
        vocab_count = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).count()
        
        # Get last vocabulary update time
        last_vocab_update = db.query(VocabItem.updated_at).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).order_by(VocabItem.updated_at.desc()).first()
        
        return {
            "user_id": user_id,
            "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
            "vocab_sync_interval_hours": user.vocab_sync_interval or 24,
            "server_vocab_count": vocab_count,
            "last_vocab_update": last_vocab_update[0].isoformat() if last_vocab_update else None,
            "server_time": datetime.utcnow().isoformat(),
            "sync_recommended": True  # Could implement logic to determine if sync is needed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get sync status failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sync status"
        )


@router.post("/force-download")
async def force_download_all_data(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Force download all user data from server
    
    This endpoint returns all user vocabulary data, regardless of sync timestamps.
    Useful for data recovery or initial setup on new devices.
    """
    try:
        user_id = current_user["sub"]
        
        # Get all active vocabulary items
        vocab_items = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).order_by(VocabItem.created_at.desc()).all()
        
        vocabulary_data = []
        for item in vocab_items:
            vocabulary_data.append(VocabSyncItem(
                word=item.word,
                definition=item.definition or "",
                phonetic=item.phonetic or "",
                translation=item.translation or "",
                source=item.source or "",
                level=item.level or "",
                familiarity=item.familiarity,
                encounter_count=item.encounter_count,
                correct_count=item.correct_count,
                mastery_score=item.mastery_score,
                is_mastered=item.is_mastered,
                last_reviewed=item.last_reviewed.isoformat() if item.last_reviewed else None,
                updated_at=item.updated_at.isoformat()
            ))
        
        return {
            "vocabulary": vocabulary_data,
            "total_items": len(vocabulary_data),
            "download_time": datetime.utcnow().isoformat(),
            "message": f"Downloaded {len(vocabulary_data)} vocabulary items"
        }
        
    except Exception as e:
        logger.error(f"Force download failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download data"
        )