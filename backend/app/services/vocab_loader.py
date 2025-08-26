"""
VocabLoader Service - 根据用户 grade 自动加载对应等级词汇
完全复制 talkai_py/vocab_loader.py 的功能
"""
import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.vocab import VocabItem


class VocabLoader:
    """根据用户级别从txt文件加载词汇到学习词汇数据库"""
    
    def __init__(self):
        self.grade_to_txt_file = {
            "Primary School": "primary_school_all.txt",
            "Middle School": "middle_school_all.txt", 
            "High School": "high_school_all.txt",
            "CET4": "CET4_all.txt",
            "CET6": "CET6_all.txt",
            "TOEFL": "TOEFL_all.txt",
            "IELTS": "IELTS_all.txt",
            "GRE": "GRE_all.txt"
        }
        
        # 词汇文件路径
        self.level_words_dir = "data/level_words"
    
    def _read_txt_words(self, txt_file_path: str) -> List[str]:
        """从txt文件读取词汇列表（复制 talkai_py 逻辑）"""
        words = []
        try:
            with open(txt_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word and not word.startswith('#'):  # 忽略空行和注释
                        # 允许字母和连字符组成的词汇
                        if re.match(r'^[a-zA-Z-]+$', word):
                            words.append(word.lower())
        except Exception as e:
            logger.error(f"读取txt文件失败: {e}")
        return words
    
    def _load_current_vocab(self, user_id: str, db: Session) -> Dict:
        """加载当前用户的学习词汇，返回词汇字典和单词集合"""
        vocab_items = db.query(VocabItem).filter(
            VocabItem.user_id == user_id,
            VocabItem.is_active == True
        ).all()
        
        existing_words = {item.word.lower() for item in vocab_items}
        vocab_dict = {item.word.lower(): item for item in vocab_items}
        
        return vocab_dict, existing_words
    
    def _create_word_entry(self, word: str, grade: str, user_id: str) -> VocabItem:
        """创建词汇条目的默认格式（复制 talkai_py 逻辑）"""
        today = datetime.utcnow()
        return VocabItem(
            user_id=user_id,
            word=word.lower(),
            source="level_vocab",
            level=grade,
            encounter_count=1,
            correct_count=0,
            mastery_score=0.0,
            is_mastered=False,
            is_active=True,
            created_at=today,
            updated_at=today
        )
    
    def _update_existing_word(self, vocab_item: VocabItem, grade: str) -> None:
        """更新现有词汇的source和level（复制 talkai_py 逻辑）"""
        vocab_item.source = "level_vocab"
        vocab_item.level = grade
        vocab_item.updated_at = datetime.utcnow()
    
    def load_vocab_by_grade(self, user_id: str, db: Session) -> bool:
        """根据用户grade从txt文件加载对应词汇表（完全复制 talkai_py 逻辑）"""
        try:
            # 获取用户资料
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"用户 {user_id} 不存在")
                return False
                
            grade = user.grade
            if not grade:
                logger.error("用户未设置grade")
                return False
                
            # 检查是否已添加过此级别词汇（通过实际的数据库记录检查）
            from app.models.vocab import VocabItem
            existing_vocab_count = db.query(VocabItem).filter(
                VocabItem.user_id == user_id,
                VocabItem.level == grade,
                VocabItem.is_active == True
            ).count()
            
            if existing_vocab_count > 0:
                logger.info(f"已添加过 {grade} 级别的词汇，数据库中有 {existing_vocab_count} 个词汇")
                return False
            
            logger.info(f"用户 {user_id} 尚未加载 {grade} 级别词汇，开始加载...")
                
            # 获取对应txt文件名
            txt_filename = self.grade_to_txt_file.get(grade)
            if not txt_filename:
                logger.error(f"不支持的grade级别: {grade}")
                return False
                
            # 构建txt文件路径
            txt_file_path = os.path.join(self.level_words_dir, txt_filename)
            if not os.path.exists(txt_file_path):
                logger.error(f"文件不存在: {txt_file_path}")
                return False
                
            # 从txt文件读取词汇
            words_from_txt = self._read_txt_words(txt_file_path)
            if not words_from_txt:
                logger.error(f"从 {txt_filename} 中未读取到有效词汇")
                return False
            
            # 加载当前学习词汇
            vocab_dict, existing_words = self._load_current_vocab(user_id, db)
            
            # 处理词汇：更新已存在的，添加新的
            updated_count = 0
            added_count = 0
            
            for word in words_from_txt:
                if word in existing_words:
                    # 更新已存在的词汇
                    self._update_existing_word(vocab_dict[word], grade)
                    updated_count += 1
                else:
                    # 添加新词汇
                    new_entry = self._create_word_entry(word, grade, user_id)
                    db.add(new_entry)
                    added_count += 1
            
            # 记录已添加的词汇级别
            added_vocab_levels = user.added_vocab_levels or []
            if grade not in added_vocab_levels:
                added_vocab_levels.append(grade)
                user.added_vocab_levels = added_vocab_levels
            
            db.commit()
            
            logger.info(f"成功处理 {grade} 级别词汇:")
            logger.info(f"  - 新添加: {added_count} 个词汇")
            logger.info(f"  - 更新现有: {updated_count} 个词汇")
            
            return True
            
        except Exception as e:
            logger.error(f"加载词汇失败: {e}")
            db.rollback()
            return False
    
    def monitor_profile_changes(self, user_id: str, db: Session) -> bool:
        """监听用户配置变化并自动添加词汇（复制 talkai_py 逻辑）"""
        try:
            # 检查当前用户的grade并加载对应词汇
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.grade:
                return False
            
            grade = user.grade
            logger.info(f"检测到用户grade为 {grade}，尝试添加对应词汇...")
            
            # 直接调用load_vocab_by_grade，让它内部处理重复检查
            success = self.load_vocab_by_grade(user_id, db)
            if not success:
                logger.info(f"未添加 {grade} 级别词汇（可能已存在或其他原因）")
            
            return success
            
        except Exception as e:
            logger.error(f"监听用户配置变化失败: {e}")
            return False
    
    def get_available_grades(self) -> List[str]:
        """获取所有可用的等级列表"""
        return list(self.grade_to_txt_file.keys())
    
    def get_vocab_count_by_grade(self, grade: str) -> int:
        """获取指定等级的词汇数量"""
        txt_filename = self.grade_to_txt_file.get(grade)
        if not txt_filename:
            return 0
            
        txt_file_path = os.path.join(self.level_words_dir, txt_filename)
        if not os.path.exists(txt_file_path):
            return 0
        
        words = self._read_txt_words(txt_file_path)
        return len(words)


# 创建全局实例
vocab_loader = VocabLoader()