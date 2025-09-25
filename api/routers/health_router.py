"""Health check and monitoring endpoints with enhanced error handling status."""

import asyncio
import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from api.utils.circuit_breaker import circuit_breaker_manager
from api.utils.graceful_degradation import degradation_manager, get_system_health
from api.services.enhanced_chat_service import enhanced_chat_service

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: float
    uptime: float
    version: str = "1.0.0"


class DetailedHealthResponse(BaseModel):
    """Detailed health response model."""
    status: str
    timestamp: float
    services: Dict[str, Any]
    circuit_breakers: Dict[str, Any]
    degradation_status: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    system_info: Dict[str, Any]


# Track service startup time
service_start_time = time.time()


@router.get("/", response_model=HealthResponse)
async def basic_health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=time.time(),
        uptime=time.time() - service_start_time
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """Detailed health check with all service components."""
    try:
        # Get comprehensive health status
        health_status = await enhanced_chat_service.get_health_status()

        # Get system health
        system_health = get_system_health()

        # Test critical services
        service_tests = await _test_critical_services()

        # Determine overall status
        overall_status = _determine_overall_status(
            health_status,
            system_health,
            service_tests
        )

        return DetailedHealthResponse(
            status=overall_status,
            timestamp=time.time(),
            services=service_tests,
            circuit_breakers=health_status["circuit_breakers"],
            degradation_status=health_status["degradation_status"],
            performance_metrics=health_status["performance_metrics"],
            system_info={
                "uptime": time.time() - service_start_time,
                "system_health": system_health,
                "version": "1.0.0"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/ready")
async def readiness_check():
    """Kubernetes-style readiness check."""
    try:
        # Test if critical services are responsive
        test_results = await _test_critical_services()

        # Check if any critical services are down
        critical_failures = [
            name for name, result in test_results.items()
            if not result.get("healthy", False) and result.get("critical", False)
        ]

        if critical_failures:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "ready": False,
                    "message": f"Critical services not ready: {critical_failures}",
                    "timestamp": time.time()
                }
            )

        return {
            "ready": True,
            "timestamp": time.time(),
            "services": test_results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "ready": False,
                "error": str(e),
                "timestamp": time.time()
            }
        )


@router.get("/live")
async def liveness_check():
    """Kubernetes-style liveness check."""
    try:
        # Simple liveness check - just verify the service is responding
        return {
            "alive": True,
            "timestamp": time.time(),
            "uptime": time.time() - service_start_time
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "alive": False,
                "error": str(e),
                "timestamp": time.time()
            }
        )


@router.get("/circuit-breakers")
async def circuit_breaker_status():
    """Get status of all circuit breakers."""
    try:
        metrics = circuit_breaker_manager.get_all_metrics()
        unhealthy_circuits = circuit_breaker_manager.get_unhealthy_circuits()

        return {
            "circuit_breakers": metrics,
            "unhealthy_circuits": unhealthy_circuits,
            "total_circuits": len(metrics),
            "healthy_circuits": len(metrics) - len(unhealthy_circuits),
            "timestamp": time.time()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get circuit breaker status: {str(e)}"
        )


@router.get("/degradation")
async def degradation_status():
    """Get service degradation status."""
    try:
        status = degradation_manager.get_degradation_status()
        system_health = get_system_health()

        return {
            "degradation_status": status,
            "system_health": system_health,
            "timestamp": time.time()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get degradation status: {str(e)}"
        )


