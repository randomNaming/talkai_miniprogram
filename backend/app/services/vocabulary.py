"""
Vocabulary management service with semantic similarity recommendations
Ported from talkai_py/vocab_manager.py and language_model.py
"""
import numpy as np
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.models.vocab import VocabItem
from app.models.user import User
from app.utils.text_utils import (
    embedding_model, has_chinese, original, 
    extract_words_from_text, find_word_variants_in_text
)


class VocabularyService:
    """Enhanced vocabulary service with semantic similarity and mastery tracking"""
    
    def __init__(self):
        self.embedding_cache = {}  # Cache for word embeddings
        self.mastery_threshold = 3  # right_use - wrong_use >= 3 for mastery
    
    async def suggest_vocabulary_semantic(
        self, 
        user_id: str, 
        user_input: str, 
        ai_response: str,
        db: Session,
        limit: int = 5
    ) -> List[str]:
        """
        Generate vocabulary suggestions based on semantic similarity to conversation context.
        This implements the core algorithm from talkai_py.
        
        Args:
            user_id: User ID
            user_input: User's input message
            ai_response: AI's response message  
            db: Database session
            limit: Number of suggestions to return
            
        Returns:
            List of suggested vocabulary words
        """
        try:
            if not embedding_model:
                logger.warning("Embedding model not available, falling back to basic suggestions")
                return await self._fallback_vocabulary_suggestions(user_id, db, limit)
            
            # 1. Combine last conversation turn text (same as Python version)
            last_turn_text = " ".join([user_input, ai_response])
            logger.info(f"Generating suggestions for conversation: {last_turn_text[:100]}...")
            
            # 2. Get user's unmastered vocabulary from database
            unmastered_vocab = await self._get_unmastered_vocabulary(user_id, db)
            
            if not unmastered_vocab:
                logger.info(f"No unmastered vocabulary found for user {user_id}")
                return []
            
            # 3. Generate embedding for conversation context
            history_embedding = embedding_model.encode(last_turn_text)
            
            # 4. Get or compute embeddings for unmastered words
            word_embeddings = []
            words = []
            
            for vocab_item in unmastered_vocab:
                word = vocab_item.word
                
                # Get or compute embedding for this word
                if word not in self.embedding_cache:
                    try:
                        word_embedding = embedding_model.encode(word)
                        self.embedding_cache[word] = word_embedding
                    except Exception as e:
                        logger.warning(f"Failed to encode word '{word}': {e}")
                        continue
                
                word_embeddings.append(self.embedding_cache[word])
                words.append(word)
            
            if not word_embeddings:
                return []
            
            # 5. Compute cosine similarities (same algorithm as Python version)
            word_embeddings = np.array(word_embeddings)
            similarities = np.dot(word_embeddings, history_embedding) / (
                np.linalg.norm(word_embeddings, axis=1) * np.linalg.norm(history_embedding)
            )
            
            # 6. Create word-similarity pairs and sort by similarity
            word_sim_pairs = [(words[i], float(similarities[i])) for i in range(len(words))]
            word_sim_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # 7. Return top N suggestions
            top_suggestions = [word for word, sim in word_sim_pairs[:limit]]
            
            logger.info(f"Generated {len(top_suggestions)} semantic vocabulary suggestions for user {user_id}")
            return top_suggestions
            
        except Exception as e:
            logger.error(f"Error in semantic vocabulary suggestion: {e}")
            return await self._fallback_vocabulary_suggestions(user_id, db, limit)
    
    async def _get_unmastered_vocabulary(self, user_id: str, db: Session) -> List[VocabItem]:
        """
        Get vocabulary items that are not yet mastered by the user.
        Implements the mastery logic: right_use_count - wrong_use_count < 3
        """
        try:
            # Query vocabulary items where mastery_level < mastery_threshold
            # This maps to the Python version's isMastered = False logic
            unmastered_items = (
                db.query(VocabItem)
                .filter(
                    VocabItem.user_id == user_id,
                    VocabItem.is_mastered == False
                )
                .all()
            )
            
            logger.info(f"Found {len(unmastered_items)} unmastered vocabulary items for user {user_id}")
            return unmastered_items
            
        except Exception as e:
            logger.error(f"Error fetching unmastered vocabulary: {e}")
            return []
    
    async def _fallback_vocabulary_suggestions(
        self, 
        user_id: str, 
        db: Session, 
        limit: int
    ) -> List[str]:
        """Fallback vocabulary suggestions when semantic similarity is not available"""
        try:
            # Get recently added or least reviewed vocabulary
            vocab_items = (
                db.query(VocabItem)
                .filter(VocabItem.user_id == user_id)
                .filter(VocabItem.is_mastered == False)
                .order_by(VocabItem.last_reviewed.asc())
                .limit(limit)
                .all()
            )
            
            return [item.word for item in vocab_items]
            
        except Exception as e:
            logger.error(f"Error in fallback vocabulary suggestions: {e}")
            return []
    
    async def update_vocabulary_usage(
        self,
        user_id: str,
        word: str,
        usage_type: str,  # "right_use", "wrong_use", "lookup", "user_input"
        db: Session,
        source_context: str = ""
    ) -> bool:
        """
        Update vocabulary usage statistics and mastery level.
        Implements the core logic from talkai_py vocab_manager.
        
        Args:
            user_id: User ID
            word: The word being updated
            usage_type: Type of usage (right_use, wrong_use, lookup, user_input)
            db: Database session
            source_context: Context where the word was used
            
        Returns:
            Success status
        """
        try:
            # Skip Chinese words
            if has_chinese(word):
                return False
            
            # Normalize word to its original form
            normalized_word = original(word)
            
            # Find existing vocabulary entry or create new one
            vocab_item = (
                db.query(VocabItem)
                .filter(
                    VocabItem.user_id == user_id,
                    VocabItem.word == normalized_word
                )
                .first()
            )
            
            if not vocab_item:
                # Create new vocabulary entry
                vocab_item = VocabItem(
                    user_id=user_id,
                    word=normalized_word,
                    correct_count=0,
                    encounter_count=0,
                    mastery_score=0.0,
                    created_at=datetime.utcnow(),
                    last_reviewed=datetime.utcnow(),
                    is_active=True,
                    is_mastered=False
                )
                db.add(vocab_item)
            
            # Update usage counts based on type (same logic as Python version)
            if usage_type == "right_use":
                vocab_item.correct_count = (vocab_item.correct_count or 0) + 1
            elif usage_type in ["wrong_use", "lookup", "user_input"]:
                vocab_item.encounter_count = (vocab_item.encounter_count or 0) + 1
            
            # Update last reviewed time
            vocab_item.last_reviewed = datetime.utcnow()
            
            # Calculate mastery level (implements Python version's logic)
            right_count = vocab_item.correct_count or 0
            wrong_count = (vocab_item.encounter_count or 0) - right_count
            mastery_score = right_count - wrong_count
            vocab_item.mastery_score = max(0.0, min(1.0, mastery_score / 3.0))
            
            # Update example sentence if provided
            if source_context and len(source_context.strip()) > 0:
                vocab_item.example_sentence = source_context[:500]  # Limit length
            
            # Check if mastered (Python version logic: right_use - wrong_use >= 3)
            is_mastered = mastery_score >= self.mastery_threshold
            vocab_item.is_mastered = is_mastered
            
            # Invalidate embedding cache for this word to force re-computation
            if normalized_word in self.embedding_cache:
                del self.embedding_cache[normalized_word]
            
            db.commit()
            
            logger.info(
                f"Updated vocabulary '{normalized_word}' for user {user_id}: "
                f"correct={right_count}, "
                f"wrong={wrong_count}, "
                f"mastery_score={vocab_item.mastery_score}, "
                f"mastered={is_mastered}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating vocabulary usage: {e}")
            db.rollback()
            return False
    
    async def update_vocabulary_from_correction(
        self,
        user_id: str,
        correction_result: Dict[str, Any],
        user_input: str,
        db: Session
    ) -> bool:
        """
        Update vocabulary based on grammar correction results.
        Implements the logic from talkai_py language_model.update_vocab_oneturn_async
        """
        try:
            is_valid = correction_result.get("is_valid", False)
            
            # Only update if correction is valid
            if not is_valid:
                logger.info("Correction not valid, skipping vocabulary update")
                return False
            
            corrected_input = correction_result.get("corrected_input")
            words_deserve_to_learn = correction_result.get("words_deserve_to_learn", [])
            
            # Process words that need learning (wrong usage)
            if words_deserve_to_learn:
                for word_pair in words_deserve_to_learn:
                    original_word = word_pair.get("original", "")
                    corrected_word = word_pair.get("corrected", "")
                    error_type = word_pair.get("error_type", "vocabulary")
                    
                    if original_word and corrected_word and (original_word != corrected_word):
                        # Only save valuable vocabulary types (filter out grammar/collocation)
                        if error_type in ["translation", "vocabulary"]:
                            # Filter: no Chinese, single word, meaningful length, not too simple
                            if (not has_chinese(corrected_word) and 
                                len(corrected_word.split()) == 1 and 
                                len(corrected_word) > 2):
                                
                                await self.update_vocabulary_usage(
                                    user_id, corrected_word, "wrong_use", db, user_input
                                )
            
            # Process correctly used words
            correct_used_words = set()
            
            if corrected_input:
                # Has corrected input - find common words between original and corrected
                original_words = extract_words_from_text(user_input)
                corrected_words = extract_words_from_text(corrected_input)
                correct_used_words = original_words.intersection(corrected_words)
            else:
                # Input is completely correct
                if not words_deserve_to_learn and not has_chinese(user_input):
                    correct_used_words = extract_words_from_text(user_input)
            
            # Update correctly used words
            for word in correct_used_words:
                if len(word) > 2:  # Skip very short words
                    await self.update_vocabulary_usage(
                        user_id, word, "right_use", db, user_input
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating vocabulary from correction: {e}")
            return False
    
    async def load_level_vocabulary(
        self,
        user_id: str,
        grade: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Load vocabulary for a specific learning level.
        Implements functionality from talkai_py/vocab_loader.py
        """
        try:
            # Grade to vocabulary level mapping
            grade_vocab_map = {
                "Primary School": "primary",
                "Middle School": "middle", 
                "High School": "high",
                "CET4": "cet4",
                "CET6": "cet6",
                "TOEFL": "toefl",
                "IELTS": "ielts",
                "GRE": "gre"
            }
            
            vocab_level = grade_vocab_map.get(grade)
            if not vocab_level:
                logger.warning(f"Unsupported grade level: {grade}")
                return {"success": False, "message": f"Unsupported grade level: {grade}"}
            
            # Check if user already has vocabulary for this level
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "message": "User not found"}
            
            # For now, we'll implement a basic level vocabulary loading
            # In a full implementation, this would load from vocabulary files
            basic_vocab_by_level = {
                "primary": ["apple", "book", "cat", "dog", "eat", "friend", "good", "happy"],
                "middle": ["adventure", "beautiful", "challenge", "difficult", "education", "knowledge"],
                "high": ["achievement", "analyze", "communicate", "creativity", "development", "environment"],
                "cet4": ["accommodate", "appreciate", "circumstances", "concentrate", "demonstrate"],
                "cet6": ["acknowledge", "comprehensive", "controversial", "deteriorate", "elaborate"],
                "toefl": ["adolescence", "controversy", "deterioration", "encompasses", "substantially"],
                "ielts": ["predominantly", "sophisticated", "unprecedented", "comprehensive", "establishment"],
                "gre": ["abstruse", "conundrum", "ephemeral", "ubiquitous", "zenith"]
            }
            
            words_to_add = basic_vocab_by_level.get(vocab_level, [])
            added_count = 0
            
            for word in words_to_add:
                # Check if word already exists for this user
                existing = (
                    db.query(Vocabulary)
                    .filter(
                        Vocabulary.user_id == user_id,
                        Vocabulary.word == word
                    )
                    .first()
                )
                
                if not existing:
                    # Add new vocabulary item
                    vocab_item = Vocabulary(
                        user_id=user_id,
                        word=word,
                        definition=f"Level vocabulary: {grade}",
                        correct_usage_count=0,
                        incorrect_usage_count=0,
                        mastery_level=0,
                        created_at=datetime.utcnow(),
                        last_reviewed_at=datetime.utcnow()
                    )
                    db.add(vocab_item)
                    added_count += 1
            
            db.commit()
            
            logger.info(f"Added {added_count} vocabulary words for user {user_id} at level {grade}")
            return {
                "success": True, 
                "message": f"Added {added_count} vocabulary words for {grade} level",
                "added_count": added_count
            }
            
        except Exception as e:
            logger.error(f"Error loading level vocabulary: {e}")
            db.rollback()
            return {"success": False, "message": f"Error loading vocabulary: {str(e)}"}
    
    async def get_vocabulary_stats(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Get vocabulary learning statistics for the user"""
        try:
            # Total vocabulary count
            total_vocab = (
                db.query(func.count(VocabItem.id))
                .filter(VocabItem.user_id == user_id)
                .scalar()
            )
            
            # Mastered vocabulary count
            mastered_vocab = (
                db.query(func.count(VocabItem.id))
                .filter(
                    VocabItem.user_id == user_id,
                    VocabItem.is_mastered == True
                )
                .scalar()
            )
            
            # Learning vocabulary count (not mastered)
            learning_vocab = total_vocab - mastered_vocab
            
            # Recent additions (last 7 days)
            from datetime import timedelta
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_additions = (
                db.query(func.count(VocabItem.id))
                .filter(
                    VocabItem.user_id == user_id,
                    VocabItem.created_at >= recent_cutoff
                )
                .scalar()
            )
            
            return {
                "total_vocabulary": total_vocab or 0,
                "mastered_vocabulary": mastered_vocab or 0,
                "learning_vocabulary": learning_vocab or 0,
                "recent_additions": recent_additions or 0,
                "mastery_rate": round((mastered_vocab / total_vocab * 100) if total_vocab > 0 else 0, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting vocabulary stats: {e}")
            return {
                "total_vocabulary": 0,
                "mastered_vocabulary": 0, 
                "learning_vocabulary": 0,
                "recent_additions": 0,
                "mastery_rate": 0.0
            }


# Global vocabulary service instance
vocabulary_service = VocabularyService()