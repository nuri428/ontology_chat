"""Metrics and monitoring endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from api.monitoring.metrics import metrics_collector
from api.cache import multi_level_cache
from api.services.cached_chat_service import cached_chat_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Get Prometheus metrics in text format."""
    # Update cache metrics before returning
    try:
        cache_stats = await multi_level_cache.get_all_stats()
        metrics_collector.update_cache_metrics(cache_stats)
    except Exception:
        pass  # Continue even if cache stats fail

    # Update quality score (mock for now - should come from actual quality calculation)
    try:
        # This should be replaced with actual quality score calculation
        quality_score = 0.949  # Mock A-grade score
        metrics_collector.update_quality_score(quality_score)
    except Exception:
        pass

    return metrics_collector.get_metrics()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Detailed health check endpoint."""
    try:
        # Check cache health
        cache_stats = await multi_level_cache.get_all_stats()
        cache_healthy = cache_stats["overall"]["hit_rate"] > 0.3

        # Check service components
        components = {
            "cache": {
                "healthy": cache_healthy,
                "hit_rate": cache_stats["overall"]["hit_rate"],
                "l1_connected": "l1" in cache_stats,
                "l2_connected": cache_stats.get("l2", {}).get("connected", False),
                "l3_connected": "l3" in cache_stats,
            },
            "llm": {
                "healthy": True,  # Should implement actual LLM health check
                "model": "llama3.1:8b"
            },
            "databases": {
                "neo4j_healthy": True,  # Should implement actual Neo4j health check
                "opensearch_healthy": True  # Should implement actual OpenSearch health check
            }
        }

        # Overall health
        overall_healthy = (
            cache_healthy and
            components["llm"]["healthy"] and
            components["databases"]["neo4j_healthy"] and
            components["databases"]["opensearch_healthy"]
        )

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": "2024-01-01T00:00:00Z",  # Should use actual timestamp
            "components": components,
            "version": "1.0.0",
            "uptime_seconds": 3600  # Should calculate actual uptime
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }


@router.get("/cache/prometheus")
async def get_cache_prometheus_metrics() -> Dict[str, Any]:
    """Get cache metrics in Prometheus format."""
    try:
        cache_stats = await multi_level_cache.get_all_stats()
        metrics_collector.update_cache_metrics(cache_stats)

        return {
            "status": "success",
            "metrics": cache_stats
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/quality/update")
async def update_quality_score(quality_score: float):
    """Update the A-grade quality score metric."""
    try:
        if 0 <= quality_score <= 1:
            metrics_collector.update_quality_score(quality_score)
            return {
                "status": "success",
                "quality_score": quality_score
            }
        else:
            return {
                "status": "error",
                "error": "Quality score must be between 0 and 1"
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/dashboard")
async def get_dashboard_metrics() -> Dict[str, Any]:
    """Get comprehensive metrics for dashboard display."""
    try:
        # Cache metrics
        cache_stats = await multi_level_cache.get_all_stats()

        # Service metrics
        service_metrics = await cached_chat_service.get_cache_metrics()

        # Combine all metrics
        dashboard_data = {
            "quality_score": 0.949,  # Should come from actual calculation
            "cache_stats": cache_stats,
            "service_metrics": service_metrics,
            "system_health": {
                "healthy": True,
                "degradation_level": 0,
                "uptime_seconds": 3600
            },
            "performance": {
                "avg_response_time_ms": cache_stats["overall"].get("avg_response_time_ms", 50),
                "request_rate": 10.0,  # Should calculate actual request rate
                "error_rate": 0.01
            }
        }

        return dashboard_data

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }