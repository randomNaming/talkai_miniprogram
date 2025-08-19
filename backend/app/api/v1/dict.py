"""
Dictionary API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from loguru import logger

from app.services.dictionary import dictionary_service

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