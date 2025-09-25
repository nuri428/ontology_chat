"""Multi-level caching system with L1 (Memory), L2 (Redis), and L3 (Disk) tiers."""

import asyncio
import json
import hashlib
import pickle
import time
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union, Callable, List
from collections import OrderedDict
from pathlib import Path
import logging
import aiofiles
import redis.asyncio as redis
from enum import Enum

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache level definitions."""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DISK = "l3_disk"


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""
    hits: int = 0
    misses: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    avg_response_time_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "l3_hits": self.l3_hits,
            "evictions": self.evictions,
            "total_size_bytes": self.total_size_bytes,
            "avg_response_time_ms": self.avg_response_time_ms
        }


@dataclass
class CacheEntry:
    """Individual cache entry with metadata."""
    key: str
    value: Any
    timestamp: float
    ttl: float
    size_bytes: int
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    cache_level: CacheLevel = CacheLevel.L1_MEMORY

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() - self.timestamp > self.ttl

    def update_access(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_access = time.time()


class L1MemoryCache:
    """Level 1: In-memory cache using LRU eviction."""

    def __init__(self, max_size: int = 100, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_memory_bytes = 0
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from L1 cache."""
        async with self._lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]
            if entry.is_expired():
                del self.cache[key]
                self.current_memory_bytes -= entry.size_bytes
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            entry.update_access()
            return entry.value

    async def set(self, key: str, value: Any, ttl: float = 300.0) -> bool:
        """Set value in L1 cache."""
        async with self._lock:
            # Calculate size
            size_bytes = len(pickle.dumps(value))

            # Check if we need to evict
            while (len(self.cache) >= self.max_size or
                   self.current_memory_bytes + size_bytes > self.max_memory_bytes):
                if not self.cache:
                    break
                # Remove least recently used
                lru_key, lru_entry = self.cache.popitem(last=False)
                self.current_memory_bytes -= lru_entry.size_bytes
                logger.debug(f"L1 evicted: {lru_key}")

            # Add new entry
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                ttl=ttl,
                size_bytes=size_bytes,
                cache_level=CacheLevel.L1_MEMORY
            )
            self.cache[key] = entry
            self.current_memory_bytes += size_bytes

            return True

    async def delete(self, key: str) -> bool:
        """Delete entry from L1 cache."""
        async with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                del self.cache[key]
                self.current_memory_bytes -= entry.size_bytes
                return True
            return False

    async def clear(self):
        """Clear all L1 cache entries."""
        async with self._lock:
            self.cache.clear()
            self.current_memory_bytes = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get L1 cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "memory_bytes": self.current_memory_bytes,
            "max_memory_bytes": self.max_memory_bytes,
            "memory_usage_percent": (self.current_memory_bytes / self.max_memory_bytes * 100)
                                   if self.max_memory_bytes > 0 else 0
        }


