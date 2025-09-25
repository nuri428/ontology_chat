"""Enhanced utilities for error handling and system resilience."""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    circuit_breaker,
    sync_circuit_breaker,
    circuit_breaker_manager
)

from .retry_handler import (
    RetryHandler,
    RetryConfig,
    BackoffStrategy,
    retry_async,
    retry_sync,
    retry_on_connection_error,
    retry_on_http_error,
    retry_database_operation,
    retry_until_success
)

from .graceful_degradation import (
    GracefulDegradationManager,
    ServiceLevel,
    FallbackConfig,
    graceful_degradation,
    degradation_manager,
    get_system_health,
    recover_service,
    force_degrade_service
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "circuit_breaker",
    "sync_circuit_breaker",
    "circuit_breaker_manager",

    # Retry Handler
    "RetryHandler",
    "RetryConfig",
    "BackoffStrategy",
    "retry_async",
    "retry_sync",
    "retry_on_connection_error",
    "retry_on_http_error",
    "retry_database_operation",
    "retry_until_success",

    # Graceful Degradation
    "GracefulDegradationManager",
    "ServiceLevel",
    "FallbackConfig",
    "graceful_degradation",
    "degradation_manager",
    "get_system_health",
    "recover_service",
    "force_degrade_service"
]