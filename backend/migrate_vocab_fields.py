#!/usr/bin/env python3
"""
Vocabulary Database Migration Script
将现有的词汇数据库字段迁移为talkai_py兼容格式

字段映射关系：
- encounter_count - correct_count → wrong_use_count
- correct_count → right_use_count  
- last_reviewed → last_used
- created_at → added_date
- is_mastered → isMastered
"""

import sqlite3
from datetime import datetime
import os
import sys

# Add backend path to import models
sys.path.append(os.path.dirname(__file__))

def migrate_vocab_database(db_path: str):
    """执行词汇数据库迁移"""
    
    print(f"开始迁移词汇数据库: {db_path}")
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 检查当前表结构
        cursor.execute("PRAGMA table_info(vocab_items)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        print(f"当前表字段: {list(columns.keys())}")
        
        # 2. 添加新字段（如果不存在）
        new_fields = [
            ("wrong_use_count", "INTEGER DEFAULT 0"),
            ("right_use_count", "INTEGER DEFAULT 0"), 
            ("last_used", "DATETIME"),
            ("added_date", "DATETIME"),
            ("isMastered", "BOOLEAN DEFAULT 0")
        ]
        
        for field_name, field_type in new_fields:
            if field_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE vocab_items ADD COLUMN {field_name} {field_type}")
                    print(f"添加字段: {field_name}")
                except sqlite3.Error as e:
                    print(f"添加字段 {field_name} 失败: {e}")
        
        # 3. 迁移现有数据
        print("开始迁移现有数据...")
        
        # 获取所有现有记录
        cursor.execute("""
            SELECT id, encounter_count, correct_count, last_reviewed, created_at, is_mastered
            FROM vocab_items 
            WHERE wrong_use_count IS NULL OR right_use_count IS NULL
        """)
        
        records = cursor.fetchall()
        print(f"需要迁移 {len(records)} 条记录")
        
        # 批量更新记录
        for record in records:
            record_id, encounter_count, correct_count, last_reviewed, created_at, is_mastered = record
            
            # 计算新字段值
            encounter_count = encounter_count or 0
            correct_count = correct_count or 0
            wrong_use_count = max(0, encounter_count - correct_count)
            right_use_count = correct_count
            
            # 时间字段迁移
            last_used = last_reviewed if last_reviewed else created_at
            added_date = created_at if created_at else datetime.utcnow().isoformat()
            isMastered = bool(is_mastered) if is_mastered is not None else False
            
            # 更新记录
            cursor.execute("""
                UPDATE vocab_items 
                SET wrong_use_count = ?, right_use_count = ?, last_used = ?, added_date = ?, isMastered = ?
                WHERE id = ?
            """, (wrong_use_count, right_use_count, last_used, added_date, isMastered, record_id))
        
        # 4. 提交更改
        conn.commit()
        print("数据库迁移完成!")
        
        # 5. 验证迁移结果
        cursor.execute("SELECT COUNT(*) FROM vocab_items WHERE wrong_use_count IS NOT NULL")
        migrated_count = cursor.fetchone()[0]
        print(f"迁移验证: {migrated_count} 条记录已更新")
        
        # 6. 显示示例数据
        cursor.execute("""
            SELECT word, wrong_use_count, right_use_count, last_used, added_date, isMastered 
            FROM vocab_items 
            LIMIT 5
        """)
        
        sample_records = cursor.fetchall()
        print("\n示例迁移后的数据:")
        print("Word | Wrong | Right | Last Used | Added Date | Mastered")
        print("-" * 60)
        for record in sample_records:
            word, wrong, right, last_used, added_date, mastered = record
            print(f"{word[:10]:<10} | {wrong:>5} | {right:>5} | {str(last_used)[:10]:>10} | {str(added_date)[:10]:>10} | {bool(mastered)}")
            
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """主函数"""
    db_path = "/Users/pean/aiproject/talkai_mini/backend/data/db/talkai.db"
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    # 创建备份
    backup_path = db_path + ".backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"已创建数据库备份: {backup_path}")
    
    try:
        migrate_vocab_database(db_path)
        print("迁移成功完成!")
    except Exception as e:
        print(f"迁移失败: {e}")
        print(f"可以从备份恢复: {backup_path}")
        
if __name__ == "__main__":
    main()