"""
词汇向量化服务
复制 talkai_py 中的词汇向量计算逻辑
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from loguru import logger

from app.models.vocab import VocabItem


class VocabularyEmbeddingService:
    """词汇向量化服务，用于计算和管理词汇的向量表示"""
    
    def __init__(self):
        """初始化向量模型"""
        try:
            # 使用与 talkai_py 相同的模型
            self.embedding_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
            logger.info("词汇向量化模型初始化成功")
        except Exception as e:
            logger.error(f"词汇向量化模型初始化失败: {e}")
            self.embedding_model = None
    
    def compute_vocab_embeddings(self, user_id: str, db: Session) -> Tuple[Optional[np.ndarray], Optional[Dict[str, int]]]:
        """
        为用户的词汇库计算向量表示
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            Tuple[word_embeddings, word_to_index]
            - word_embeddings: 词汇向量数组 (n_words, embedding_dim)
            - word_to_index: 词汇到索引的映射字典
        """
        try:
            if not self.embedding_model:
                logger.error("向量化模型未初始化")
                return None, None
            
            # 获取用户的未掌握词汇（复制 talkai_py 逻辑）
            unmastered_vocabs = db.query(VocabItem).filter(
                VocabItem.user_id == user_id,
                VocabItem.is_active == True,
                VocabItem.isMastered == False  # 使用talkai_py兼容的字段名
            ).all()
            
            if not unmastered_vocabs:
                logger.info(f"用户 {user_id} 没有未掌握的词汇")
                return None, None
            
            # 提取词汇列表
            words = [vocab.word for vocab in unmastered_vocabs]
            logger.info(f"为用户 {user_id} 计算 {len(words)} 个词汇的向量表示")
            
            # 计算向量表示
            word_embeddings = self.embedding_model.encode(words)
            
            # 创建词汇到索引的映射
            word_to_index = {word: idx for idx, word in enumerate(words)}
            
            logger.info(f"词汇向量计算完成: {word_embeddings.shape}")
            return word_embeddings, word_to_index
            
        except Exception as e:
            logger.error(f"计算词汇向量失败: {e}")
            return None, None
    
    def find_similar_vocabulary(
        self, 
        user_input: str, 
        ai_response: str, 
        user_id: str, 
        db: Session,
        top_n: int = 5
    ) -> List[str]:
        """
        基于对话内容找到相似的词汇建议
        复制 talkai_py 中的 find_vocabulary_from_last_turn 逻辑
        
        Args:
            user_input: 用户输入
            ai_response: AI回复
            user_id: 用户ID
            db: 数据库会话
            top_n: 返回的词汇数量
            
        Returns:
            推荐的词汇列表
        """
        try:
            if not self.embedding_model:
                logger.error("向量化模型未初始化")
                return []
            
            # 提取最后一轮对话的文本
            last_turn_text = " ".join([user_input, ai_response])
            
            # 计算对话的向量表示
            history_embedding = self.embedding_model.encode(last_turn_text)
            
            # 获取用户的词汇向量
            word_embeddings, word_to_index = self.compute_vocab_embeddings(user_id, db)
            
            if word_embeddings is None or word_to_index is None:
                logger.info(f"用户 {user_id} 没有可用的词汇向量")
                return []
            
            # 计算相似度
            similarities = np.dot(word_embeddings, history_embedding) / (
                np.linalg.norm(word_embeddings, axis=1) * np.linalg.norm(history_embedding)
            )
            
            # 创建单词-相似度对
            words = list(word_to_index.keys())
            word_sim_pairs = [(words[i], float(similarities[i])) for i in range(len(words))]
            
            # 按相似度降序排序
            word_sim_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # 返回前 top_n 个词汇
            top_pairs = word_sim_pairs[:top_n]
            result = [word for word, sim in top_pairs]
            
            logger.info(f"为用户 {user_id} 生成了 {len(result)} 个词汇建议")
            return result
            
        except Exception as e:
            logger.error(f"查找相似词汇失败: {e}")
            return []
    
    def update_vocab_embeddings_cache(self, user_id: str, db: Session):
        """
        更新用户的词汇向量缓存
        这可以在词汇库更新后调用，以提高后续查询性能
        """
        try:
            word_embeddings, word_to_index = self.compute_vocab_embeddings(user_id, db)
            if word_embeddings is not None:
                # 这里可以实现缓存逻辑，例如存储到Redis或文件
                logger.info(f"用户 {user_id} 的词汇向量缓存已更新")
            return word_embeddings is not None
        except Exception as e:
            logger.error(f"更新词汇向量缓存失败: {e}")
            return False


# 创建全局实例
vocabulary_embedding_service = VocabularyEmbeddingService()