@router.post("/reset")
async def reset_error_handling():
    """Reset all error handling mechanisms (for maintenance)."""
    try:
        await enhanced_chat_service.reset_error_handling()

        return {
            "message": "All error handling mechanisms reset successfully",
            "timestamp": time.time(),
            "reset_components": [
                "circuit_breakers",
                "degradation_levels",
                "retry_counters"
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset error handling: {str(e)}"
        )


@router.get("/performance")
async def performance_metrics():
    """Get performance metrics and statistics."""
    try:
        health_status = await enhanced_chat_service.get_health_status()
        performance = health_status.get("performance_metrics", {})

        # Calculate additional metrics
        success_rate = (
            performance.get("successful_requests", 0) /
            max(performance.get("total_requests", 1), 1)
        )

        failure_rate = (
            performance.get("failed_requests", 0) /
            max(performance.get("total_requests", 1), 1)
        )

        return {
            "performance_metrics": performance,
            "calculated_metrics": {
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "uptime": time.time() - service_start_time,
                "requests_per_minute": performance.get("total_requests", 0) / max((time.time() - service_start_time) / 60, 1)
            },
            "circuit_breaker_stats": circuit_breaker_manager.get_all_metrics(),
            "timestamp": time.time()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


async def _test_critical_services() -> Dict[str, Dict[str, Any]]:
    """Test critical services and return their status."""
    services_to_test = {
        "enhanced_chat_service": {
            "test_func": _test_chat_service,
            "critical": True,
            "timeout": 5.0
        },
        "neo4j_connection": {
            "test_func": _test_neo4j,
            "critical": True,
            "timeout": 3.0
        },
        "opensearch_connection": {
            "test_func": _test_opensearch,
            "critical": True,
            "timeout": 3.0
        },
        "llm_service": {
            "test_func": _test_llm,
            "critical": False,
            "timeout": 10.0
        }
    }

    results = {}

    for service_name, config in services_to_test.items():
        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                config["test_func"](),
                timeout=config["timeout"]
            )
            response_time = time.time() - start_time

            results[service_name] = {
                "healthy": True,
                "response_time": response_time,
                "critical": config["critical"],
                "result": result
            }

        except asyncio.TimeoutError:
            results[service_name] = {
                "healthy": False,
                "error": "timeout",
                "critical": config["critical"],
                "timeout": config["timeout"]
            }

        except Exception as e:
            results[service_name] = {
                "healthy": False,
                "error": str(e),
                "critical": config["critical"]
            }

    return results


async def _test_chat_service() -> Dict[str, Any]:
    """Test chat service basic functionality."""
    try:
        # Test with a simple query
        response = await enhanced_chat_service.get_context("test health check")
        return {
            "status": "ok",
            "context_count": len(response.get("context", [])),
            "quality_score": response.get("metadata", {}).get("quality_score", 0)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _test_neo4j() -> Dict[str, Any]:
    """Test Neo4j connection."""
    try:
        # Simple connection test
        result = await enhanced_chat_service._safe_neo4j_search("test", "health check")
        return {
            "status": "ok",
            "connection": "active",
            "result_count": len(result) if result else 0
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _test_opensearch() -> Dict[str, Any]:
    """Test OpenSearch connection."""
    try:
        # Simple connection test
        result = await enhanced_chat_service._safe_opensearch_search("health check", "test")
        return {
            "status": "ok",
            "connection": "active",
            "result_count": len(result) if result else 0
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _test_llm() -> Dict[str, Any]:
    """Test LLM service."""
    try:
        if enhanced_chat_service.ollama_llm:
            keywords = await enhanced_chat_service._safe_extract_keywords("test query")
            return {
                "status": "ok",
                "llm_available": True,
                "keywords_extracted": bool(keywords)
            }
        else:
            return {
                "status": "degraded",
                "llm_available": False,
                "fallback_active": True
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _determine_overall_status(
    health_status: Dict[str, Any],
    system_health: Dict[str, Any],
    service_tests: Dict[str, Any]
) -> str:
    """Determine overall system status based on all health indicators."""
    # Check for critical service failures
    critical_failures = [
        name for name, result in service_tests.items()
        if not result.get("healthy", False) and result.get("critical", False)
    ]

    if critical_failures:
        return "critical"

    # Check system health
    if system_health.get("status") == "critical":
        return "critical"
    elif system_health.get("status") == "degraded":
        return "degraded"

    # Check for any open circuit breakers
    cb_metrics = health_status.get("circuit_breakers", {})
    open_circuits = [name for name, metrics in cb_metrics.items() if metrics.get("state") == "open"]

    if open_circuits:
        return "degraded"

    # Check degradation status
    degraded_services = health_status.get("degradation_status", {}).get("degraded_services", [])
    if degraded_services:
        return "degraded"

    return "healthy"