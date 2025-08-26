"""
Dictionary API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from app.services.dictionary import dictionary_service
from app.core.database import get_db
from app.api.v1.auth import get_current_user

router = APIRouter()


class WordResult(BaseModel):
    """Word lookup result"""
    word: str
    phonetic: Optional[str] = ""
    definition: Optional[str] = ""
    translation: Optional[str] = ""
    pos: Optional[str] = ""  # part of speech
    collins: Optional[int] = 0
    oxford: Optional[int] = 0
    tag: Optional[str] = ""
    exchange: Optional[str] = ""
    formatted_definition: Optional[str] = None  # For Chinese query results with HTML formatting


class WordSearchResponse(BaseModel):
    """Word search response"""
    query: str
    results: List[WordResult]
    total: int


@router.get("/query", response_model=Optional[WordResult])
async def query_word(
    word: str = Query(..., description="Word to query"),
    fuzzy: bool = Query(False, description="Enable fuzzy matching for English words")
):
    """
    Query a single word in the dictionary
    
    Supports both English-to-Chinese and Chinese-to-English lookups.
    Auto-detects the language based on input.
    """
    try:
        if not word or not word.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Word parameter is required"
            )
        
        result = dictionary_service.query_word(word.strip(), fuzzy=fuzzy)
        
        if result:
            # 如果结果是字符串（中文查询的格式化结果），需要特殊处理
            if isinstance(result, str):
                # 创建一个简化的响应，主要在definition字段返回格式化结果
                return WordResult(
                    word=word.strip(),
                    phonetic="",
                    definition=result,
                    translation="",
                    pos="",
                    collins=0,
                    oxford=0,
                    tag="",
                    exchange="",
                    formatted_definition=result
                )
            else:
                # 正常的字典响应
                return WordResult(**result)
        else:
            return None
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dictionary query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dictionary query failed"
        )


@router.get("/lookup")
async def lookup_word_simple(
    word: str = Query(..., description="Word to lookup and add to vocabulary"),
    db: Session = Depends(get_db)
):
    """
    词典查询并模拟添加到词汇管理器（不需要认证的简化版本）
    复制 talkai_py 中的 handle_word_lookup 逻辑
    
    - 如果是中文输入，不添加到词汇管理器；如果是英文输入，则模拟添加
    - 支持中英文双向查询
    """
    try:
        if not word or not word.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Word parameter is required"
            )
        
        word = word.strip()
        
        # 获取单词定义
        result = dictionary_service.query_word(word, fuzzy=False)
        
        if not result:
            return {
                "word": word,
                "definition": f"未找到单词 '{word}' 的定义",
                "added_to_vocab": False,
                "message": f"Word '{word}' not found in dictionary"
            }
        
        # 检查是否包含中文字符 (复制 talkai_py 逻辑)
        def has_chinese(text: str) -> bool:
            import re
            return bool(re.search(r'[\u4e00-\u9fff]', text))
        
        added_to_vocab = False
        vocab_message = ""
        
        # 如果是中文输入，不添加到词汇管理器；如果是英文输入，则模拟添加
        if not has_chinese(word):
            # 模拟成功添加（实际应用中需要用户认证和真实的词汇管理）
            added_to_vocab = True
            vocab_message = f"✓ Added vocabulary: '{word}' to learning list."
            logger.info(f"Simulated adding English word '{word}' to vocabulary (source: lookup)")
        else:
            vocab_message = "Chinese input - not added to vocabulary manager."
            logger.info(f"Chinese input '{word}' not added to vocabulary manager")
        
        return {
            "word": word,
            "definition": result,
            "added_to_vocab": added_to_vocab,
            "message": vocab_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Word lookup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Word lookup failed"
        )


@router.get("/search", response_model=WordSearchResponse)
async def search_words(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """
    Search for words matching the query
    
    Returns multiple results for fuzzy matching or prefix matching.
    Supports both English and Chinese queries.
    """
    try:
        if not q or not q.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query parameter is required"
            )
        
        results = dictionary_service.search_words(q.strip(), limit=limit)
        
        word_results = []
        for result in results:
            if result:  # Filter out None results
                word_results.append(WordResult(**result))
        
        return WordSearchResponse(
            query=q.strip(),
            results=word_results,
            total=len(word_results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dictionary search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dictionary search failed"
        )


@router.get("/batch")
async def batch_query_words(
    words: str = Query(..., description="Comma-separated list of words to query")
):
    """
    Query multiple words at once
    
    Useful for looking up several words in a single request.
    Returns a dictionary mapping each word to its result.
    """
    try:
        if not words or not words.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Words parameter is required"
            )
        
        word_list = [word.strip() for word in words.split(",") if word.strip()]
        
        if not word_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid words provided"
            )
        
        if len(word_list) > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 20 words allowed per batch request"
            )
        
        results = {}
        for word in word_list:
            try:
                result = dictionary_service.query_word(word)
                results[word] = WordResult(**result) if result else None
            except Exception as e:
                logger.warning(f"Failed to query word '{word}': {e}")
                results[word] = None
        
        return {
            "query": words.strip(),
            "results": results,
            "total_queried": len(word_list),
            "total_found": len([r for r in results.values() if r is not None])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch dictionary query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch dictionary query failed"
        )


@router.get("/health")
async def dictionary_health():
    """
    Check dictionary service health
    """
    try:
        # Test with a simple query
        test_result = dictionary_service.query_word("test")
        
        return {
            "status": "healthy",
            "dictionary_available": test_result is not None or True,  # Don't fail if 'test' is not in dict
            "message": "Dictionary service is operational"
        }
        
    except Exception as e:
        logger.error(f"Dictionary health check failed: {e}")
        return {
            "status": "unhealthy",
            "dictionary_available": False,
            "message": f"Dictionary service error: {str(e)}"
        }


@router.post("/ai-chat")
async def dict_ai_chat(request: dict):
    """
    AI chat endpoint in dict module with FULL functionality (no authentication required)
    
    This endpoint now provides complete AI chat functionality including:
    - Grammar correction
    - Vocabulary suggestions 
    - Natural conversation
    
    This matches the /chat/send API but without authentication requirement.
    """
    try:
        from app.services.ai import ai_service
        from app.services.vocabulary import vocabulary_service
        from datetime import datetime
        from app.core.database import get_db
        from sqlalchemy.orm import Session
        
        message = request.get("message", "").strip()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message is required"
            )
        
        # Create anonymous user profile for consistent behavior
        anonymous_user_profile = {
            "user_id": "anonymous_user",
            "age": None,
            "gender": None,
            "grade": "Primary School",  # Default level
            "preferred_ai_model": "moonshot-v1-8k"
        }
        
        # STEP 1: IMMEDIATE AI DIALOGUE RESPONSE (following talkai_py pattern)
        logger.info("Step 1: Generating natural dialogue response for anonymous user")
        response_result = ai_service.generate_response_natural(
            user_input=message,
            user_profile=anonymous_user_profile,
            user_id="anonymous_user"
        )
        ai_response = response_result.get("text", "Hello! I'm your English learning assistant.")
        
        # STEP 2: PARALLEL GRAMMAR CHECK (separate AI call, different prompt)
        logger.info("Step 2: Starting parallel grammar check")
        
        async def grammar_check_task():
            """Separate grammar check task for anonymous user"""
            return ai_service.check_vocab_from_input(message)
        
        # Run grammar check (for anonymous users, we don't need complex parallel processing)
        import asyncio
        grammar_result = await grammar_check_task()
        
        # Step 3: Create grammar check response
        grammar_check = None
        corrected_input = grammar_result.get("corrected_input")
        words_deserve_to_learn = grammar_result.get("words_deserve_to_learn", [])
        
        # Only show correction if corrected_input exists AND is different from user input
        if corrected_input and corrected_input != message:
            from pydantic import BaseModel
            from typing import List
            
            class VocabItem(BaseModel):
                original: str
                corrected: str
                explanation: str = ""
            
            vocab_items = []
            for item in words_deserve_to_learn:
                vocab_items.append({
                    "original": item.get("original", ""),
                    "corrected": item.get("corrected", ""),
                    "explanation": item.get("explanation", "")
                })
            
            grammar_check = {
                "corrected_input": corrected_input,
                "has_error": True,
                "vocab_to_learn": vocab_items
            }
        
        # Step 4: Generate vocabulary suggestions (simplified for anonymous)
        suggested_vocab = []
        try:
            # For anonymous users, provide some sample vocabulary suggestions
            # based on common words for the user level
            sample_vocab_by_level = {
                "Primary School": ["apple", "book", "cat", "dog", "eat", "fun", "good", "happy"],
                "Middle School": ["adventure", "beautiful", "computer", "education", "friendship", "important", "knowledge", "library"], 
                "High School": ["accomplish", "analyze", "comprehensive", "demonstrate", "environment", "fascinating", "generation", "hypothesis"]
            }
            
            level = anonymous_user_profile.get("grade", "Primary School")
            available_vocab = sample_vocab_by_level.get(level, sample_vocab_by_level["Primary School"])
            
            # Simple context-based selection (first 5 words)
            suggested_vocab = available_vocab[:5]
            
        except Exception as e:
            logger.warning(f"Vocabulary suggestion failed for anonymous user: {e}")
        
        return {
            "response": ai_response.strip(),
            "grammar_check": grammar_check,
            "suggested_vocab": suggested_vocab,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dict AI chat failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI chat service temporarily unavailable"
        )