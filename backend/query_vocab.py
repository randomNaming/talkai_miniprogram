#!/usr/bin/env python3
"""
独立的词汇库查询工具
功能：查询字典数据库和用户词汇表中单词的所有属性
用法：python query_vocab.py <单词> [选项]

本文件代码逻辑：
1. 连接字典数据库(dictionary400k.db)和用户数据库(talkai.db)  
2. 提供英文单词和中文词汇的查询功能
3. 显示字典属性和用户学习数据的完整信息
4. 支持模糊匹配和精确查询
5. 提供命令行接口便于独立使用
"""

import os
import sys
import sqlite3
import argparse
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from tabulate import tabulate


class VocabQueryTool:
    """词汇查询工具类"""
    
    def __init__(self, dict_db_path: str = "./data/db/dictionary400k.db", 
                 user_db_path: str = "./data/db/talkai.db"):
        """
        初始化查询工具
        
        Args:
            dict_db_path: 字典数据库路径
            user_db_path: 用户数据库路径
        """
        self.dict_db_path = dict_db_path
        self.user_db_path = user_db_path
        
        # 检查数据库文件是否存在
        if not os.path.exists(self.dict_db_path):
            print(f"警告: 字典数据库不存在: {self.dict_db_path}")
        
        if not os.path.exists(self.user_db_path):
            print(f"警告: 用户数据库不存在: {self.user_db_path}")
    
    def _is_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def query_dict_word(self, word: str, fuzzy: bool = False) -> Optional[Dict[str, Any]]:
        """
        查询字典数据库中的单词信息
        
        Args:
            word: 要查询的单词
            fuzzy: 是否使用模糊匹配
            
        Returns:
            包含单词信息的字典，如果未找到则返回None
        """
        try:
            if not os.path.exists(self.dict_db_path):
                return None
            
            conn = sqlite3.connect(self.dict_db_path)
            cursor = conn.cursor()
            
            if fuzzy:
                sql = """
                SELECT word, phonetic, definition, translation, pos, collins, oxford, tag, exchange 
                FROM stardict 
                WHERE word LIKE ? 
                ORDER BY word 
                LIMIT 1
                """
                cursor.execute(sql, (f"{word}%",))
            else:
                sql = """
                SELECT word, phonetic, definition, translation, pos, collins, oxford, tag, exchange 
                FROM stardict 
                WHERE word = ?
                """
                cursor.execute(sql, (word,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'word': row[0],
                    'phonetic': row[1] or '',
                    'definition': row[2] or '',
                    'translation': row[3] or '',
                    'pos': row[4] or '',
                    'collins': row[5] or 0,
                    'oxford': row[6] or 0,
                    'tag': row[7] or '',
                    'exchange': row[8] or ''
                }
            return None
            
        except Exception as e:
            print(f"查询字典数据库出错: {e}")
            return None
    
    def search_chinese_in_dict(self, chinese_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        在字典中搜索包含中文的英文单词
        
        Args:
            chinese_text: 中文查询文本
            limit: 结果数量限制
            
        Returns:
            匹配的单词列表
        """
        try:
            if not os.path.exists(self.dict_db_path):
                return []
            
            conn = sqlite3.connect(self.dict_db_path)
            cursor = conn.cursor()
            
            sql = """
            SELECT word, phonetic, definition, translation, pos, collins, oxford, tag, exchange 
            FROM stardict 
            WHERE definition LIKE ? OR translation LIKE ? 
            ORDER BY 
                CASE 
                    WHEN translation = ? THEN 1
                    WHEN translation LIKE ? THEN 2
                    WHEN definition LIKE ? THEN 3
                    ELSE 4
                END
            LIMIT ?
            """
            
            search_pattern = f'%{chinese_text}%'
            exact_pattern = chinese_text
            cursor.execute(sql, (search_pattern, search_pattern, exact_pattern, 
                               f'%{exact_pattern}', f'%{exact_pattern}', limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'word': row[0],
                    'phonetic': row[1] or '',
                    'definition': row[2] or '',
                    'translation': row[3] or '',
                    'pos': row[4] or '',
                    'collins': row[5] or 0,
                    'oxford': row[6] or 0,
                    'tag': row[7] or '',
                    'exchange': row[8] or ''
                })
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"搜索中文词汇出错: {e}")
            return []
    
    def query_user_vocab(self, word: str, user_id: str = None) -> List[Dict[str, Any]]:
        """
        查询用户词汇表中的单词学习数据
        
        Args:
            word: 要查询的单词
            user_id: 用户ID，如果为None则查询所有用户
            
        Returns:
            用户学习数据列表
        """
        try:
            if not os.path.exists(self.user_db_path):
                return []
            
            conn = sqlite3.connect(self.user_db_path)
            cursor = conn.cursor()
            
            if user_id:
                sql = """
                SELECT id, user_id, word, definition, phonetic, translation, source, level,
                       wrong_use_count, right_use_count, last_used, added_date, familiarity,
                       mastery_score, is_active, isMastered
                FROM vocab_items 
                WHERE word = ? AND user_id = ?
                """
                cursor.execute(sql, (word, user_id))
            else:
                sql = """
                SELECT id, user_id, word, definition, phonetic, translation, source, level,
                       wrong_use_count, right_use_count, last_used, added_date, familiarity,
                       mastery_score, is_active, isMastered
                FROM vocab_items 
                WHERE word = ?
                """
                cursor.execute(sql, (word,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'user_id': row[1],
                    'word': row[2],
                    'definition': row[3] or '',
                    'phonetic': row[4] or '',
                    'translation': row[5] or '',
                    'source': row[6] or '',
                    'level': row[7] or '',
                    'wrong_use_count': row[8] or 0,
                    'right_use_count': row[9] or 0,
                    'last_used': row[10],
                    'added_date': row[11],
                    'familiarity': row[12] or 0.0,
                    'mastery_score': row[13] or 0.0,
                    'is_active': bool(row[14]),
                    'isMastered': bool(row[15]),
                    'encounter_count': (row[8] or 0) + (row[9] or 0)
                })
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"查询用户词汇出错: {e}")
            return []
    
    def display_dict_result(self, word_data: Dict[str, Any]):
        """显示字典查询结果"""
        if not word_data:
            print("字典中未找到该单词")
            return
        
        print("\n=== 字典信息 ===")
        table_data = [
            ["属性", "值"],
            ["单词", word_data['word']],
            ["音标", word_data['phonetic']],
            ["词性", word_data['pos']],
            ["英文定义", word_data['definition'][:100] + "..." if len(word_data['definition']) > 100 else word_data['definition']],
            ["中文翻译", word_data['translation']],
            ["柯林斯等级", word_data['collins']],
            ["牛津等级", word_data['oxford']],
            ["标签", word_data['tag']],
            ["词形变化", word_data['exchange']]
        ]
        
        print(tabulate(table_data, headers="firstrow", tablefmt="grid"))
        
        # 如果定义很长，单独显示
        if len(word_data['definition']) > 100:
            print(f"\n完整英文定义:\n{word_data['definition']}")
    
    def display_chinese_search_results(self, results: List[Dict[str, Any]], chinese_text: str):
        """显示中文搜索结果"""
        if not results:
            print(f"未找到包含'{chinese_text}'的英文单词")
            return
        
        print(f"\n=== 包含'{chinese_text}'的英文单词 ===")
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['word']}")
            if result['phonetic']:
                print(f"   音标: {result['phonetic']}")
            if result['translation']:
                print(f"   中文: {result['translation']}")
            if result['definition']:
                definition = result['definition'][:150] + "..." if len(result['definition']) > 150 else result['definition']
                print(f"   英文: {definition}")
    
    def display_user_vocab_results(self, results: List[Dict[str, Any]], word: str):
        """显示用户词汇学习数据"""
        if not results:
            print(f"用户词汇表中未找到'{word}'")
            return
        
        print(f"\n=== 用户学习数据 ('{word}') ===")
        
        for i, vocab in enumerate(results, 1):
            print(f"\n--- 记录 {i} (用户: {vocab['user_id']}) ---")
            
            table_data = [
                ["属性", "值"],
                ["ID", vocab['id']],
                ["用户ID", vocab['user_id']],
                ["单词", vocab['word']],
                ["定义", vocab['definition'][:100] + "..." if len(vocab['definition']) > 100 else vocab['definition']],
                ["音标", vocab['phonetic']],
                ["翻译", vocab['translation']],
                ["来源", vocab['source']],
                ["等级", vocab['level']],
                ["错误次数", vocab['wrong_use_count']],
                ["正确次数", vocab['right_use_count']],
                ["总遇到次数", vocab['encounter_count']],
                ["熟悉度", f"{vocab['familiarity']:.2f}"],
                ["掌握分数", f"{vocab['mastery_score']:.2f}"],
                ["是否激活", "是" if vocab['is_active'] else "否"],
                ["是否掌握", "是" if vocab['isMastered'] else "否"],
                ["最后使用", vocab['last_used'] or "未使用"],
                ["添加日期", vocab['added_date']]
            ]
            
            print(tabulate(table_data, headers="firstrow", tablefmt="grid"))
    
    def query_word(self, word: str, fuzzy: bool = False, user_id: str = None, 
                   show_dict: bool = True, show_user: bool = True):
        """
        综合查询单词的所有属性
        
        Args:
            word: 要查询的单词
            fuzzy: 是否使用模糊匹配
            user_id: 特定用户ID
            show_dict: 是否显示字典信息
            show_user: 是否显示用户学习数据
        """
        word = word.strip().lower()
        
        print(f"查询单词: '{word}'")
        print("=" * 50)
        
        # 检查是否为中文查询
        if self._is_chinese(word):
            if show_dict:
                results = self.search_chinese_in_dict(word, limit=10)
                self.display_chinese_search_results(results, word)
        else:
            # 英文单词查询
            if show_dict:
                dict_result = self.query_dict_word(word, fuzzy=fuzzy)
                self.display_dict_result(dict_result)
            
            if show_user:
                user_results = self.query_user_vocab(word, user_id=user_id)
                self.display_user_vocab_results(user_results, word)


def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(
        description="词汇库查询工具 - 查询单词的字典信息和用户学习数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python query_vocab.py hello              # 查询 'hello' 的所有信息
  python query_vocab.py 你好               # 中文查英文
  python query_vocab.py hel --fuzzy        # 模糊匹配以 'hel' 开头的单词
  python query_vocab.py hello --user-id user123  # 查询特定用户的学习数据
  python query_vocab.py hello --dict-only  # 只显示字典信息
  python query_vocab.py hello --user-only  # 只显示用户学习数据
        """
    )
    
    parser.add_argument("word", help="要查询的单词或中文词汇")
    parser.add_argument("--fuzzy", action="store_true", help="使用模糊匹配(仅对英文单词有效)")
    parser.add_argument("--user-id", help="指定用户ID")
    parser.add_argument("--dict-only", action="store_true", help="只显示字典信息")
    parser.add_argument("--user-only", action="store_true", help="只显示用户学习数据")
    parser.add_argument("--dict-db", default="./data/db/dictionary400k.db", help="字典数据库路径")
    parser.add_argument("--user-db", default="./data/db/talkai.db", help="用户数据库路径")
    
    args = parser.parse_args()
    
    # 创建查询工具实例
    tool = VocabQueryTool(dict_db_path=args.dict_db, user_db_path=args.user_db)
    
    # 确定显示选项
    show_dict = not args.user_only
    show_user = not args.dict_only
    
    # 执行查询
    tool.query_word(
        word=args.word,
        fuzzy=args.fuzzy,
        user_id=args.user_id,
        show_dict=show_dict,
        show_user=show_user
    )


if __name__ == "__main__":
    main()