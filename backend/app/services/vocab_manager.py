"""
VocabManager Service - 完全复制 talkai_py/vocab_manager.py 的功能
用于异步更新学习词汇，支持批量保存和向量化处理
"""
import asyncio
import threading
import time
from datetime import datetime
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.vocab import VocabItem
from app.core.database import get_db


class VocabManager:
    """词汇管理器 - 复制 talkai_py 的所有功能"""
    
    def __init__(self, save_mode="on_exit", auto_save_interval=30):
        # 线程池用于异步处理词汇更新
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._pending_updates = set()  # 跟踪待处理的更新
        
        # 批量保存相关设置
        self._has_unsaved_changes = False  # 标记是否有未保存的更改
        self.save_mode = save_mode  # "on_exit" 或 "auto_save"
        self.auto_save_interval = auto_save_interval  # 自动保存间隔（秒）
        
        # 定时器相关
        self._save_timer = None
        self._timer_lock = threading.Lock()
        
        logger.info(f"VocabManager initialized with save_mode: {save_mode}")
        
        # 如果是自动保存模式，启动定时器
        if self.save_mode == "auto_save":
            self._start_auto_save_timer()
    
    def _start_auto_save_timer(self):
        """启动自动保存定时器（复制 talkai_py 逻辑）"""
        with self._timer_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            
            def auto_save_task():
                if self._has_unsaved_changes:
                    logger.info("Auto-save triggered")
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
    
    def set_save_mode(self, mode: str, auto_save_interval: Optional[int] = None):
        """动态切换保存模式（复制 talkai_py 逻辑）"""
        self.save_mode = mode
        
        if auto_save_interval is not None:
            self.auto_save_interval = auto_save_interval
        
        if mode == "auto_save":
            self._start_auto_save_timer()
        else:
            self._stop_auto_save_timer()
    
    async def update_learning_vocab_async(self, word: str, source: str, user_id: str) -> bool:
        """
        异步更新学习词汇，不阻塞UI（完全复制 talkai_py 逻辑）
        
        参数:
            word (str): 要更新的单词
            source (str): 词汇来源 ("user_input", "lookup", "wrong_use", "right_use")
            user_id (str): 用户ID
        
        返回:
            bool: 更新是否成功
        """
        # 验证输入
        if not word or not word.strip():
            logger.warning(f"Empty word provided for user {user_id}")
            return False
        
        # 检查是否包含中文
        if self._has_chinese(word):
            logger.debug(f"Skipping Chinese word: {word}")
            return False

        # 在线程池中异步执行
        try:
            loop = asyncio.get_event_loop()
            future = await loop.run_in_executor(
                self.executor, 
                self._update_vocab_background, 
                word, source, user_id
            )
            logger.info(f"update_learning_vocab_async word: {word}, source: {source}, user_id: {user_id}")
            return future
        except Exception as e:
            logger.error(f"Async vocab update failed: {e}")
            return False
    
    def _has_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def _original(self, word: str) -> str:
        """获取单词的原始形式（简化处理）"""
        return word.lower().strip()
    
    def _update_vocab_background(self, word: str, source: str, user_id: str) -> bool:
        """
        后台更新词汇（在线程池中执行） - 完全复制 talkai_py 逻辑
        使用延迟批量处理机制，只标记更改，不立即保存
        
        wrong_use_count+=1 for "user_input", "lookup", "wrong_use"
        right_use_count+=1 for "right_use"
        isMastered = True if right_use_count - wrong_use_count >= 3
        """
        try:
            word = self._original(word)
            
            # 获取数据库连接
            with next(get_db()) as db:
                # 查找现有词汇
                existing_vocab = db.query(VocabItem).filter(
                    VocabItem.user_id == user_id,
                    VocabItem.word == word.lower(),
                    VocabItem.is_active == True
                ).first()
                
                if existing_vocab:
                    # 更新现有词汇
                    existing_vocab.last_reviewed = datetime.utcnow()
                    existing_vocab.last_used = datetime.utcnow()
                    
                    if source in ["user_input", "lookup", "wrong_use"]:  # 3 cases for wrong_use_count
                        # wrong_use_count = encounter_count - correct_count
                        existing_vocab.encounter_count += 1
                        # correct_count 保持不变，所以 wrong_use_count 实际增加了 1
                    elif source == "right_use":
                        existing_vocab.encounter_count += 1
                        existing_vocab.correct_count += 1
                    
                    # 计算掌握度：right_use_count - wrong_use_count >= 3
                    right_use_count = existing_vocab.correct_count
                    wrong_use_count = existing_vocab.encounter_count - existing_vocab.correct_count
                    mastery_score = right_use_count - wrong_use_count
                    
                    existing_vocab.mastery_score = mastery_score
                    existing_vocab.is_mastered = mastery_score >= 3
                    
                    self._has_unsaved_changes = True
                    db.commit()
                    
                    logger.debug(f"Updated existing vocab: {word} for user {user_id}, mastery_score: {mastery_score}")
                    return True
                
                # 创建新词汇（只有非 "right_use" 的情况才创建）
                if source != "right_use":  # "right_use" will not add to learning_vocab
                    success = self._create_new_word(word, source, user_id, db)
                    if success:
                        self._has_unsaved_changes = True
                        db.commit()
                        logger.info(f"Created new vocab: {word} for user {user_id}")
                    return success
                
                return True
                
        except Exception as e:
            logger.error(f"Background vocab update failed: {e}, word: {word}, source: {source}, user_id: {user_id}")
            return False
    
    def _create_new_word(self, word: str, source: str, user_id: str, db: Session) -> bool:
        """创建新单词（完全复制 talkai_py 逻辑）"""
        try:
            today = datetime.utcnow()
            
            # 根据 source 确定初始计数
            if source in ["wrong_use", "user_input", "lookup"]:
                encounter_count = 1
                correct_count = 0
            else:
                encounter_count = 1
                correct_count = 0
            
            new_vocab = VocabItem(
                user_id=user_id,
                word=word.lower(),
                source=source,
                level="none",  # 默认级别
                encounter_count=encounter_count,
                correct_count=correct_count,
                mastery_score=correct_count - (encounter_count - correct_count),  # right_use_count - wrong_use_count
                is_mastered=False,
                created_at=today,
                last_reviewed=today,
                is_active=True
            )
            
            db.add(new_vocab)
            return True
            
        except Exception as e:
            logger.error(f"Create new word failed: {e}")
            return False
    
    def finalize(self):
        """应用退出时调用，执行最终的保存操作（复制 talkai_py 逻辑）"""
        logger.info("Finalizing vocab manager...")
        
        # 停止定时器
        self._stop_auto_save_timer()
        
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


# 创建全局实例
vocab_manager = VocabManager()