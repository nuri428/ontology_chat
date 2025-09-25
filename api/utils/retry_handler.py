"""Advanced retry mechanisms with backoff strategies."""

import asyncio
import random
import time
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, Type, Union, List
from functools import wraps
import inspect

logger = logging.getLogger(__name__)


class BackoffStrategy(Enum):
    """Available backoff strategies."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


@dataclass
class RetryConfig:
    """Configuration for retry mechanism."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter_max: float = 0.1
    retryable_exceptions: tuple = (Exception,)
    non_retryable_exceptions: tuple = ()


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Retry exhausted after {attempts} attempts. "
            f"Last error: {last_exception}"
        )


class RetryHandler:
    """Advanced retry handler with multiple backoff strategies."""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._total_attempts = 0
        self._total_successes = 0
        self._total_failures = 0

    @property
    def success_rate(self) -> float:
        """Get success rate (0.0 to 1.0)."""
        if self._total_attempts == 0:
            return 0.0
        return self._total_successes / self._total_attempts

    @property
    def metrics(self) -> dict:
        """Get retry metrics."""
        return {
            "total_attempts": self._total_attempts,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "success_rate": self.success_rate
        }

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt using configured strategy."""
        if self.config.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.config.initial_delay

        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.config.initial_delay * attempt

        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.config.initial_delay * (self.config.backoff_multiplier ** (attempt - 1))

        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER:
            base_delay = self.config.initial_delay * (self.config.backoff_multiplier ** (attempt - 1))
            jitter = random.uniform(-self.config.jitter_max, self.config.jitter_max)
            delay = base_delay * (1 + jitter)

        else:
            delay = self.config.initial_delay

        return min(delay, self.config.max_delay)

    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if we should retry based on exception and attempt count."""
        # Check if we've exceeded max attempts
        if attempt >= self.config.max_attempts:
            return False

        # Check if exception is in non-retryable list
        if isinstance(exception, self.config.non_retryable_exceptions):
            logger.debug(f"Not retrying due to non-retryable exception: {type(exception).__name__}")
            return False

        # Check if exception is retryable
        if not isinstance(exception, self.config.retryable_exceptions):
            logger.debug(f"Not retrying due to non-retryable exception: {type(exception).__name__}")
            return False

        return True

    async def execute_async(self, func: Callable) -> Any:
        """Execute async function with retry logic."""
        last_exception = None

        for attempt in range(1, self.config.max_attempts + 1):
            self._total_attempts += 1

            try:
                logger.debug(f"Attempting operation (attempt {attempt}/{self.config.max_attempts})")
                result = await func()
                self._total_successes += 1

                if attempt > 1:
                    logger.info(f"Operation succeeded after {attempt} attempts")

                return result

            except Exception as e:
                last_exception = e
                self._total_failures += 1

                logger.warning(
                    f"Attempt {attempt} failed: {type(e).__name__}: {str(e)}"
                )

                if not self._should_retry(e, attempt):
                    break

                if attempt < self.config.max_attempts:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)

        # All retries exhausted
        raise RetryExhaustedError(attempt, last_exception)

    def execute_sync(self, func: Callable) -> Any:
        """Execute sync function with retry logic."""
        last_exception = None

        for attempt in range(1, self.config.max_attempts + 1):
            self._total_attempts += 1

            try:
                logger.debug(f"Attempting operation (attempt {attempt}/{self.config.max_attempts})")
                result = func()
                self._total_successes += 1

                if attempt > 1:
                    logger.info(f"Operation succeeded after {attempt} attempts")

                return result

            except Exception as e:
                last_exception = e
                self._total_failures += 1

                logger.warning(
                    f"Attempt {attempt} failed: {type(e).__name__}: {str(e)}"
                )

                if not self._should_retry(e, attempt):
                    break

                if attempt < self.config.max_attempts:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)

        # All retries exhausted
        raise RetryExhaustedError(attempt, last_exception)


def retry_async(config: Optional[RetryConfig] = None):
    """Decorator for async functions with retry logic."""
    def decorator(func: Callable):
        handler = RetryHandler(config)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            async def execute():
                return await func(*args, **kwargs)

            return await handler.execute_async(execute)

        # Attach metrics to wrapper
        wrapper.retry_metrics = handler.metrics
        wrapper.retry_handler = handler

        return wrapper
    return decorator


def retry_sync(config: Optional[RetryConfig] = None):
    """Decorator for sync functions with retry logic."""
    def decorator(func: Callable):
        handler = RetryHandler(config)

        @wraps(func)
        def wrapper(*args, **kwargs):
            def execute():
                return func(*args, **kwargs)

            return handler.execute_sync(execute)

        # Attach metrics to wrapper
        wrapper.retry_metrics = handler.metrics
        wrapper.retry_handler = handler

        return wrapper
    return decorator


class ConditionalRetry:
    """Conditional retry based on return value or custom condition."""

    def __init__(
        self,
        condition: Callable[[Any], bool],
        config: Optional[RetryConfig] = None
    ):
        self.condition = condition
        self.config = config or RetryConfig()
        self.handler = RetryHandler(self.config)

    async def execute_async(self, func: Callable) -> Any:
        """Execute with conditional retry logic."""
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = await func()

                if self.condition(result):
                    if attempt > 1:
                        logger.info(f"Condition met after {attempt} attempts")
                    return result

                # Condition not met, treat as retryable
                if attempt < self.config.max_attempts:
                    delay = self.handler._calculate_delay(attempt)
                    logger.info(f"Condition not met, retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.warning(f"Attempt {attempt} failed: {e}")
                if attempt < self.config.max_attempts:
                    delay = self.handler._calculate_delay(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

        raise RetryExhaustedError(attempt, Exception("Condition never met"))


# Pre-configured retry decorators for common scenarios
def retry_on_connection_error(max_attempts: int = 3):
    """Retry decorator specifically for connection errors."""
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=1.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
        ),
        non_retryable_exceptions=(
            ValueError,
            TypeError,
            KeyError,
        )
    )
    return retry_async(config)


def retry_on_http_error(max_attempts: int = 3):
    """Retry decorator for HTTP-related errors."""
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=0.5,
        max_delay=10.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
        )
    )
    return retry_async(config)


def retry_database_operation(max_attempts: int = 5):
    """Retry decorator for database operations."""
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=0.1,
        max_delay=5.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
        )
    )
    return retry_async(config)


# Utility functions
async def retry_until_success(
    func: Callable,
    timeout: float = 30.0,
    interval: float = 1.0
) -> Any:
    """Retry function until success or timeout."""
    start_time = time.time()
    attempt = 0

    while time.time() - start_time < timeout:
        attempt += 1
        try:
            result = await func()
            logger.info(f"Operation succeeded after {attempt} attempts")
            return result
        except Exception as e:
            logger.debug(f"Attempt {attempt} failed: {e}")
            await asyncio.sleep(interval)

    raise TimeoutError(f"Operation failed to succeed within {timeout}s timeout")


async def retry_with_circuit_breaker(
    func: Callable,
    circuit_breaker,
    retry_config: Optional[RetryConfig] = None
) -> Any:
    """Combine retry logic with circuit breaker."""
    retry_handler = RetryHandler(retry_config)

    async def wrapped_func():
        return await circuit_breaker(func)

    return await retry_handler.execute_async(wrapped_func)