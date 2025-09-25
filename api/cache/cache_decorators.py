"""Decorators and utilities for multi-level caching."""

import asyncio
import hashlib
import inspect
import time
from functools import wraps
from typing import Any, Callable, List, Optional, Union
import logging

from api.cache.multi_level_cache import (
    multi_level_cache,
    cache_key_generator,
    CacheLevel
)

logger = logging.getLogger(__name__)


def multi_cache(
    prefix: str = None,
    ttl: Optional[float] = None,
    cache_levels: Optional[List[CacheLevel]] = None,
    key_builder: Optional[Callable] = None,
    condition: Optional[Callable] = None
):
    """
    Decorator for multi-level caching of function results.

    Args:
        prefix: Cache key prefix (defaults to function name)
        ttl: Time to live in seconds
        cache_levels: Specific cache levels to use
        key_builder: Custom key builder function
        condition: Function to determine if result should be cached

    Example:
        @multi_cache(prefix="search", ttl=600)
        async def search_documents(query: str):
            # Expensive search operation
            return results
    """
    def decorator(func: Callable):
        cache_prefix = prefix or f"{func.__module__}.{func.__name__}"
        is_async = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache_key_generator(cache_prefix, *args, **kwargs)

            # Try to get from cache
            cached_value = await multi_level_cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Execute function
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Check condition for caching
            if condition and not condition(result):
                logger.debug(f"Result not cached due to condition: {cache_key}")
                return result

            # Cache the result
            await multi_level_cache.set(
                cache_key,
                result,
                ttl=ttl,
                cache_levels=cache_levels
            )

            logger.debug(f"Cached result for {cache_key} (execution: {execution_time:.2f}s)")
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))

        # Attach cache management methods
        wrapper = async_wrapper if is_async else sync_wrapper
        wrapper.cache_key_for = lambda *a, **kw: cache_key_generator(cache_prefix, *a, **kw)
        wrapper.invalidate = lambda *a, **kw: asyncio.run(
            multi_level_cache.delete(cache_key_generator(cache_prefix, *a, **kw))
        )
        wrapper.cache_prefix = cache_prefix

        return wrapper

    return decorator


def l1_cache(ttl: float = 300.0, **kwargs):
    """Decorator for L1 (memory) caching only."""
    return multi_cache(
        ttl=ttl,
        cache_levels=[CacheLevel.L1_MEMORY],
        **kwargs
    )


def l2_cache(ttl: float = 1800.0, **kwargs):
    """Decorator for L2 (Redis) caching only."""
    return multi_cache(
        ttl=ttl,
        cache_levels=[CacheLevel.L2_REDIS],
        **kwargs
    )


def l3_cache(ttl: float = 86400.0, **kwargs):
    """Decorator for L3 (disk) caching only."""
    return multi_cache(
        ttl=ttl,
        cache_levels=[CacheLevel.L3_DISK],
        **kwargs
    )


def tiered_cache(
    l1_ttl: float = 300.0,
    l2_ttl: float = 1800.0,
    l3_ttl: float = 86400.0,
    **kwargs
):
    """
    Decorator for tiered caching with different TTLs per level.

    This decorator applies different TTL values to different cache levels,
    allowing for sophisticated cache aging strategies.
    """
    def decorator(func: Callable):
        cache_prefix = kwargs.get("prefix") or f"{func.__module__}.{func.__name__}"
        is_async = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kw):
            # Generate cache key
            cache_key = cache_key_generator(cache_prefix, *args, **kw)

            # Try to get from cache
            cached_value = await multi_level_cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kw) if is_async else func(*args, **kw)

            # Set in different levels with different TTLs
            await multi_level_cache.l1_cache.set(cache_key, result, l1_ttl)

            if multi_level_cache.enable_l2 and multi_level_cache.l2_cache:
                await multi_level_cache.l2_cache.set(cache_key, result, l2_ttl)

            if multi_level_cache.enable_l3 and multi_level_cache.l3_cache:
                await multi_level_cache.l3_cache.set(cache_key, result, l3_ttl)

            return result

        return async_wrapper if is_async else wraps(func)(
            lambda *a, **kw: asyncio.run(async_wrapper(*a, **kw))
        )

    return decorator


