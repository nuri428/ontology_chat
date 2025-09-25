"""Cache management API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from api.services.cached_chat_service import cached_chat_service
from api.cache import multi_level_cache, cache_metrics, CacheLevel

router = APIRouter(prefix="/cache", tags=["Cache Management"])


class CacheStatsResponse(BaseModel):
    """Cache statistics response model."""
    overall: Dict[str, Any]
    l1: Dict[str, Any]
    l2: Optional[Dict[str, Any]]
    l3: Optional[Dict[str, Any]]
    quality_impact: Dict[str, float]
    recommendations: List[str]


class CacheInvalidateRequest(BaseModel):
    """Cache invalidation request model."""
    pattern: Optional[str] = None
    levels: Optional[List[str]] = None


class PreloadRequest(BaseModel):
    """Cache preload request model."""
    queries: List[str]


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_statistics():
    """Get comprehensive cache statistics."""
    try:
        metrics = await cached_chat_service.get_cache_metrics()

        return CacheStatsResponse(
            overall=metrics["multi_level_stats"]["overall"],
            l1=metrics["multi_level_stats"]["l1"],
            l2=metrics["multi_level_stats"].get("l2"),
            l3=metrics["multi_level_stats"].get("l3"),
            quality_impact=metrics["quality_impact"],
            recommendations=metrics["recommendations"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache statistics: {str(e)}"
        )


@router.post("/invalidate")
async def invalidate_cache(request: CacheInvalidateRequest):
    """
    Invalidate cache entries.

    - **pattern**: Optional pattern to match cache keys
    - **levels**: Optional list of cache levels to clear ["l1", "l2", "l3"]
    """
    try:
        if request.levels:
            # Convert string levels to CacheLevel enum
            cache_levels = []
            for level in request.levels:
                if level.lower() == "l1":
                    cache_levels.append(CacheLevel.L1_MEMORY)
                elif level.lower() == "l2":
                    cache_levels.append(CacheLevel.L2_REDIS)
                elif level.lower() == "l3":
                    cache_levels.append(CacheLevel.L3_DISK)

            await multi_level_cache.clear(cache_levels)
            message = f"Cleared cache levels: {', '.join(request.levels)}"
        else:
            # Clear all levels
            await cached_chat_service.invalidate_cache(request.pattern)
            message = "All cache levels cleared"

            if request.pattern:
                message = f"Cleared cache entries matching pattern: {request.pattern}"

        return {"status": "success", "message": message}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.post("/optimize")
async def optimize_cache():
    """
    Optimize cache by cleaning expired entries and analyzing usage patterns.
    """
    try:
        await cached_chat_service.optimize_cache()

        # Get updated stats
        stats = await multi_level_cache.get_all_stats()

        return {
            "status": "success",
            "message": "Cache optimization completed",
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache optimization failed: {str(e)}"
        )


@router.post("/preload")
async def preload_queries(request: PreloadRequest):
    """
    Preload queries into cache for faster response times.
    """
    try:
        if not request.queries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No queries provided for preloading"
            )

        # Limit number of queries to prevent abuse
        if len(request.queries) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many queries. Maximum 50 allowed."
            )

        await cached_chat_service.preload_popular_queries(request.queries)

        return {
            "status": "success",
            "message": f"Preloaded {len(request.queries)} queries",
            "queries": request.queries
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache preload failed: {str(e)}"
        )


@router.get("/hot-queries")
async def get_hot_queries(top_n: int = Query(default=10, ge=1, le=100)):
    """
    Get the most frequently accessed queries.
    """
    try:
        hot_queries = await cached_chat_service.get_hot_queries(top_n)

        return {
            "hot_queries": hot_queries,
            "count": len(hot_queries)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hot queries: {str(e)}"
        )


@router.get("/hit-rate")
async def get_cache_hit_rate():
    """
    Get current cache hit rate and performance metrics.
    """
    try:
        stats = await multi_level_cache.get_all_stats()
        decorator_metrics = cache_metrics.to_dict()

        overall_stats = stats["overall"]

        return {
            "hit_rate": overall_stats["hit_rate"],
            "total_hits": overall_stats["hits"],
            "total_misses": overall_stats["misses"],
            "l1_hits": overall_stats["l1_hits"],
            "l2_hits": overall_stats["l2_hits"],
            "l3_hits": overall_stats["l3_hits"],
            "avg_response_time_ms": overall_stats["avg_response_time_ms"],
            "decorator_metrics": decorator_metrics,
            "cache_effectiveness": _calculate_effectiveness(overall_stats)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hit rate: {str(e)}"
        )


@router.get("/memory-usage")
async def get_cache_memory_usage():
    """
    Get memory usage statistics for all cache levels.
    """
    try:
        stats = await multi_level_cache.get_all_stats()

        memory_info = {
            "l1": {
                "used_bytes": stats["l1"]["memory_bytes"],
                "max_bytes": stats["l1"]["max_memory_bytes"],
                "usage_percent": stats["l1"]["memory_usage_percent"],
                "entries": stats["l1"]["size"],
                "max_entries": stats["l1"]["max_size"]
            }
        }

        if "l2" in stats:
            memory_info["l2"] = {
                "connected": stats["l2"].get("connected", False),
                "used_memory": stats["l2"].get("memory_used_human", "N/A"),
                "entries": stats["l2"].get("size", 0)
            }

        if "l3" in stats:
            memory_info["l3"] = {
                "used_bytes": stats["l3"]["total_size_bytes"],
                "used_mb": stats["l3"]["total_size_mb"],
                "max_bytes": stats["l3"]["max_size_bytes"],
                "usage_percent": stats["l3"]["usage_percent"],
                "entries": stats["l3"]["size"]
            }

        return memory_info

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory usage: {str(e)}"
        )


@router.post("/warmup")
async def warmup_cache():
    """
    Warm up cache with predefined common queries.
    """
    try:
        # Use the default warmup queries
        await cached_chat_service._warmup_cache()

        stats = await multi_level_cache.get_all_stats()

        return {
            "status": "success",
            "message": "Cache warmup completed",
            "warmed_queries": cached_chat_service.warmup_queries,
            "cache_size": {
                "l1": stats["l1"]["size"],
                "l2": stats.get("l2", {}).get("size", 0),
                "l3": stats.get("l3", {}).get("size", 0)
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache warmup failed: {str(e)}"
        )


def _calculate_effectiveness(stats: Dict[str, Any]) -> str:
    """Calculate cache effectiveness rating."""
    hit_rate = stats["hit_rate"]
    avg_response = stats["avg_response_time_ms"]

    if hit_rate >= 0.8 and avg_response < 50:
        return "excellent"
    elif hit_rate >= 0.6 and avg_response < 100:
        return "good"
    elif hit_rate >= 0.4 and avg_response < 200:
        return "moderate"
    else:
        return "needs_improvement"