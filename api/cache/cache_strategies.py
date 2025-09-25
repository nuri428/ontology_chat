"""Advanced caching strategies for different use cases."""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import logging

from api.cache.multi_level_cache import multi_level_cache, CacheLevel

logger = logging.getLogger(__name__)


class CacheStrategy(ABC):
    """Abstract base class for caching strategies."""

    @abstractmethod
    async def read(self, key: str, loader: Callable) -> Any:
        """Read data with caching strategy."""
        pass

    @abstractmethod
    async def write(self, key: str, value: Any, writer: Optional[Callable] = None) -> bool:
        """Write data with caching strategy."""
        pass

    @abstractmethod
    async def delete(self, key: str, deleter: Optional[Callable] = None) -> bool:
        """Delete data with caching strategy."""
        pass


class WriteThrough(CacheStrategy):
    """
    Write-through caching strategy.

    Data is written to both cache and backing store synchronously.
    Ensures data consistency but may have higher write latency.
    """

    def __init__(self, ttl: float = 3600.0):
        self.ttl = ttl

    async def read(self, key: str, loader: Callable) -> Any:
        """Read with write-through strategy."""
        # Try cache first
        value = await multi_level_cache.get(key)
        if value is not None:
            return value

        # Load from backing store
        value = await loader(key)
        if value is not None:
            # Cache the loaded value
            await multi_level_cache.set(key, value, ttl=self.ttl)

        return value

    async def write(self, key: str, value: Any, writer: Optional[Callable] = None) -> bool:
        """Write through to cache and backing store."""
        success = True

        # Write to backing store first
        if writer:
            success = await writer(key, value)

        # Write to cache if backing store write succeeded
        if success:
            success = await multi_level_cache.set(key, value, ttl=self.ttl)

        return success

    async def delete(self, key: str, deleter: Optional[Callable] = None) -> bool:
        """Delete from cache and backing store."""
        success = True

        # Delete from backing store first
        if deleter:
            success = await deleter(key)

        # Delete from cache
        if success:
            success = await multi_level_cache.delete(key)

        return success


class WriteBack(CacheStrategy):
    """
    Write-back (write-behind) caching strategy.

    Data is written to cache immediately and to backing store asynchronously.
    Provides better write performance but may risk data loss.
    """

    def __init__(self, ttl: float = 3600.0, flush_interval: float = 30.0):
        self.ttl = ttl
        self.flush_interval = flush_interval
        self.write_buffer: Dict[str, Any] = {}
        self.buffer_lock = asyncio.Lock()
        self._flush_task = None

    async def start_flush_task(self, writer: Callable):
        """Start background flush task."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_loop(writer))

    async def stop_flush_task(self):
        """Stop background flush task."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None

    async def _flush_loop(self, writer: Callable):
        """Background loop to flush write buffer."""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self._flush_buffer(writer)

    async def _flush_buffer(self, writer: Callable):
        """Flush write buffer to backing store."""
        async with self.buffer_lock:
            if not self.write_buffer:
                return

            buffer_copy = self.write_buffer.copy()
            self.write_buffer.clear()

        # Write to backing store
        for key, value in buffer_copy.items():
            try:
                await writer(key, value)
                logger.debug(f"Flushed {key} to backing store")
            except Exception as e:
                logger.error(f"Failed to flush {key}: {e}")
                # Re-add to buffer for retry
                async with self.buffer_lock:
                    self.write_buffer[key] = value

    async def read(self, key: str, loader: Callable) -> Any:
        """Read with write-back strategy."""
        # Check write buffer first
        async with self.buffer_lock:
            if key in self.write_buffer:
                return self.write_buffer[key]

        # Try cache
        value = await multi_level_cache.get(key)
        if value is not None:
            return value

        # Load from backing store
        value = await loader(key)
        if value is not None:
            await multi_level_cache.set(key, value, ttl=self.ttl)

        return value

    async def write(self, key: str, value: Any, writer: Optional[Callable] = None) -> bool:
        """Write to cache immediately, backing store later."""
        # Write to cache immediately
        success = await multi_level_cache.set(key, value, ttl=self.ttl)

        # Add to write buffer for async write
        if writer:
            async with self.buffer_lock:
                self.write_buffer[key] = value

            # Ensure flush task is running
            await self.start_flush_task(writer)

        return success

    async def delete(self, key: str, deleter: Optional[Callable] = None) -> bool:
        """Delete from cache and mark for deletion in backing store."""
        # Remove from write buffer
        async with self.buffer_lock:
            self.write_buffer.pop(key, None)

        # Delete from cache
        success = await multi_level_cache.delete(key)

        # Async delete from backing store
        if deleter:
            asyncio.create_task(deleter(key))

        return success