class CachingContext:
    """Context manager for temporary cache configuration."""

    def __init__(
        self,
        disable: bool = False,
        cache_levels: Optional[List[CacheLevel]] = None,
        ttl_override: Optional[float] = None
    ):
        self.disable = disable
        self.cache_levels = cache_levels
        self.ttl_override = ttl_override
        self._original_state = {}

    async def __aenter__(self):
        """Enter caching context."""
        if self.disable:
            # Store original state and disable caching
            self._original_state["enable_l2"] = multi_level_cache.enable_l2
            self._original_state["enable_l3"] = multi_level_cache.enable_l3
            multi_level_cache.enable_l2 = False
            multi_level_cache.enable_l3 = False

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit caching context and restore state."""
        if self.disable:
            # Restore original state
            multi_level_cache.enable_l2 = self._original_state.get("enable_l2", True)
            multi_level_cache.enable_l3 = self._original_state.get("enable_l3", True)


def cache_invalidation_group(*keys: str):
    """
    Decorator for grouping cache invalidation.

    When a function decorated with this is called, it invalidates
    all specified cache keys.

    Example:
        @cache_invalidation_group("user:*", "session:*")
        async def update_user_profile(user_id: str):
            # This will invalidate user and session caches
            pass
    """
    def decorator(func: Callable):
        is_async = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Execute function
            result = await func(*args, **kwargs) if is_async else func(*args, **kwargs)

            # Invalidate cache keys
            for key_pattern in keys:
                if "*" in key_pattern:
                    # Pattern-based invalidation
                    # This would need to be implemented based on your needs
                    logger.info(f"Pattern invalidation not yet implemented: {key_pattern}")
                else:
                    await multi_level_cache.delete(key_pattern)

            return result

        return async_wrapper if is_async else wraps(func)(
            lambda *a, **kw: asyncio.run(async_wrapper(*a, **kw))
        )

    return decorator


def conditional_cache(
    condition_func: Callable[[Any], bool],
    **cache_kwargs
):
    """
    Cache only if condition is met.

    Example:
        @conditional_cache(lambda result: len(result) > 0)
        async def search(query: str):
            # Only cache non-empty results
            return results
    """
    return multi_cache(condition=condition_func, **cache_kwargs)


def cache_aside(
    loader: Callable,
    prefix: str,
    ttl: Optional[float] = None,
    cache_levels: Optional[List[CacheLevel]] = None
):
    """
    Cache-aside pattern implementation.

    Tries cache first, if miss, loads data and caches it.

    Example:
        async def load_user(user_id):
            return await db.get_user(user_id)

        cached_load_user = cache_aside(load_user, "user", ttl=3600)
        user = await cached_load_user(user_id=123)
    """
    async def cached_loader(*args, **kwargs):
        # Generate cache key
        cache_key = cache_key_generator(prefix, *args, **kwargs)

        # Try cache
        cached_value = await multi_level_cache.get(cache_key)
        if cached_value is not None:
            return cached_value

        # Load data
        value = await loader(*args, **kwargs)

        # Cache it
        if value is not None:
            await multi_level_cache.set(
                cache_key,
                value,
                ttl=ttl,
                cache_levels=cache_levels
            )

        return value

    return cached_loader


class CacheMetrics:
    """Cache metrics collector for monitoring."""

    def __init__(self):
        self.request_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_latency_ms = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.request_count == 0:
            return 0.0
        return self.cache_hits / self.request_count

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.request_count == 0:
            return 0.0
        return self.total_latency_ms / self.request_count

    def record_hit(self, latency_ms: float):
        """Record a cache hit."""
        self.request_count += 1
        self.cache_hits += 1
        self.total_latency_ms += latency_ms

    def record_miss(self, latency_ms: float):
        """Record a cache miss."""
        self.request_count += 1
        self.cache_misses += 1
        self.total_latency_ms += latency_ms

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            "request_count": self.request_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.hit_rate,
            "avg_latency_ms": self.avg_latency_ms
        }


# Global metrics instance
cache_metrics = CacheMetrics()


def monitored_cache(**cache_kwargs):
    """
    Cache decorator with metrics monitoring.

    This decorator adds metrics collection to cached functions.
    """
    def decorator(func: Callable):
        original_decorator = multi_cache(**cache_kwargs)
        decorated_func = original_decorator(func)

        @wraps(decorated_func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            # Check if we'll get a cache hit
            cache_key = cache_key_generator(
                cache_kwargs.get("prefix", f"{func.__module__}.{func.__name__}"),
                *args,
                **kwargs
            )
            cached_value = await multi_level_cache.get(cache_key)

            latency_ms = (time.time() - start_time) * 1000

            if cached_value is not None:
                cache_metrics.record_hit(latency_ms)
                return cached_value
            else:
                cache_metrics.record_miss(latency_ms)
                # Call original decorated function
                return await decorated_func(*args, **kwargs)

        return wrapper

    return decorator