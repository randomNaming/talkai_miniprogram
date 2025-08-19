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
    
    def _format_word_result(self, word_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format word result for API response"""
        if not word_data:
            return None
        
        return {
            "word": word_data.get("word") or "",
            "phonetic": word_data.get("phonetic") or "",
            "definition": word_data.get("definition") or "",
            "translation": word_data.get("translation") or "",
            "pos": word_data.get("pos") or "",  # part of speech
            "collins": word_data.get("collins") or 0,
            "oxford": word_data.get("oxford") or 0,
            "tag": word_data.get("tag") or "",
            "exchange": word_data.get("exchange") or ""
        }
    
    def _search_chinese_in_translation(self, chinese_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for Chinese text in definition and translation fields"""
        try:
            if not os.path.exists(self.dict_path):
                logger.error(f"Dictionary database not found: {self.dict_path}")
                return []
            
            conn = sqlite3.connect(self.dict_path)
            cursor = conn.cursor()
            
            # Search for records containing the Chinese text
            sql = """
            SELECT word, phonetic, definition, translation, pos, collins, oxford, tag, exchange 
            FROM stardict 
            WHERE definition LIKE ? OR translation LIKE ? 
            LIMIT ?
            """
            search_pattern = f'%{chinese_text}%'
            cursor.execute(sql, (search_pattern, search_pattern, limit * 2))
            
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
                # Chinese to English lookup
                results = self._search_chinese_in_translation(word, limit=1)
                if results:
                    return self._format_word_result(results[0])
                else:
                    return None
            else:
                # English word lookup
                word_data = self._query_english_word(word, fuzzy=fuzzy)
                if word_data:
                    return self._format_word_result(word_data)
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
                # Chinese to English search
                results = self._search_chinese_in_translation(query, limit=limit)
                return [self._format_word_result(result) for result in results]
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
                    results.append(self._format_word_result(word_data))
                
                conn.close()
                return results
                
        except Exception as e:
            logger.error(f"Error in word search: {e}")
            return []


# Global dictionary service instance
dictionary_service = DictionaryService()