class ReadThrough(CacheStrategy):
    """
    Read-through caching strategy.

    Cache automatically loads data from backing store on cache miss.
    Simplifies application code by hiding cache population logic.
    """

    def __init__(self, ttl: float = 3600.0, negative_ttl: float = 60.0):
        self.ttl = ttl
        self.negative_ttl = negative_ttl  # TTL for null/not-found results

    async def read(self, key: str, loader: Callable) -> Any:
        """Read-through implementation."""
        # Try cache first
        cached = await multi_level_cache.get(key)

        # Check for negative cache (cached None value)
        if cached is not None or cached == "NEGATIVE_CACHE":
            return None if cached == "NEGATIVE_CACHE" else cached

        # Load from backing store
        value = await loader(key)

        if value is not None:
            # Cache positive result
            await multi_level_cache.set(key, value, ttl=self.ttl)
        else:
            # Cache negative result with shorter TTL
            await multi_level_cache.set(
                key,
                "NEGATIVE_CACHE",
                ttl=self.negative_ttl,
                cache_levels=[CacheLevel.L1_MEMORY]  # Only in L1 for negative cache
            )

        return value

    async def write(self, key: str, value: Any, writer: Optional[Callable] = None) -> bool:
        """Write with read-through strategy."""
        success = True

        # Write to backing store
        if writer:
            success = await writer(key, value)

        # Update cache
        if success:
            await multi_level_cache.set(key, value, ttl=self.ttl)

        return success

    async def delete(self, key: str, deleter: Optional[Callable] = None) -> bool:
        """Delete with read-through strategy."""
        success = True

        # Delete from backing store
        if deleter:
            success = await deleter(key)

        # Delete from cache
        if success:
            await multi_level_cache.delete(key)

        return success


