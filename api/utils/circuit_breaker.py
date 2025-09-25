"""Circuit Breaker pattern implementation for resilient service calls."""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, Union
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Number of failures to open circuit
    recovery_timeout: float = 60.0      # Seconds to wait before trying again
    success_threshold: int = 3          # Successes needed to close circuit in half-open
    timeout: float = 30.0              # Request timeout in seconds
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreakerTimeoutError(Exception):
    """Raised when request times out."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation with async support.

    Prevents cascading failures by failing fast when a service is unavailable.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

        # Metrics
        self._total_requests = 0
        self._total_failures = 0
        self._total_timeouts = 0
        self._total_circuit_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def failure_rate(self) -> float:
        """Get failure rate (0.0 to 1.0)."""
        if self._total_requests == 0:
            return 0.0
        return self._total_failures / self._total_requests

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "total_requests": self._total_requests,
            "total_failures": self._total_failures,
            "total_timeouts": self._total_timeouts,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_rate": self.failure_rate,
            "circuit_open_calls": self._total_circuit_open_calls,
            "last_failure_time": self._last_failure_time
        }

    async def __call__(self, func: Callable) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            # Check if we can proceed
            if not await self._can_proceed():
                self._total_circuit_open_calls += 1
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Last failure: {self._last_failure_time}"
                )

        self._total_requests += 1

        try:
            # Execute with timeout
            result = await asyncio.wait_for(func(), timeout=self.config.timeout)

            # Handle success
            await self._on_success()
            return result

        except asyncio.TimeoutError:
            self._total_timeouts += 1
            await self._on_failure()
            raise CircuitBreakerTimeoutError(
                f"Request timed out after {self.config.timeout}s"
            )

        except self.config.expected_exception as e:
            await self._on_failure()
            raise e

    async def _can_proceed(self) -> bool:
        """Check if request can proceed based on circuit state."""
        if self._state == CircuitState.CLOSED:
            return True

        elif self._state == CircuitState.OPEN:
            # Check if we should move to half-open
            if (self._last_failure_time and
                time.time() - self._last_failure_time >= self.config.recovery_timeout):
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(f"Circuit breaker '{self.name}' moving to HALF_OPEN")
                return True
            return False

        else:  # HALF_OPEN
            return True

    async def _on_success(self):
        """Handle successful request."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"Circuit breaker '{self.name}' CLOSED after recovery")
            elif self._state == CircuitState.CLOSED:
                self._failure_count = max(0, self._failure_count - 1)

    async def _on_failure(self):
        """Handle failed request."""
        async with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit breaker '{self.name}' OPENED after "
                        f"{self._failure_count} failures"
                    )
            elif self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' reopened during half-open test")

    async def reset(self):
        """Manually reset circuit breaker to closed state."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""

    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

    def get_circuit_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create circuit breaker by name."""
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(name, config)
        return self._circuit_breakers[name]

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers."""
        return {
            name: cb.metrics
            for name, cb in self._circuit_breakers.items()
        }

    async def reset_all(self):
        """Reset all circuit breakers."""
        for cb in self._circuit_breakers.values():
            await cb.reset()

    def get_unhealthy_circuits(self) -> list[str]:
        """Get list of circuit breakers that are open."""
        return [
            name for name, cb in self._circuit_breakers.items()
            if cb.state == CircuitState.OPEN
        ]


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Decorator for applying circuit breaker to async functions."""
    def decorator(func: Callable):
        cb = circuit_breaker_manager.get_circuit_breaker(name, config)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            async def execute():
                return await func(*args, **kwargs)

            return await cb(execute)

        return wrapper
    return decorator


def sync_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Decorator for applying circuit breaker to sync functions."""
    def decorator(func: Callable):
        cb = circuit_breaker_manager.get_circuit_breaker(name, config)

        @wraps(func)
        def wrapper(*args, **kwargs):
            async def execute():
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, func, *args, **kwargs)

            # Run the circuit breaker logic
            return asyncio.run(cb(execute))

        return wrapper
    return decorator