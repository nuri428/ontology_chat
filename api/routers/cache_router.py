# Cache Management API Router
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from api.services.context_cache import context_cache

router = APIRouter(prefix="/api/cache", tags=["cache"])

class CacheInvalidateRequest(BaseModel):
    """캐시 무효화 요청 모델"""
    query: Optional[str] = None
    pattern: Optional[str] = None

class CacheStats(BaseModel):
    """캐시 통계 응답 모델"""
    hits: int
    misses: int
    evictions: int
    total_requests: int
    hit_rate: float
    cache_size: int
    max_size: int

class HotQuery(BaseModel):
    """인기 쿼리 모델"""
    query: str
    hit_count: int
    last_accessed: str

@router.get("/stats", response_model=CacheStats)
async def get_cache_stats() -> Dict[str, Any]:
    """캐시 통계 조회"""
    return context_cache.get_stats()

@router.get("/hot-queries", response_model=List[HotQuery])
async def get_hot_queries(top_n: int = 10) -> List[Dict[str, Any]]:
    """자주 사용되는 쿼리 조회"""
    return context_cache.get_hot_queries(top_n)

@router.post("/invalidate")
async def invalidate_cache(request: CacheInvalidateRequest) -> Dict[str, Any]:
    """특정 캐시 무효화"""
    if not request.query and not request.pattern:
        raise HTTPException(
            status_code=400,
            detail="Either 'query' or 'pattern' must be provided"
        )

    invalidated = await context_cache.invalidate(
        query=request.query,
        pattern=request.pattern
    )

    return {
        "success": True,
        "invalidated_count": invalidated,
        "message": f"Invalidated {invalidated} cache entries"
    }

@router.post("/clear")
async def clear_all_cache() -> Dict[str, Any]:
    """전체 캐시 초기화"""
    await context_cache.clear()
    return {
        "success": True,
        "message": "All cache entries cleared"
    }

@router.post("/cleanup")
async def cleanup_expired() -> Dict[str, Any]:
    """만료된 캐시 정리"""
    cleaned = await context_cache.cleanup_expired()
    return {
        "success": True,
        "cleaned_count": cleaned,
        "message": f"Cleaned up {cleaned} expired entries"
    }