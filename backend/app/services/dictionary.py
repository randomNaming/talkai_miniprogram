"""
Dictionary service for word lookups
"""
import os
import sqlite3
import re
from typing import List, Dict, Any, Optional
from loguru import logger

from app.core.config import settings


class DictionaryService:
    """Dictionary service for word lookups"""
    
    def __init__(self):
        self.dict_path = settings.dictionary_db_path
        
    def _is_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def _format_word_result(self, word_data: Dict[str, Any], is_chinese_query: bool = False) -> Dict[str, Any]:
        """
        Format word result for API response
        复制 talkai_py 中的格式化逻辑
        """
        if not word_data:
            return None
        
        # 如果是中文查询，使用talkai_py的格式化逻辑返回字符串
        if is_chinese_query:
            return self._format_chinese_query_result(word_data)
        
        # 英文查询，使用常规字典格式
        result = {
            "word": word_data.get("word") or "",
            "phonetic": word_data.get("phonetic") or "",
            "definition": word_data.get("definition") or "",
            "translation": word_data.get("translation") or "",
            "pos": word_data.get("pos") or "",  # part of speech
            "collins": word_data.get("collins") or 0,
            "oxford": word_data.get("oxford") or 0,
            "tag": word_data.get("tag") or "",
            "exchange": word_data.get("exchange") or "",
            "formatted_definition": None
        }
        
        return result
    
    def _format_chinese_query_result(self, word_data: Dict[str, Any]) -> str:
        """
        格式化中文查询的英文结果显示，完全复制 talkai_py/ecdict.py 的 format_word_result 逻辑
        """
        try:
            if not word_data:
                return None
            
            result = []
            
            # 第一行：单词和音标 (复制 talkai_py/ecdict.py:32-35)
            first_line = word_data.get("word", "")
            if word_data.get('phonetic'):
                first_line += f"    <phonetic>{word_data['phonetic']}</phonetic>"
            result.append(first_line)
            
            # 第二行：释义（definition 或 translation）(复制 talkai_py/ecdict.py:37-45)
            definition_line = ""
            if word_data.get('definition'):
                definition_line = word_data['definition']
            elif word_data.get('translation'):
                definition_line = word_data['translation']
            
            if definition_line:
                result.append(definition_line)
            
            return "\n".join(result)
            
        except Exception as e:
            logger.error(f"Error formatting Chinese query result: {e}")
            definition = word_data.get("definition", "") or word_data.get("translation", "")
            word = word_data.get("word", "")
            phonetic = word_data.get("phonetic", "")
            
            # 基本格式的后备方案
            if phonetic:
                return f"{word}    <phonetic>{phonetic}</phonetic>\n{definition}"
            else:
                return f"{word}\n{definition}"
    
    def _search_chinese_in_translation(self, chinese_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for Chinese text in definition and translation fields"""
        try:
            if not os.path.exists(self.dict_path):
                logger.error(f"Dictionary database not found: {self.dict_path}")
                return []
            
            conn = sqlite3.connect(self.dict_path)
            cursor = conn.cursor()
            
            # 获取所有可能包含该中文的记录 (完全复制 talkai_py/ecdict.py:78-85)
            sql = """
            SELECT word, phonetic, definition, translation, pos, collins, oxford, tag, exchange 
            FROM stardict 
            WHERE definition LIKE ? OR translation LIKE ? 
            """
            search_pattern = f'%{chinese_text}%'
            cursor.execute(sql, (search_pattern, search_pattern))
            
            results = []
            seen_words = set()
            
            # Build regex for exact matching
            escaped_text = re.escape(chinese_text)
            pattern = rf'(^|[\s\.\,\;\:\!\?\(\)\[\]\{{}}，。；：！？（）【】「」]){escaped_text}($|[\s\.\,\;\:\!\?\(\)\[\]\{{}}，。；：！？（）【】「」])'
            
            for row in cursor.fetchall():
                word = row[0]
                if word in seen_words:
                    continue
                    
                definition = row[2] or ""
                translation = row[3] or ""
                
                # Check for exact match
                if re.search(pattern, definition) or re.search(pattern, translation):
                    seen_words.add(word)
                    word_data = {
                        'word': word,
                        'phonetic': row[1],
                        'definition': definition,
                        'translation': translation,
                        'pos': row[4],
                        'collins': row[5],
                        'oxford': row[6],
                        'tag': row[7],
                        'exchange': row[8]
                    }
                    results.append(word_data)
                    
                    if len(results) >= limit:
                        break
            
            conn.close()
            
            # Sort by match quality
            def sort_key(item):
                def_text = item['definition'] or ""
                trans_text = item['translation'] or ""
                
                # Exact match
                if def_text.strip() == chinese_text or trans_text.strip() == chinese_text:
                    return 0
                # Simple format match (e.g., "n. 香蕉")
                elif def_text.strip().endswith(chinese_text) or trans_text.strip().endswith(chinese_text):
                    return 1
                else:
                    return 2
            
            results.sort(key=sort_key)
            return results
            
        except Exception as e:
            logger.error(f"Error searching Chinese text: {e}")
            return []
    
    def _query_english_word(self, word: str, fuzzy: bool = False) -> Optional[Dict[str, Any]]:
        """Query English word in dictionary"""
        try:
            if not os.path.exists(self.dict_path):
                logger.error(f"Dictionary database not found: {self.dict_path}")
                return None
            
            conn = sqlite3.connect(self.dict_path)
            cursor = conn.cursor()
            
            if fuzzy:
                # Fuzzy search - find words starting with the input
                sql = "SELECT word, phonetic, definition, translation, pos, collins, oxford, tag, exchange FROM stardict WHERE word LIKE ? LIMIT 1"
                cursor.execute(sql, (f"{word}%",))
            else:
                # Exact search
                sql = "SELECT word, phonetic, definition, translation, pos, collins, oxford, tag, exchange FROM stardict WHERE word = ?"
                cursor.execute(sql, (word,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'word': row[0],
                    'phonetic': row[1],
                    'definition': row[2],
                    'translation': row[3],
                    'pos': row[4],
                    'collins': row[5],
                    'oxford': row[6],
                    'tag': row[7],
                    'exchange': row[8]
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error querying English word: {e}")
            return None
    
    def query_word(self, word: str, fuzzy: bool = False) -> Optional[Dict[str, Any]]:
        """
        Query word in dictionary
        
        Args:
            word: Word to query
            fuzzy: Whether to use fuzzy matching for English words
            
        Returns:
            Dictionary containing word information or None if not found
        """
        try:
            word = word.strip().lower()
            
            if not word:
                return None
            
            # Auto-detect Chinese query
            if self._is_chinese(word):
                # Chinese to English lookup - 复制 talkai_py/language_model.py:371-374
                results = self._search_chinese_in_translation(word, limit=10)
                if results and len(results) > 0:
                    # 使用 format_multiple_word_results 逻辑
                    formatted_results = []
                    for word_data in results[:5]:  # limit=5 如 talkai_py
                        formatted = self._format_word_result(word_data, is_chinese_query=True)
                        if formatted:
                            formatted_results.append(formatted)
                    
                    if formatted_results:
                        return "\n\n".join(formatted_results)
                    else:
                        return None
                else:
                    return None
            else:
                # English word lookup
                word_data = self._query_english_word(word, fuzzy=fuzzy)
                if word_data:
                    return self._format_word_result(word_data, is_chinese_query=False)
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Error in word query: {e}")
            return None
    
    def search_words(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for multiple words matching the query
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of dictionaries containing word information
        """
        try:
            query = query.strip().lower()
            
            if not query:
                return []
            
            if self._is_chinese(query):
                # Chinese to English search - 复制 talkai_py 的 format_multiple_word_results 逻辑
                results = self._search_chinese_in_translation(query, limit=limit)
                formatted_results = []
                for result in results:
                    formatted = self._format_word_result(result, is_chinese_query=True)
                    if formatted:
                        formatted_results.append(formatted)
                # 对于中文查询，返回单个组合的格式化字符串
                if formatted_results:
                    combined_result = "\n\n".join(formatted_results)
                    return [{
                        "word": query,
                        "phonetic": "",
                        "definition": combined_result,
                        "translation": "",
                        "pos": "",
                        "collins": 0,
                        "oxford": 0,
                        "tag": "",
                        "exchange": "",
                        "formatted_definition": combined_result
                    }]
                else:
                    return []
            else:
                # English word search (fuzzy)
                if not os.path.exists(self.dict_path):
                    logger.error(f"Dictionary database not found: {self.dict_path}")
                    return []
                
                conn = sqlite3.connect(self.dict_path)
                cursor = conn.cursor()
                
                sql = """
                SELECT word, phonetic, definition, translation, pos, collins, oxford, tag, exchange 
                FROM stardict 
                WHERE word LIKE ? 
                ORDER BY word 
                LIMIT ?
                """
                cursor.execute(sql, (f"{query}%", limit))
                
                results = []
                for row in cursor.fetchall():
                    word_data = {
                        'word': row[0],
                        'phonetic': row[1],
                        'definition': row[2],
                        'translation': row[3],
                        'pos': row[4],
                        'collins': row[5],
                        'oxford': row[6],
                        'tag': row[7],
                        'exchange': row[8]
                    }
                    results.append(self._format_word_result(word_data, is_chinese_query=False))
                
                conn.close()
                return results
                
        except Exception as e:
            logger.error(f"Error in word search: {e}")
            return []


# Global dictionary service instance
dictionary_service = DictionaryService()