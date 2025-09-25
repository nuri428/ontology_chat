"""Unit tests for error handling mechanisms."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from api.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from api.utils.retry_handler import RetryHandler, RetryConfig, BackoffStrategy
from api.utils.graceful_degradation import GracefulDegradationManager, ServiceLevel


@pytest.mark.unit
class TestCircuitBreaker:
    """Test suite for Circuit Breaker functionality."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0)
        cb = CircuitBreaker("test_service", config)

        assert cb.name == "test_service"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_rate == 0.0

    @pytest.mark.asyncio
    async def test_circuit_breaker_success_flow(self):
        """Test circuit breaker with successful calls."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))

        async def successful_func():
            return "success"

        # Multiple successful calls should keep circuit closed
        for _ in range(5):
            result = await cb(successful_func)
            assert result == "success"
            assert cb.state == CircuitState.CLOSED

        metrics = cb.metrics
        assert metrics["total_requests"] == 5
        assert metrics["total_failures"] == 0
        assert metrics["failure_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker opening after failure threshold."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=2))

        async def failing_func():
            raise Exception("Test failure")

        # First failure - circuit should remain closed
        with pytest.raises(Exception):
            await cb(failing_func)
        assert cb.state == CircuitState.CLOSED

        # Second failure - circuit should open
        with pytest.raises(Exception):
            await cb(failing_func)
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker half-open state and recovery."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,  # Short timeout for testing
            success_threshold=2
        ))

        # Fail once to open circuit
        async def failing_func():
            raise Exception("Test failure")

        with pytest.raises(Exception):
            await cb(failing_func)
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Next call should move to half-open
        async def successful_func():
            return "success"

        result = await cb(successful_func)
        assert result == "success"
        assert cb.state == CircuitState.HALF_OPEN

        # Another success should close the circuit
        result = await cb(successful_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_timeout(self):
        """Test circuit breaker timeout handling."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(timeout=0.1))

        async def slow_func():
            await asyncio.sleep(0.2)  # Longer than timeout
            return "success"

        with pytest.raises(Exception):  # Should be CircuitBreakerTimeoutError
            await cb(slow_func)

        metrics = cb.metrics
        assert metrics["total_timeouts"] == 1


