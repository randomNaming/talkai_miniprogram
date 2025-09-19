"""
Vocabulary management service with semantic similarity recommendations
Ported from talkai_py/vocab_manager.py and language_model.py
"""
import numpy as np
import threading
import time
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.models.vocab import VocabItem
from app.models.user import User
# Import text utilities, use fallback if not available
try:
    from app.utils.text_utils import (
        embedding_model, has_chinese, original, 
        extract_words_from_text, find_word_variants_in_text
    )
except ImportError:
    # Fallback implementations
    import re
    embedding_model = None
    
    def has_chinese(text: str) -> bool:
        """检查文本是否包含中文字符"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def original(word: str) -> str:
        """处理单词，转换为小写并去除特殊字符"""
        return re.sub(r'[^\w]', '', word.lower())
    
    def extract_words_from_text(text: str) -> set:
        """从文本中提取单词"""
        return set(re.findall(r'\b\w+\b', text.lower()))


class VocabularyService:
    """Enhanced vocabulary service with semantic similarity and mastery tracking"""
    
    def __init__(self):
        self.embedding_cache = {}  # Cache for word embeddings
        self.mastery_threshold = 3  # right_use - wrong_use >= 3 for mastery
        
        # 内存缓存和批量更新机制 (复制 talkai_py 逻辑)
        self._memory_cache = {}  # 用户词汇更新的内存缓存 {user_id: {word: update_info}}
        self._has_unsaved_changes = {}  # 每个用户的未保存更改标记
        self._pending_updates = set()  # 跟踪待处理的更新
        
        # 自动保存机制
        self.auto_save_interval = 30  # 30秒自动保存
        self._save_timer = None
        self._timer_lock = threading.Lock()
        
        # 线程池用于异步处理
        from concurrent.futures import ThreadPoolExecutor
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # 启动自动保存定时器
        self._start_auto_save_timer()
    
    def _start_auto_save_timer(self):
        """启动自动保存定时器 (复制 talkai_py 逻辑)"""
        with self._timer_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            
            def auto_save_task():
                if self._has_unsaved_changes or self._memory_cache:
                    self._perform_batch_save()
                # 重新启动定时器
                self._start_auto_save_timer()
            
            self._save_timer = threading.Timer(self.auto_save_interval, auto_save_task)
            self._save_timer.daemon = True
            self._save_timer.start()
    
    def _stop_auto_save_timer(self):
        """停止自动保存定时器"""
        with self._timer_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None
    
    def _perform_batch_save(self):
        """执行批量保存操作 (复制 talkai_py 逻辑)"""
        try:
            if not self._memory_cache:
                return
            
            logger.info("执行批量词汇保存操作...")
            
            # 这里应该在实际应用中使用数据库会话
            # 由于这是异步操作且涉及数据库，在实际使用时需要传入db会话
            # 目前只是标记已保存
            
            # 清空内存缓存
            saved_users = []
            for user_id in list(self._memory_cache.keys()):
                if self._memory_cache[user_id]:
                    saved_users.append(user_id)
                    self._memory_cache[user_id] = {}
                    self._has_unsaved_changes[user_id] = False
            
            if saved_users:
                logger.info(f"批量保存完成，涉及用户: {saved_users}")
            
        except Exception as e:
            logger.error(f"批量保存失败: {e}")
    
    def finalize(self):
        """应用退出时调用，执行最终的保存操作 (复制 talkai_py 逻辑)"""
        logger.info("正在完成词汇管理服务...")
        
        # 停止定时器
        self._stop_auto_save_timer()
        
        # 执行最终保存
        if self._has_unsaved_changes or self._memory_cache:
            self._perform_batch_save()
        
        # 关闭线程池
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
    
    def __del__(self):
        """析构函数，确保线程池正确关闭"""
        try:
            self.finalize()
        except:
            # 在析构函数中静默失败，避免异常
            pass
    
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
                    wrong_use_count=0,
                    right_use_count=0,
                    mastery_score=0.0,
                    added_date=datetime.utcnow(),
                    last_used=datetime.utcnow(),
                    is_active=True,
                    isMastered=False
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
            import re
            from app.utils.prompts import simple_words
            
            is_valid = correction_result.get("is_valid", False)
            
            # 如果 is_valid = False，不更新词汇
            if not is_valid:
                logger.info("Correction is not valid, skipping vocabulary update")
                return True
            
            corrected_input = correction_result.get("corrected_input")
            words_deserve_to_learn = correction_result.get("words_deserve_to_learn", [])
            
            # 处理值得学习的单词(wrong_use)
            if words_deserve_to_learn:
                for word_pair in words_deserve_to_learn:
                    original_word = word_pair.get("original", "")
                    corrected_word = word_pair.get("corrected", "")
                    error_type = word_pair.get("error_type", "vocabulary")
                    
                    if original_word and corrected_word and (original_word != corrected_word):
                        # 只保存有价值的词汇类型到learning_vocab.json，过滤error_type："grammar"， "collocation"
                        if error_type in ["translation", "vocabulary"]:
                            # 将错误使用的单词添加到未掌握词汇表: 过滤掉中文，过滤掉短语，过滤掉简单词
                            if (not has_chinese(corrected_word) and 
                                len(corrected_word.split()) == 1 and 
                                len(corrected_word) > 2 and 
                                corrected_word not in simple_words):
                                
                                await self._update_learning_vocab_async(
                                    user_id, corrected_word, "wrong_use", db
                                )
            
            # 处理正确使用的单词(right_use)
            correct_used_words = set()
            
            logger.info(f"开始处理正确使用的单词 - corrected_input: {corrected_input}, words_deserve_to_learn: {len(words_deserve_to_learn)}, user_input: {user_input}")
            
            if corrected_input:
                # 有修正输入，对比原始输入和修正后的输入，找出正确使用的单词
                original_words = set(re.findall(r'\b\w+\b', user_input.lower()))
                corrected_words = set(re.findall(r'\b\w+\b', corrected_input.lower()))
                
                # 找出两者共有的单词（可能是正确使用的单词）
                common_words = original_words.intersection(corrected_words)
                correct_used_words = common_words - simple_words
                logger.info(f"有修正输入场景 - original_words: {original_words}, corrected_words: {corrected_words}, correct_used_words: {correct_used_words}")
            else:
                # 输入完全正确（corrected_input为null），直接提取输入中的所有单词
                # 如果 没有值得学习的单词，且输入全英文，correct_used_words 为全部单词-simple_words
                if not words_deserve_to_learn and not has_chinese(user_input):
                    all_words = set(re.findall(r'\b\w+\b', user_input.lower())) 
                    correct_used_words = all_words - simple_words
                    logger.info(f"输入完全正确场景 - all_words: {all_words}, simple_words数量: {len(simple_words)}, correct_used_words: {correct_used_words}")
                # 如果输入有中文，或有值得学习的单词，则correct_used_words 为空 （保守策略）
                else:
                    correct_used_words = set()
                    logger.info(f"保守策略场景 - 有中文或有错误单词，correct_used_words为空")
            
            # 更新词汇使用情况
            if correct_used_words:
                logger.info(f"准备更新 {len(correct_used_words)} 个正确使用的单词: {correct_used_words}")
                for word in correct_used_words:
                    if len(word) > 2:  # 忽略过短的单词
                        logger.info(f"正在更新词汇 '{word}' 的 right_use_count")
                        await self._update_learning_vocab_async(
                            user_id, word, "right_use", db
                        )
                    else:
                        logger.info(f"跳过过短单词: '{word}'")
            else:
                logger.info("没有需要更新 right_use_count 的单词")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating vocabulary from correction: {e}")
            return False
    
    async def _update_learning_vocab_async(
        self,
        user_id: str,
        word: str,
        source: str,
        db: Session
    ) -> bool:
        """
        异步更新学习词汇
        复制 talkai_py 中的 _update_vocab_background 逻辑
        支持内存缓存和批量更新机制
        
        wrong_use_count+=1 for "user_input", "lookup", "wrong_use"
        right_use_count+=1 for "right_use"
        isMastered = True if right_use_count - wrong_use_count >= 3
        
        Args:
            user_id: 用户ID
            word: 要更新的单词
            source: 词汇来源 ("wrong_use", "right_use", "user_input", "lookup")
            db: 数据库会话
            
        Returns:
            更新是否成功
        """
        try:
            if has_chinese(word):
                return True
            
            word = original(word)
            
            # 先更新内存缓存 (可能先更新到内存，一段时间后再统一更新到文件)
            if user_id not in self._memory_cache:
                self._memory_cache[user_id] = {}
            
            if word not in self._memory_cache[user_id]:
                self._memory_cache[user_id][word] = {
                    'right_use_count': 0,
                    'wrong_use_count': 0,
                    'last_updated': datetime.utcnow(),
                    'source': source
                }
            
            # 更新内存缓存中的计数
            if source in ["user_input", "lookup", "wrong_use"]:
                self._memory_cache[user_id][word]['wrong_use_count'] += 1
            elif source == "right_use":
                self._memory_cache[user_id][word]['right_use_count'] += 1
            
            self._memory_cache[user_id][word]['last_updated'] = datetime.utcnow()
            
            # 标记有未保存的更改
            self._has_unsaved_changes[user_id] = True
            
            # 同时立即更新数据库（为了保证数据一致性）
            existing_vocab = db.query(VocabItem).filter(
                VocabItem.user_id == user_id,
                VocabItem.word == word,
                VocabItem.is_active == True
            ).first()
            
            if existing_vocab:
                # 更新现有词汇
                existing_vocab.last_used = datetime.utcnow()
                
                # 使用talkai_py兼容的字段名：wrong_use_count, right_use_count
                if source in ["user_input", "lookup", "wrong_use"]:  # 3 cases for wrong_use
                    existing_vocab.wrong_use_count = (existing_vocab.wrong_use_count or 0) + 1
                elif source == "right_use":
                    existing_vocab.right_use_count = (existing_vocab.right_use_count or 0) + 1
                
                # 计算掌握状态：right_use_count - wrong_use_count >= 3 (talkai_py logic)
                right_count = existing_vocab.right_use_count or 0
                wrong_count = existing_vocab.wrong_use_count or 0
                mastery_score = right_count - wrong_count
                existing_vocab.isMastered = mastery_score >= 3
                
                db.commit()
                
                logger.info(
                    f"更新词汇 {word} for user {user_id}: "
                    f"right={right_count}, wrong={wrong_count}, "
                    f"mastered={existing_vocab.isMastered}, source={source}"
                )
                
                return True
            else:
                # "right_use" will not add to learning_vocab.json
                if source != "right_use":
                    # 创建新词汇项 (talkai_py兼容格式)
                    new_vocab = VocabItem(
                        user_id=user_id,
                        word=word,
                        source=source,
                        level="none",  # 动态添加的词汇标记为 "none"
                        added_date=datetime.utcnow(),  # talkai_py: added_date
                        last_used=datetime.utcnow(),   # talkai_py: last_used
                        right_use_count=0,             # talkai_py: right_use_count
                        wrong_use_count=1 if source in ["user_input", "lookup", "wrong_use"] else 0,  # talkai_py: wrong_use_count
                        isMastered=False,              # talkai_py: isMastered
                        is_active=True
                    )
                    
                    db.add(new_vocab)
                    db.commit()
                    
                    logger.info(
                        f"创建新词汇 {word} for user {user_id}, source: {source}"
                    )
                else:
                    # right_use 但词汇不存在，按照设计不创建新词汇
                    logger.info(
                        f"单词 '{word}' 正确使用但不在用户词汇库中，跳过 (用户 {user_id})"
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"异步更新词汇失败: {e}, word: {word}, source: {source}")
            db.rollback()
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
    
    async def add_vocabulary_item(
        self,
        user_id: str,
        word: str,
        level: str = "none",
        source: str = "user_input",
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Add a new vocabulary item to the user's learning vocabulary.
        This method is called by the learning_vocab API endpoint.
        
        Args:
            user_id: User ID
            word: The word to add
            level: Learning level (default: "none")
            source: Source of the word (default: "user_input")
            db: Database session
            
        Returns:
            Dict with success status and details about the operation
        """
        try:
            # Skip Chinese words
            if has_chinese(word):
                logger.info(f"Skipping Chinese word: {word}")
                return {"success": False, "reason": "chinese_word", "message": "Skipping Chinese word"}
            
            # Normalize word to its original form
            normalized_word = original(word)
            
            # Check if word already exists for this user
            existing_vocab = (
                db.query(VocabItem)
                .filter(
                    VocabItem.user_id == user_id,
                    VocabItem.word == normalized_word,
                    VocabItem.is_active == True
                )
                .first()
            )
            
            if existing_vocab:
                # Word already exists, update last_used and usage count directly
                existing_vocab.last_used = datetime.utcnow()
                
                # Update usage counts based on source
                if source in ["user_input", "lookup", "wrong_use", "chat_correction"]:
                    existing_vocab.wrong_use_count = (existing_vocab.wrong_use_count or 0) + 1
                elif source == "right_use":
                    existing_vocab.right_use_count = (existing_vocab.right_use_count or 0) + 1
                
                # Calculate mastery status
                right_count = existing_vocab.right_use_count or 0
                wrong_count = existing_vocab.wrong_use_count or 0
                mastery_score = right_count - wrong_count
                existing_vocab.isMastered = mastery_score >= 3
                
                db.commit()
                logger.info(f"Word '{normalized_word}' already exists for user {user_id}, updated usage")
                return {
                    "success": True, 
                    "action": "updated", 
                    "word": normalized_word,
                    "original_source": existing_vocab.source,
                    "original_level": existing_vocab.level,
                    "is_level_vocab": existing_vocab.source == "level_vocab",
                    "message": f"Updated existing word '{normalized_word}'"
                }
            else:
                # Create new vocabulary item
                new_vocab = VocabItem(
                    user_id=user_id,
                    word=normalized_word,
                    source=source,
                    level=level,
                    added_date=datetime.utcnow(),
                    last_used=datetime.utcnow(),
                    right_use_count=0,
                    wrong_use_count=1 if source in ["user_input", "lookup", "wrong_use", "chat_correction"] else 0,
                    isMastered=False,
                    is_active=True,
                    mastery_score=0.0
                )
                
                db.add(new_vocab)
                db.commit()
                
                logger.info(f"Added new vocabulary word '{normalized_word}' for user {user_id}, source: {source}")
                return {
                    "success": True, 
                    "action": "created", 
                    "word": normalized_word,
                    "source": source,
                    "level": level,
                    "is_level_vocab": False,
                    "message": f"Added new word '{normalized_word}'"
                }
            
        except Exception as e:
            logger.error(f"Error adding vocabulary item: {e}")
            db.rollback()
            return {"success": False, "reason": "database_error", "message": f"Database error: {str(e)}"}

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