class L2RedisCache:
    """Level 2: Redis cache for distributed caching."""

    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "ontology_chat:"):
        self.redis_url = redis_url
        self.prefix = prefix
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis."""
        if not self.client:
            self.client = redis.from_url(self.redis_url, decode_responses=False)
            await self.client.ping()
            logger.info("L2 Redis cache connected")

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            self.client = None

    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key."""
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from L2 cache."""
        if not self.client:
            await self.connect()

        try:
            redis_key = self._make_key(key)
            data = await self.client.get(redis_key)

            if data:
                entry = pickle.loads(data)
                if isinstance(entry, CacheEntry) and not entry.is_expired():
                    entry.update_access()
                    # Update access count in Redis
                    await self.client.expire(redis_key, int(entry.ttl))
                    return entry.value
                else:
                    await self.client.delete(redis_key)

        except Exception as e:
            logger.warning(f"L2 Redis get error: {e}")

        return None

    async def set(self, key: str, value: Any, ttl: float = 300.0) -> bool:
        """Set value in L2 cache."""
        if not self.client:
            await self.connect()

        try:
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                ttl=ttl,
                size_bytes=len(pickle.dumps(value)),
                cache_level=CacheLevel.L2_REDIS
            )

            redis_key = self._make_key(key)
            data = pickle.dumps(entry)
            await self.client.setex(redis_key, int(ttl), data)
            return True

        except Exception as e:
            logger.warning(f"L2 Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete entry from L2 cache."""
        if not self.client:
            await self.connect()

        try:
            redis_key = self._make_key(key)
            result = await self.client.delete(redis_key)
            return result > 0

        except Exception as e:
            logger.warning(f"L2 Redis delete error: {e}")
            return False

    async def clear(self):
        """Clear all L2 cache entries with prefix."""
        if not self.client:
            await self.connect()

        try:
            pattern = f"{self.prefix}*"
            cursor = 0
            while True:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.client.delete(*keys)
                if cursor == 0:
                    break

        except Exception as e:
            logger.warning(f"L2 Redis clear error: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get L2 cache statistics."""
        if not self.client:
            await self.connect()

        try:
            info = await self.client.info("memory")
            pattern = f"{self.prefix}*"
            keys = await self.client.keys(pattern)

            return {
                "size": len(keys),
                "memory_used": info.get("used_memory", 0),
                "memory_used_human": info.get("used_memory_human", "0B"),
                "connected": True
            }

        except Exception as e:
            logger.warning(f"L2 Redis stats error: {e}")
            return {"connected": False, "error": str(e)}


class L3DiskCache:
    """Level 3: Disk-based cache for long-term storage."""

    def __init__(self, cache_dir: str = "/tmp/ontology_chat_cache", max_size_gb: float = 1.0):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.index_file = self.cache_dir / "index.json"
        self.index: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._load_index()

    def _load_index(self):
        """Load cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            except Exception as e:
                logger.warning(f"L3 index load error: {e}")
                self.index = {}

    async def _save_index(self):
        """Save cache index to disk."""
        try:
            async with aiofiles.open(self.index_file, 'w') as f:
                await f.write(json.dumps(self.index))
        except Exception as e:
            logger.warning(f"L3 index save error: {e}")

    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash[:2]}" / f"{key_hash}.cache"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from L3 cache."""
        async with self._lock:
            if key not in self.index:
                return None

            meta = self.index[key]
            if time.time() - meta["timestamp"] > meta["ttl"]:
                # Expired
                await self.delete(key)
                return None

            cache_file = self._get_cache_file(key)
            if not cache_file.exists():
                del self.index[key]
                return None

            try:
                async with aiofiles.open(cache_file, 'rb') as f:
                    data = await f.read()
                    entry = pickle.loads(data)

                if isinstance(entry, CacheEntry):
                    entry.update_access()
                    # Update index
                    self.index[key]["access_count"] = entry.access_count
                    self.index[key]["last_access"] = entry.last_access
                    await self._save_index()
                    return entry.value

            except Exception as e:
                logger.warning(f"L3 disk get error: {e}")
                del self.index[key]

        return None

    async def set(self, key: str, value: Any, ttl: float = 3600.0) -> bool:
        """Set value in L3 cache."""
        async with self._lock:
            try:
                # Check disk space
                current_size = sum(meta["size_bytes"] for meta in self.index.values())
                size_bytes = len(pickle.dumps(value))

                # Evict if necessary (LRU based on last_access)
                while current_size + size_bytes > self.max_size_bytes and self.index:
                    # Find least recently used
                    lru_key = min(
                        self.index.keys(),
                        key=lambda k: self.index[k].get("last_access", 0)
                    )
                    await self.delete(lru_key)
                    current_size = sum(meta["size_bytes"] for meta in self.index.values())

                # Create entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    timestamp=time.time(),
                    ttl=ttl,
                    size_bytes=size_bytes,
                    cache_level=CacheLevel.L3_DISK
                )

                # Save to disk
                cache_file = self._get_cache_file(key)
                cache_file.parent.mkdir(parents=True, exist_ok=True)

                async with aiofiles.open(cache_file, 'wb') as f:
                    await f.write(pickle.dumps(entry))

                # Update index
                self.index[key] = {
                    "timestamp": entry.timestamp,
                    "ttl": entry.ttl,
                    "size_bytes": entry.size_bytes,
                    "access_count": 0,
                    "last_access": time.time()
                }
                await self._save_index()

                return True

            except Exception as e:
                logger.warning(f"L3 disk set error: {e}")
                return False

    async def delete(self, key: str) -> bool:
        """Delete entry from L3 cache."""
        async with self._lock:
            if key not in self.index:
                return False

            try:
                cache_file = self._get_cache_file(key)
                if cache_file.exists():
                    cache_file.unlink()

                del self.index[key]
                await self._save_index()
                return True

            except Exception as e:
                logger.warning(f"L3 disk delete error: {e}")
                return False

    async def clear(self):
        """Clear all L3 cache entries."""
        async with self._lock:
            try:
                # Remove all cache files
                for cache_file in self.cache_dir.rglob("*.cache"):
                    cache_file.unlink()

                # Clear index
                self.index.clear()
                await self._save_index()

            except Exception as e:
                logger.warning(f"L3 disk clear error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get L3 cache statistics."""
        total_size = sum(meta["size_bytes"] for meta in self.index.values())
        return {
            "size": len(self.index),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_bytes": self.max_size_bytes,
            "usage_percent": (total_size / self.max_size_bytes * 100)
                           if self.max_size_bytes > 0 else 0
        }


class MultiLevelCache:
    """Multi-level cache orchestrator managing L1, L2, and L3 caches."""

    def __init__(
        self,
        l1_config: Optional[Dict[str, Any]] = None,
        l2_config: Optional[Dict[str, Any]] = None,
        l3_config: Optional[Dict[str, Any]] = None,
        enable_l2: bool = True,
        enable_l3: bool = True
    ):
        # Initialize L1 (always enabled)
        l1_config = l1_config or {"max_size": 100, "max_memory_mb": 100}
        self.l1_cache = L1MemoryCache(**l1_config)

        # Initialize L2 (Redis)
        self.enable_l2 = enable_l2
        if enable_l2:
            l2_config = l2_config or {"redis_url": "redis://localhost:6379"}
            self.l2_cache = L2RedisCache(**l2_config)
        else:
            self.l2_cache = None

        # Initialize L3 (Disk)
        self.enable_l3 = enable_l3
        if enable_l3:
            l3_config = l3_config or {"cache_dir": "/tmp/ontology_chat_cache"}
            self.l3_cache = L3DiskCache(**l3_config)
        else:
            self.l3_cache = None

        # Statistics
        self.stats = CacheStats()
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize all cache levels."""
        if self.enable_l2 and self.l2_cache:
            try:
                await self.l2_cache.connect()
                logger.info("L2 Redis cache connected successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize L2 Redis cache: {e}")
                logger.info("Disabling L2 cache and continuing with L1 and L3 only")
                self.enable_l2 = False
                self.l2_cache = None

        logger.info(f"Multi-level cache initialized (L1: True, L2: {self.enable_l2}, L3: {self.enable_l3})")

    async def get(
        self,
        key: str,
        promotion: bool = True
    ) -> Optional[Any]:
        """
        Get value from cache hierarchy.

        Args:
            key: Cache key
            promotion: If True, promote value to higher cache levels

        Returns:
            Cached value or None
        """
        start_time = time.time()

        # Try L1 first
        value = await self.l1_cache.get(key)
        if value is not None:
            self.stats.l1_hits += 1
            self.stats.hits += 1
            self._update_response_time(start_time)
            logger.debug(f"L1 hit: {key}")
            return value

        # Try L2
        if self.enable_l2 and self.l2_cache:
            value = await self.l2_cache.get(key)
            if value is not None:
                self.stats.l2_hits += 1
                self.stats.hits += 1

                # Promote to L1
                if promotion:
                    await self.l1_cache.set(key, value)

                self._update_response_time(start_time)
                logger.debug(f"L2 hit: {key}")
                return value

        # Try L3
        if self.enable_l3 and self.l3_cache:
            value = await self.l3_cache.get(key)
            if value is not None:
                self.stats.l3_hits += 1
                self.stats.hits += 1

                # Promote to L2 and L1
                if promotion:
                    if self.enable_l2 and self.l2_cache:
                        await self.l2_cache.set(key, value)
                    await self.l1_cache.set(key, value)

                self._update_response_time(start_time)
                logger.debug(f"L3 hit: {key}")
                return value

        # Cache miss
        self.stats.misses += 1
        self._update_response_time(start_time)
        logger.debug(f"Cache miss: {key}")
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        cache_levels: Optional[List[CacheLevel]] = None
    ) -> bool:
        """
        Set value in cache hierarchy.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (different for each level if not specified)
            cache_levels: Specific cache levels to write to

        Returns:
            Success status
        """
        if cache_levels is None:
            cache_levels = [CacheLevel.L1_MEMORY]
            if self.enable_l2:
                cache_levels.append(CacheLevel.L2_REDIS)
            if self.enable_l3:
                cache_levels.append(CacheLevel.L3_DISK)

        success = True

        # Set in specified cache levels with appropriate TTL
        if CacheLevel.L1_MEMORY in cache_levels:
            l1_ttl = ttl or 300  # 5 minutes default
            success &= await self.l1_cache.set(key, value, l1_ttl)

        if CacheLevel.L2_REDIS in cache_levels and self.enable_l2 and self.l2_cache:
            l2_ttl = ttl or 1800  # 30 minutes default
            success &= await self.l2_cache.set(key, value, l2_ttl)

        if CacheLevel.L3_DISK in cache_levels and self.enable_l3 and self.l3_cache:
            l3_ttl = ttl or 86400  # 24 hours default
            success &= await self.l3_cache.set(key, value, l3_ttl)

        return success

    async def delete(self, key: str) -> bool:
        """Delete value from all cache levels."""
        success = True

        # Delete from all levels
        success &= await self.l1_cache.delete(key)

        if self.enable_l2 and self.l2_cache:
            success &= await self.l2_cache.delete(key)

        if self.enable_l3 and self.l3_cache:
            success &= await self.l3_cache.delete(key)

        return success

    async def clear(self, cache_levels: Optional[List[CacheLevel]] = None):
        """Clear specified cache levels or all if not specified."""
        if cache_levels is None:
            cache_levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_DISK]

        if CacheLevel.L1_MEMORY in cache_levels:
            await self.l1_cache.clear()

        if CacheLevel.L2_REDIS in cache_levels and self.enable_l2 and self.l2_cache:
            await self.l2_cache.clear()

        if CacheLevel.L3_DISK in cache_levels and self.enable_l3 and self.l3_cache:
            await self.l3_cache.clear()

        # Reset stats
        self.stats = CacheStats()

    def _update_response_time(self, start_time: float):
        """Update average response time metric."""
        response_time_ms = (time.time() - start_time) * 1000
        total_requests = self.stats.hits + self.stats.misses

        if total_requests == 1:
            self.stats.avg_response_time_ms = response_time_ms
        else:
            # Moving average
            self.stats.avg_response_time_ms = (
                (self.stats.avg_response_time_ms * (total_requests - 1) + response_time_ms) /
                total_requests
            )

    async def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all cache levels."""
        stats = {
            "overall": self.stats.to_dict(),
            "l1": self.l1_cache.get_stats()
        }

        if self.enable_l2 and self.l2_cache:
            stats["l2"] = await self.l2_cache.get_stats()

        if self.enable_l3 and self.l3_cache:
            stats["l3"] = self.l3_cache.get_stats()

        return stats

    async def optimize(self):
        """Optimize cache by cleaning expired entries and rebalancing."""
        # Clean expired entries in L1
        expired_keys = []
        for key, entry in self.l1_cache.cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            await self.l1_cache.delete(key)

        # TODO: Implement more sophisticated optimization strategies
        # - Analyze access patterns
        # - Adjust TTLs dynamically
        # - Rebalance hot data across levels

        logger.info(f"Cache optimization completed. Removed {len(expired_keys)} expired entries")

    async def warmup(
        self,
        data_loader: Callable,
        keys: List[str],
        cache_levels: Optional[List[CacheLevel]] = None
    ):
        """
        Warm up cache with preloaded data.

        Args:
            data_loader: Async function to load data for a key
            keys: List of keys to preload
            cache_levels: Cache levels to warm up
        """
        if cache_levels is None:
            cache_levels = [CacheLevel.L1_MEMORY]

        success_count = 0
        for key in keys:
            try:
                value = await data_loader(key)
                if value is not None:
                    await self.set(key, value, cache_levels=cache_levels)
                    success_count += 1
            except Exception as e:
                logger.warning(f"Cache warmup failed for key {key}: {e}")

        logger.info(f"Cache warmup completed: {success_count}/{len(keys)} keys loaded")


# Global multi-level cache instance
def _create_multi_level_cache() -> MultiLevelCache:
    """Create multi-level cache instance with environment configuration."""
    # Redis configuration from environment
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Cache level configurations
    l1_config = {
        "max_size": int(os.getenv("L1_CACHE_MAX_SIZE", "100")),
        "max_memory_mb": int(os.getenv("L1_CACHE_MAX_MEMORY_MB", "100"))
    }

    l2_config = {
        "redis_url": redis_url,
        "prefix": os.getenv("L2_CACHE_PREFIX", "ontology_chat:")
    }

    l3_config = {
        "cache_dir": os.getenv("L3_CACHE_DIR", "/tmp/ontology_chat_cache"),
        "max_size_gb": float(os.getenv("L3_CACHE_MAX_SIZE_GB", "1.0"))
    }

    # Enable/disable cache levels
    enable_l2 = os.getenv("ENABLE_L2_CACHE", "true").lower() == "true"
    enable_l3 = os.getenv("ENABLE_L3_CACHE", "true").lower() == "true"

    logger.info(f"Initializing multi-level cache: L2={enable_l2}, L3={enable_l3}")

    return MultiLevelCache(
        l1_config=l1_config,
        l2_config=l2_config,
        l3_config=l3_config,
        enable_l2=enable_l2,
        enable_l3=enable_l3
    )

multi_level_cache = _create_multi_level_cache()


def cache_key_generator(prefix: str, *args, **kwargs) -> str:
    """Generate cache key from arguments."""
    key_parts = [prefix]

    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])

    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}:{v}")
        else:
            key_parts.append(f"{k}:{hashlib.md5(str(v).encode()).hexdigest()[:8]}")

    return ":".join(key_parts)