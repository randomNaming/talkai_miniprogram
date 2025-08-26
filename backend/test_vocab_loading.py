#!/usr/bin/env python3
"""
测试词汇加载功能
"""
import sys
import os
sys.path.append('/Users/pean/aiproject/talkai_mini/backend')

from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.services.vocab_loader import vocab_loader
from app.models.user import User
from app.models.vocab import VocabItem

def test_vocab_loading():
    """测试词汇加载功能"""
    db = SessionLocal()
    try:
        # 获取最新用户
        user = db.query(User).order_by(User.created_at.desc()).first()
        if not user:
            print("没有找到用户")
            return
            
        print(f"用户 ID: {user.id}")
        print(f"用户 grade: {user.grade}")
        print(f"已添加词汇级别: {user.added_vocab_levels}")
        
        # 检查当前词汇数量
        current_vocab_count = db.query(VocabItem).filter(
            VocabItem.user_id == user.id,
            VocabItem.is_active == True
        ).count()
        print(f"当前词汇数量: {current_vocab_count}")
        
        # 手动加载Primary School词汇
        print("\n尝试加载Primary School词汇...")
        
        # 先重置用户的added_vocab_levels来强制重新加载
        user.added_vocab_levels = []
        db.commit()
        
        success = vocab_loader.load_vocab_by_grade(user.id, db)
        print(f"词汇加载结果: {success}")
        
        # 检查加载后的词汇数量
        new_vocab_count = db.query(VocabItem).filter(
            VocabItem.user_id == user.id,
            VocabItem.is_active == True
        ).count()
        print(f"加载后词汇数量: {new_vocab_count}")
        
        # 检查加载的词汇示例
        sample_vocabs = db.query(VocabItem).filter(
            VocabItem.user_id == user.id,
            VocabItem.is_active == True
        ).limit(5).all()
        
        print("\n词汇示例:")
        for vocab in sample_vocabs:
            print(f"- {vocab.word} (level: {vocab.level}, source: {vocab.source})")
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_vocab_loading()