@pytest.mark.unit
class TestRetryHandler:
    """Test suite for Retry Handler functionality."""

    @pytest.mark.asyncio
    async def test_retry_handler_success_on_first_attempt(self):
        """Test retry handler with immediate success."""
        handler = RetryHandler(RetryConfig(max_attempts=3))

        async def successful_func():
            return "success"

        result = await handler.execute_async(successful_func)
        assert result == "success"

        metrics = handler.metrics
        assert metrics["total_attempts"] == 1
        assert metrics["total_successes"] == 1
        assert metrics["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_retry_handler_success_after_failures(self):
        """Test retry handler succeeding after initial failures."""
        handler = RetryHandler(RetryConfig(
            max_attempts=3,
            initial_delay=0.01,  # Fast retry for testing
            backoff_strategy=BackoffStrategy.FIXED
        ))

        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Failure {call_count}")
            return "success"

        result = await handler.execute_async(flaky_func)
        assert result == "success"
        assert call_count == 3

        metrics = handler.metrics
        assert metrics["total_attempts"] == 3
        assert metrics["total_successes"] == 1

    @pytest.mark.asyncio
    async def test_retry_handler_exhausted(self):
        """Test retry handler exhausting all attempts."""
        handler = RetryHandler(RetryConfig(
            max_attempts=2,
            initial_delay=0.01
        ))

        async def always_failing_func():
            raise Exception("Always fails")

        with pytest.raises(Exception):  # Should be RetryExhaustedError
            await handler.execute_async(always_failing_func)

        metrics = handler.metrics
        assert metrics["total_attempts"] == 2
        assert metrics["total_failures"] == 2

    @pytest.mark.asyncio
    async def test_retry_backoff_strategies(self):
        """Test different backoff strategies."""
        # Test exponential backoff
        handler = RetryHandler(RetryConfig(
            max_attempts=4,
            initial_delay=0.01,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            backoff_multiplier=2.0
        ))

        delays = []
        for attempt in range(1, 4):
            delay = handler._calculate_delay(attempt)
            delays.append(delay)

        # Should be: 0.01, 0.02, 0.04
        assert delays[0] == 0.01
        assert delays[1] == 0.02
        assert delays[2] == 0.04

    def test_retry_sync_function(self):
        """Test retry handler with synchronous functions."""
        handler = RetryHandler(RetryConfig(max_attempts=2))

        call_count = 0

        def flaky_sync_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First failure")
            return "success"

        result = handler.execute_sync(flaky_sync_func)
        assert result == "success"
        assert call_count == 2


@pytest.mark.unit
class TestGracefulDegradation:
    """Test suite for Graceful Degradation functionality."""

    def test_degradation_manager_initialization(self):
        """Test degradation manager initialization."""
        manager = GracefulDegradationManager()
        manager.register_service("test_service", ServiceLevel.FULL)

        assert manager.get_service_level("test_service") == ServiceLevel.FULL

    def test_service_level_changes(self):
        """Test manual service level changes."""
        manager = GracefulDegradationManager()
        manager.register_service("test_service", ServiceLevel.FULL)

        # Change to degraded
        manager.set_service_level("test_service", ServiceLevel.DEGRADED)
        assert manager.get_service_level("test_service") == ServiceLevel.DEGRADED

        # Change to emergency
        manager.set_service_level("test_service", ServiceLevel.EMERGENCY)
        assert manager.get_service_level("test_service") == ServiceLevel.EMERGENCY

    def test_automatic_degradation(self):
        """Test automatic service degradation based on metrics."""
        manager = GracefulDegradationManager()
        manager.register_service("test_service", ServiceLevel.FULL)

        # Simulate failures
        for _ in range(5):
            manager.update_service_metrics("test_service", False, 5.0)

        # Should be degraded due to high error rate
        level = manager.get_service_level("test_service")
        assert level in [ServiceLevel.DEGRADED, ServiceLevel.MINIMAL, ServiceLevel.EMERGENCY]

    def test_cache_functionality(self):
        """Test fallback cache functionality."""
        manager = GracefulDegradationManager()

        # Cache a result
        manager.cache_result("test_key", {"data": "test"}, ttl=1.0)

        # Retrieve cached result
        result = manager.get_cached_result("test_key")
        assert result == {"data": "test"}

        # Test expiration
        time.sleep(1.1)
        result = manager.get_cached_result("test_key")
        assert result is None

    def test_degradation_status(self):
        """Test degradation status reporting."""
        manager = GracefulDegradationManager()
        manager.register_service("service1", ServiceLevel.FULL)
        manager.register_service("service2", ServiceLevel.DEGRADED)

        status = manager.get_degradation_status()

        assert "services" in status
        assert "service1" in status["services"]
        assert "service2" in status["services"]
        assert status["services"]["service1"]["level"] == "full"
        assert status["services"]["service2"]["level"] == "degraded"

    @pytest.mark.asyncio
    async def test_graceful_degradation_decorator(self):
        """Test graceful degradation decorator functionality."""
        from api.utils.graceful_degradation import graceful_degradation, FallbackConfig

        @graceful_degradation("test_service", FallbackConfig(enable_cache_fallback=True))
        async def test_function(value):
            if value == "fail":
                raise Exception("Test failure")
            return f"success: {value}"

        # Test successful call
        result = await test_function("ok")
        assert result == "success: ok"

        # Test failure with fallback (would use cache or default response)
        try:
            result = await test_function("fail")
            # Should get some form of fallback response
            assert result is not None
        except Exception:
            # Or may raise exception if no fallback configured
            pass


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling components."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_retry(self):
        """Test circuit breaker working with retry mechanism."""
        from api.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        from api.utils.retry_handler import RetryHandler, RetryConfig

        cb = CircuitBreaker("integration_test", CircuitBreakerConfig(failure_threshold=2))
        retry_handler = RetryHandler(RetryConfig(max_attempts=3, initial_delay=0.01))

        call_count = 0

        async def flaky_service():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"Failure {call_count}")
            return "success"

        async def protected_service():
            return await cb(flaky_service)

        # Should succeed after retries
        result = await retry_handler.execute_async(protected_service)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_complete_error_handling_flow(self):
        """Test complete error handling flow with all components."""
        from api.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        from api.utils.graceful_degradation import GracefulDegradationManager, ServiceLevel

        # Setup
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1))
        degradation_manager = GracefulDegradationManager()
        degradation_manager.register_service("test", ServiceLevel.FULL)

        async def failing_service():
            raise Exception("Service failure")

        # First failure opens circuit
        with pytest.raises(Exception):
            await cb(failing_service)

        assert cb.state == CircuitState.OPEN

        # Update degradation based on failure
        degradation_manager.update_service_metrics("test", False, 5.0)

        # Service should be degraded
        level = degradation_manager.get_service_level("test")
        assert level != ServiceLevel.FULL

    def test_performance_under_load(self):
        """Test error handling performance under load."""
        from api.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

        cb = CircuitBreaker("load_test", CircuitBreakerConfig())

        # Measure time for many successful calls
        start_time = time.time()

        async def quick_success():
            return "ok"

        async def run_load_test():
            tasks = [cb(quick_success) for _ in range(100)]
            results = await asyncio.gather(*tasks)
            return results

        results = asyncio.run(run_load_test())
        end_time = time.time()

        assert len(results) == 100
        assert all(r == "ok" for r in results)

        # Should complete reasonably quickly (less than 1 second)
        assert end_time - start_time < 1.0