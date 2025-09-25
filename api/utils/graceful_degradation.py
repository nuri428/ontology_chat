"""Graceful degradation mechanisms for service resilience."""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union, List
from functools import wraps
import time

logger = logging.getLogger(__name__)


class ServiceLevel(Enum):
    """Service degradation levels."""
    FULL = "full"           # All features available
    DEGRADED = "degraded"   # Some features disabled
    MINIMAL = "minimal"     # Only core features
    EMERGENCY = "emergency" # Emergency mode only


@dataclass
class FallbackConfig:
    """Configuration for fallback mechanisms."""
    enable_cache_fallback: bool = True
    enable_default_response: bool = True
    enable_simplified_processing: bool = True
    cache_duration: float = 300.0  # 5 minutes
    timeout_threshold: float = 5.0
    error_rate_threshold: float = 0.5  # 50% error rate


class GracefulDegradationManager:
    """Manager for graceful service degradation."""

    def __init__(self):
        self._service_levels: Dict[str, ServiceLevel] = {}
        self._fallback_cache: Dict[str, Dict] = {}
        self._service_metrics: Dict[str, Dict] = {}
        self._degradation_rules: Dict[str, Callable] = {}

    def register_service(
        self,
        service_name: str,
        initial_level: ServiceLevel = ServiceLevel.FULL
    ):
        """Register a service for degradation management."""
        self._service_levels[service_name] = initial_level
        self._service_metrics[service_name] = {
            "total_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "last_success": time.time(),
            "consecutive_failures": 0
        }
        logger.info(f"Registered service '{service_name}' at level {initial_level.value}")

    def set_service_level(self, service_name: str, level: ServiceLevel):
        """Manually set service degradation level."""
        old_level = self._service_levels.get(service_name, ServiceLevel.FULL)
        self._service_levels[service_name] = level

        if old_level != level:
            logger.warning(
                f"Service '{service_name}' degradation level changed: "
                f"{old_level.value} -> {level.value}"
            )

    def get_service_level(self, service_name: str) -> ServiceLevel:
        """Get current service level."""
        return self._service_levels.get(service_name, ServiceLevel.FULL)

    def update_service_metrics(
        self,
        service_name: str,
        success: bool,
        response_time: float
    ):
        """Update service metrics and potentially adjust degradation level."""
        if service_name not in self._service_metrics:
            self.register_service(service_name)

        metrics = self._service_metrics[service_name]
        metrics["total_requests"] += 1

        if success:
            metrics["last_success"] = time.time()
            metrics["consecutive_failures"] = 0
            # Update average response time (simple moving average)
            metrics["avg_response_time"] = (
                (metrics["avg_response_time"] * (metrics["total_requests"] - 1) + response_time) /
                metrics["total_requests"]
            )
        else:
            metrics["failed_requests"] += 1
            metrics["consecutive_failures"] += 1

        # Auto-adjust service level based on metrics
        self._auto_adjust_service_level(service_name)

    def _auto_adjust_service_level(self, service_name: str):
        """Automatically adjust service level based on metrics."""
        metrics = self._service_metrics[service_name]
        current_level = self._service_levels[service_name]

        # Calculate error rate
        error_rate = (
            metrics["failed_requests"] / metrics["total_requests"]
            if metrics["total_requests"] > 0 else 0
        )

        # Determine new level based on metrics
        if metrics["consecutive_failures"] >= 10:
            new_level = ServiceLevel.EMERGENCY
        elif error_rate > 0.5 or metrics["avg_response_time"] > 10.0:
            new_level = ServiceLevel.MINIMAL
        elif error_rate > 0.2 or metrics["avg_response_time"] > 5.0:
            new_level = ServiceLevel.DEGRADED
        elif error_rate < 0.1 and metrics["avg_response_time"] < 2.0:
            new_level = ServiceLevel.FULL
        else:
            new_level = current_level

        if new_level != current_level:
            self.set_service_level(service_name, new_level)

    def cache_result(self, key: str, result: Any, ttl: float = 300.0):
        """Cache a result for fallback use."""
        self._fallback_cache[key] = {
            "result": result,
            "timestamp": time.time(),
            "ttl": ttl
        }

    def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result if available and not expired."""
        if key not in self._fallback_cache:
            return None

        cached = self._fallback_cache[key]
        if time.time() - cached["timestamp"] > cached["ttl"]:
            del self._fallback_cache[key]
            return None

        return cached["result"]

    def get_degradation_status(self) -> Dict[str, Any]:
        """Get overall degradation status."""
        return {
            "services": {
                name: {
                    "level": level.value,
                    "metrics": self._service_metrics.get(name, {})
                }
                for name, level in self._service_levels.items()
            },
            "cache_size": len(self._fallback_cache),
            "degraded_services": [
                name for name, level in self._service_levels.items()
                if level != ServiceLevel.FULL
            ]
        }


# Global degradation manager
degradation_manager = GracefulDegradationManager()


def graceful_degradation(
    service_name: str,
    fallback_config: Optional[FallbackConfig] = None
):
    """Decorator for graceful service degradation."""
    config = fallback_config or FallbackConfig()

    def decorator(func: Callable):
        # Register service if not already registered
        if service_name not in degradation_manager._service_levels:
            degradation_manager.register_service(service_name)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            cache_key = f"{service_name}_{hash(str(args))}{hash(str(kwargs))}"

            try:
                # Check service level and potentially return degraded response
                service_level = degradation_manager.get_service_level(service_name)

                if service_level == ServiceLevel.EMERGENCY:
                    # Try cache first, then minimal response
                    if config.enable_cache_fallback:
                        cached = degradation_manager.get_cached_result(cache_key)
                        if cached is not None:
                            logger.info(f"Returning cached result for {service_name} (EMERGENCY)")
                            return cached

                    # Return emergency fallback
                    return await _get_emergency_fallback(service_name, func, args, kwargs)

                elif service_level == ServiceLevel.MINIMAL:
                    # Try cache, then simplified processing
                    if config.enable_cache_fallback:
                        cached = degradation_manager.get_cached_result(cache_key)
                        if cached is not None:
                            logger.info(f"Returning cached result for {service_name} (MINIMAL)")
                            return cached

                    return await _get_minimal_response(service_name, func, args, kwargs)

                elif service_level == ServiceLevel.DEGRADED:
                    # Try full function with shorter timeout, fallback to cache
                    try:
                        result = await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=config.timeout_threshold
                        )

                        # Cache successful result
                        degradation_manager.cache_result(cache_key, result, config.cache_duration)

                        response_time = time.time() - start_time
                        degradation_manager.update_service_metrics(service_name, True, response_time)

                        return result

                    except (asyncio.TimeoutError, Exception):
                        # Fall back to cache or default
                        if config.enable_cache_fallback:
                            cached = degradation_manager.get_cached_result(cache_key)
                            if cached is not None:
                                logger.warning(f"Using cached fallback for {service_name}")
                                return cached

                        return await _get_degraded_fallback(service_name, func, args, kwargs)

                # FULL service level - normal operation
                result = await func(*args, **kwargs)

                # Cache successful result
                if config.enable_cache_fallback:
                    degradation_manager.cache_result(cache_key, result, config.cache_duration)

                response_time = time.time() - start_time
                degradation_manager.update_service_metrics(service_name, True, response_time)

                return result

            except Exception as e:
                response_time = time.time() - start_time
                degradation_manager.update_service_metrics(service_name, False, response_time)

                logger.error(f"Service {service_name} failed: {e}")

                # Try fallback mechanisms
                if config.enable_cache_fallback:
                    cached = degradation_manager.get_cached_result(cache_key)
                    if cached is not None:
                        logger.info(f"Using cached fallback for failed {service_name}")
                        return cached

                if config.enable_default_response:
                    return await _get_default_response(service_name, func, args, kwargs)

                # Re-raise if no fallback available
                raise

        return wrapper
    return decorator


async def _get_emergency_fallback(service_name: str, func: Callable, args: tuple, kwargs: dict) -> Any:
    """Get emergency fallback response."""
    logger.warning(f"Service {service_name} in EMERGENCY mode")

    # Service-specific emergency responses
    if "chat" in service_name.lower():
        return {
            "context": ["System temporarily unavailable. Please try again later."],
            "sources": [],
            "quality_score": 0.5,
            "degraded": True,
            "message": "Service is experiencing issues. Limited functionality available."
        }
    elif "search" in service_name.lower():
        return []
    elif "llm" in service_name.lower():
        return "Service temporarily unavailable"
    else:
        return {"error": "Service temporarily unavailable", "degraded": True}


async def _get_minimal_response(service_name: str, func: Callable, args: tuple, kwargs: dict) -> Any:
    """Get minimal functionality response."""
    logger.info(f"Service {service_name} in MINIMAL mode")

    # Service-specific minimal responses
    if "chat" in service_name.lower():
        # Basic keyword extraction without LLM
        query = args[0] if args else kwargs.get('query', '')
        basic_keywords = ' '.join(word for word in query.split() if len(word) > 3)

        return {
            "context": [f"Basic search results for: {basic_keywords}"],
            "sources": ["simplified"],
            "quality_score": 0.6,
            "degraded": True,
            "message": "Running in simplified mode"
        }
    elif "search" in service_name.lower():
        return [{"title": "Minimal search result", "content": "Simplified result"}]
    else:
        return {"result": "minimal", "degraded": True}


async def _get_degraded_fallback(service_name: str, func: Callable, args: tuple, kwargs: dict) -> Any:
    """Get degraded functionality response."""
    logger.info(f"Service {service_name} using degraded fallback")

    # Simplified version of the operation
    if "chat" in service_name.lower():
        return {
            "context": ["Simplified response due to service degradation"],
            "sources": ["degraded"],
            "quality_score": 0.7,
            "degraded": True
        }
    else:
        return {"result": "degraded", "degraded": True}


async def _get_default_response(service_name: str, func: Callable, args: tuple, kwargs: dict) -> Any:
    """Get default response when all else fails."""
    logger.warning(f"Using default response for {service_name}")

    return {
        "error": f"Service {service_name} is currently unavailable",
        "degraded": True,
        "retry_after": 30
    }


# Utility functions for monitoring and management
def get_system_health() -> Dict[str, Any]:
    """Get overall system health status."""
    status = degradation_manager.get_degradation_status()

    degraded_count = len(status["degraded_services"])
    total_services = len(status["services"])

    if degraded_count == 0:
        health_status = "healthy"
    elif degraded_count / total_services < 0.3:
        health_status = "degraded"
    else:
        health_status = "critical"

    return {
        "status": health_status,
        "degraded_services_count": degraded_count,
        "total_services": total_services,
        "degradation_percentage": degraded_count / total_services if total_services > 0 else 0,
        **status
    }


async def recover_service(service_name: str) -> bool:
    """Attempt to recover a degraded service."""
    current_level = degradation_manager.get_service_level(service_name)

    if current_level == ServiceLevel.FULL:
        return True

    logger.info(f"Attempting to recover service: {service_name}")

    # Reset metrics and try to restore service
    degradation_manager._service_metrics[service_name] = {
        "total_requests": 0,
        "failed_requests": 0,
        "avg_response_time": 0.0,
        "last_success": time.time(),
        "consecutive_failures": 0
    }

    # Gradually increase service level
    if current_level == ServiceLevel.EMERGENCY:
        degradation_manager.set_service_level(service_name, ServiceLevel.MINIMAL)
    elif current_level == ServiceLevel.MINIMAL:
        degradation_manager.set_service_level(service_name, ServiceLevel.DEGRADED)
    elif current_level == ServiceLevel.DEGRADED:
        degradation_manager.set_service_level(service_name, ServiceLevel.FULL)

    return True


def force_degrade_service(service_name: str, level: ServiceLevel):
    """Force a service to a specific degradation level."""
    logger.warning(f"Forcing service {service_name} to level {level.value}")
    degradation_manager.set_service_level(service_name, level)