class RefreshAhead(CacheStrategy):
    """
    Refresh-ahead (proactive refresh) caching strategy.

    Automatically refreshes cache entries before they expire for frequently accessed data.
    Reduces cache misses for hot data.
    """

    def __init__(
        self,
        ttl: float = 3600.0,
        refresh_threshold: float = 0.8,  # Refresh when 80% of TTL passed
        min_access_count: int = 3  # Minimum accesses to trigger refresh
    ):
        self.ttl = ttl
        self.refresh_threshold = refresh_threshold
        self.min_access_count = min_access_count
        self.access_counts: Dict[str, int] = {}
        self.refresh_timestamps: Dict[str, float] = {}
        self._refresh_tasks: Dict[str, asyncio.Task] = {}

    async def read(self, key: str, loader: Callable) -> Any:
        """Read with refresh-ahead strategy."""
        # Update access count
        self.access_counts[key] = self.access_counts.get(key, 0) + 1

        # Try cache
        value = await multi_level_cache.get(key)

        if value is not None:
            # Check if we should refresh
            if await self._should_refresh(key):
                # Start async refresh
                await self._start_refresh(key, loader)
            return value

        # Cache miss - load and cache
        value = await loader(key)
        if value is not None:
            await multi_level_cache.set(key, value, ttl=self.ttl)
            self.refresh_timestamps[key] = time.time()

        return value

    async def write(self, key: str, value: Any, writer: Optional[Callable] = None) -> bool:
        """Write with refresh-ahead strategy."""
        success = True

        # Write to backing store
        if writer:
            success = await writer(key, value)

        # Update cache
        if success:
            await multi_level_cache.set(key, value, ttl=self.ttl)
            self.refresh_timestamps[key] = time.time()

            # Cancel any pending refresh
            if key in self._refresh_tasks:
                self._refresh_tasks[key].cancel()
                del self._refresh_tasks[key]

        return success

    async def delete(self, key: str, deleter: Optional[Callable] = None) -> bool:
        """Delete with refresh-ahead strategy."""
        # Cancel any pending refresh
        if key in self._refresh_tasks:
            self._refresh_tasks[key].cancel()
            del self._refresh_tasks[key]

        # Clean up tracking data
        self.access_counts.pop(key, None)
        self.refresh_timestamps.pop(key, None)

        success = True

        # Delete from backing store
        if deleter:
            success = await deleter(key)

        # Delete from cache
        if success:
            await multi_level_cache.delete(key)

        return success

    async def _should_refresh(self, key: str) -> bool:
        """Check if a cache entry should be refreshed."""
        # Check access count
        if self.access_counts.get(key, 0) < self.min_access_count:
            return False

        # Check if already refreshing
        if key in self._refresh_tasks and not self._refresh_tasks[key].done():
            return False

        # Check time since last refresh
        last_refresh = self.refresh_timestamps.get(key, 0)
        time_passed = time.time() - last_refresh
        threshold_time = self.ttl * self.refresh_threshold

        return time_passed >= threshold_time

    async def _start_refresh(self, key: str, loader: Callable):
        """Start async refresh task."""
        async def refresh():
            try:
                logger.debug(f"Refreshing cache for key: {key}")
                value = await loader(key)
                if value is not None:
                    await multi_level_cache.set(key, value, ttl=self.ttl)
                    self.refresh_timestamps[key] = time.time()
                    logger.debug(f"Successfully refreshed cache for key: {key}")
            except Exception as e:
                logger.warning(f"Failed to refresh cache for key {key}: {e}")
            finally:
                # Clean up task reference
                if key in self._refresh_tasks:
                    del self._refresh_tasks[key]

        # Start refresh task
        self._refresh_tasks[key] = asyncio.create_task(refresh())


@dataclass
class CacheStrategyConfig:
    """Configuration for cache strategies."""
    strategy_type: str
    ttl: float = 3600.0
    flush_interval: float = 30.0  # For write-back
    refresh_threshold: float = 0.8  # For refresh-ahead
    min_access_count: int = 3  # For refresh-ahead
    negative_ttl: float = 60.0  # For read-through


class CacheStrategyManager:
    """Manager for different caching strategies."""

    def __init__(self):
        self.strategies: Dict[str, CacheStrategy] = {}
        self._initialize_default_strategies()

    def _initialize_default_strategies(self):
        """Initialize default strategies."""
        self.strategies["write_through"] = WriteThrough()
        self.strategies["write_back"] = WriteBack()
        self.strategies["read_through"] = ReadThrough()
        self.strategies["refresh_ahead"] = RefreshAhead()

    def get_strategy(self, name: str) -> Optional[CacheStrategy]:
        """Get a caching strategy by name."""
        return self.strategies.get(name)

    def register_strategy(self, name: str, strategy: CacheStrategy):
        """Register a custom caching strategy."""
        self.strategies[name] = strategy

    def create_strategy(self, config: CacheStrategyConfig) -> CacheStrategy:
        """Create a strategy from configuration."""
        if config.strategy_type == "write_through":
            return WriteThrough(ttl=config.ttl)

        elif config.strategy_type == "write_back":
            return WriteBack(ttl=config.ttl, flush_interval=config.flush_interval)

        elif config.strategy_type == "read_through":
            return ReadThrough(ttl=config.ttl, negative_ttl=config.negative_ttl)

        elif config.strategy_type == "refresh_ahead":
            return RefreshAhead(
                ttl=config.ttl,
                refresh_threshold=config.refresh_threshold,
                min_access_count=config.min_access_count
            )

        else:
            raise ValueError(f"Unknown strategy type: {config.strategy_type}")


# Global strategy manager
cache_strategy_manager = CacheStrategyManager()