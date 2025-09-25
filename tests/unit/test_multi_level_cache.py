"""Unit tests for multi-level caching system."""

import asyncio
import pytest
import tempfile
import shutil
import time
from unittest.mock import Mock, AsyncMock, patch

from api.cache.multi_level_cache import (
    L1MemoryCache,
    L2RedisCache,
    L3DiskCache,
    MultiLevelCache,
    CacheLevel,
    CacheEntry,
    cache_key_generator
)
from api.cache.cache_decorators import (
    multi_cache,
    l1_cache,
    tiered_cache,
    cache_metrics
)


@pytest.mark.unit
class TestL1MemoryCache:
    """Test suite for L1 Memory Cache."""

    @pytest.mark.asyncio
    async def test_l1_basic_operations(self):
        """Test basic L1 cache operations."""
        cache = L1MemoryCache(max_size=3, max_memory_mb=1)

        # Test set and get
        await cache.set("key1", "value1", ttl=10.0)
        result = await cache.get("key1")
        assert result == "value1"

        # Test miss
        result = await cache.get("nonexistent")
        assert result is None

        # Test delete
        deleted = await cache.delete("key1")
        assert deleted is True
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_l1_lru_eviction(self):
        """Test LRU eviction in L1 cache."""
        cache = L1MemoryCache(max_size=2, max_memory_mb=1)

        # Fill cache to capacity
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # Both should be accessible
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"

        # Access key1 to make it recently used
        await cache.get("key1")

        # Add third item - should evict key2 (least recently used)
        await cache.set("key3", "value3")

        assert await cache.get("key1") == "value1"  # Still exists
        assert await cache.get("key2") is None      # Evicted
        assert await cache.get("key3") == "value3"  # New item

    @pytest.mark.asyncio
    async def test_l1_ttl_expiration(self):
        """Test TTL expiration in L1 cache."""
        cache = L1MemoryCache(max_size=10, max_memory_mb=1)

        # Set with short TTL
        await cache.set("key1", "value1", ttl=0.1)

        # Should be accessible immediately
        assert await cache.get("key1") == "value1"

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Should be expired
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_l1_clear(self):
        """Test L1 cache clear."""
        cache = L1MemoryCache(max_size=10, max_memory_mb=1)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        assert len(cache.cache) == 2

        await cache.clear()

        assert len(cache.cache) == 0
        assert await cache.get("key1") is None


@pytest.mark.unit
class TestL2RedisCache:
    """Test suite for L2 Redis Cache."""

    @pytest.mark.asyncio
    async def test_l2_operations_without_redis(self):
        """Test L2 operations when Redis is not available."""
        # Mock Redis client to simulate connection failure
        cache = L2RedisCache(redis_url="redis://nonexistent:6379")

        # Should handle connection errors gracefully
        result = await cache.get("key1")
        assert result is None

        success = await cache.set("key1", "value1")
        assert success is False

        success = await cache.delete("key1")
        assert success is False

    @pytest.mark.asyncio
    async def test_l2_key_prefixing(self):
        """Test Redis key prefixing."""
        cache = L2RedisCache(prefix="test:")

        key = cache._make_key("user:123")
        assert key == "test:user:123"

    @pytest.mark.asyncio
    async def test_l2_mock_operations(self):
        """Test L2 operations with mocked Redis."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            cache = L2RedisCache()
            await cache.connect()

            # Test successful operations
            mock_client.get.return_value = None
            result = await cache.get("key1")
            assert result is None

            mock_client.setex.return_value = True
            success = await cache.set("key1", "value1", 300)
            assert success is True

            mock_client.delete.return_value = 1
            success = await cache.delete("key1")
            assert success is True


@pytest.mark.unit
class TestL3DiskCache:
    """Test suite for L3 Disk Cache."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary directory for cache testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_l3_basic_operations(self, temp_cache_dir):
        """Test basic L3 cache operations."""
        cache = L3DiskCache(cache_dir=temp_cache_dir, max_size_gb=0.01)

        # Test set and get
        await cache.set("key1", {"data": "value1"}, ttl=10.0)
        result = await cache.get("key1")
        assert result == {"data": "value1"}

        # Test miss
        result = await cache.get("nonexistent")
        assert result is None

        # Test delete
        success = await cache.delete("key1")
        assert success is True
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_l3_ttl_expiration(self, temp_cache_dir):
        """Test TTL expiration in L3 cache."""
        cache = L3DiskCache(cache_dir=temp_cache_dir, max_size_gb=0.01)

        # Set with short TTL
        await cache.set("key1", "value1", ttl=0.1)

        # Should be accessible immediately
        assert await cache.get("key1") == "value1"

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Should be expired
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_l3_clear(self, temp_cache_dir):
        """Test L3 cache clear."""
        cache = L3DiskCache(cache_dir=temp_cache_dir, max_size_gb=0.01)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        assert len(cache.index) == 2

        await cache.clear()

        assert len(cache.index) == 0
        assert await cache.get("key1") is None


@pytest.mark.unit
class TestMultiLevelCache:
    """Test suite for Multi-Level Cache."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_mlc_l1_only(self):
        """Test multi-level cache with L1 only."""
        mlc = MultiLevelCache(
            l1_config={"max_size": 3, "max_memory_mb": 1},
            enable_l2=False,
            enable_l3=False
        )

        await mlc.initialize()

        # Test basic operations
        await mlc.set("key1", "value1")
        result = await mlc.get("key1")
        assert result == "value1"

        # Test stats
        stats = await mlc.get_all_stats()
        assert "l1" in stats
        assert "l2" not in stats or stats["l2"] is None
        assert "l3" not in stats or stats["l3"] is None

    @pytest.mark.asyncio
    async def test_mlc_cache_hierarchy(self, temp_cache_dir):
        """Test cache hierarchy with promotion."""
        mlc = MultiLevelCache(
            l1_config={"max_size": 2, "max_memory_mb": 1},
            l2_config={"redis_url": "redis://localhost:6379"},
            l3_config={"cache_dir": temp_cache_dir},
            enable_l2=False,  # Disable L2 for testing
            enable_l3=True
        )

        await mlc.initialize()

        # Set in L3 only
        await mlc.set("key1", "value1", cache_levels=[CacheLevel.L3_DISK])

        # First get should hit L3 and promote to L1
        result = await mlc.get("key1", promotion=True)
        assert result == "value1"

        # Second get should hit L1
        result = await mlc.get("key1")
        assert result == "value1"

        # Check stats
        stats = await mlc.get_all_stats()
        assert stats["overall"]["l3_hits"] >= 1
        assert stats["overall"]["l1_hits"] >= 1

    @pytest.mark.asyncio
    async def test_mlc_different_ttls(self):
        """Test different TTLs for different cache levels."""
        mlc = MultiLevelCache(
            l1_config={"max_size": 10, "max_memory_mb": 1},
            enable_l2=False,
            enable_l3=False
        )

        await mlc.initialize()

        # Set with short TTL
        await mlc.set("key1", "value1", ttl=0.1)

        # Should be available immediately
        assert await mlc.get("key1") == "value1"

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Should be expired
        assert await mlc.get("key1") is None

    @pytest.mark.asyncio
    async def test_mlc_clear_selective(self):
        """Test selective cache level clearing."""
        mlc = MultiLevelCache(
            l1_config={"max_size": 10, "max_memory_mb": 1},
            enable_l2=False,
            enable_l3=False
        )

        await mlc.initialize()

        await mlc.set("key1", "value1")
        await mlc.set("key2", "value2")

        # Clear only L1
        await mlc.clear([CacheLevel.L1_MEMORY])

        # All keys should be gone
        assert await mlc.get("key1") is None
        assert await mlc.get("key2") is None


@pytest.mark.unit
class TestCacheDecorators:
    """Test suite for cache decorators."""

    @pytest.mark.asyncio
    async def test_multi_cache_decorator(self):
        """Test multi_cache decorator."""
        call_count = 0

        @multi_cache(prefix="test", ttl=1.0, cache_levels=[CacheLevel.L1_MEMORY])
        async def expensive_function(value: str):
            nonlocal call_count
            call_count += 1
            return f"result:{value}"

        # First call should execute function
        result1 = await expensive_function("test")
        assert result1 == "result:test"
        assert call_count == 1

        # Second call should use cache
        result2 = await expensive_function("test")
        assert result2 == "result:test"
        assert call_count == 1  # Not incremented

        # Different parameter should execute function
        result3 = await expensive_function("test2")
        assert result3 == "result:test2"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_l1_cache_decorator(self):
        """Test l1_cache decorator."""
        @l1_cache(ttl=1.0, prefix="l1_test")
        async def test_function(x: int):
            return x * 2

        result1 = await test_function(5)
        assert result1 == 10

        result2 = await test_function(5)
        assert result2 == 10

    @pytest.mark.asyncio
    async def test_tiered_cache_decorator(self):
        """Test tiered_cache decorator."""
        @tiered_cache(l1_ttl=0.1, l2_ttl=0.2, l3_ttl=0.3, prefix="tiered_test")
        async def test_function(x: int):
            return x * 3

        result = await test_function(7)
        assert result == 21

    def test_cache_key_generator(self):
        """Test cache key generation."""
        key1 = cache_key_generator("prefix", "arg1", 123, param="value")
        key2 = cache_key_generator("prefix", "arg1", 123, param="value")
        key3 = cache_key_generator("prefix", "arg1", 124, param="value")

        # Same parameters should generate same key
        assert key1 == key2

        # Different parameters should generate different keys
        assert key1 != key3

        # Key should contain prefix and parameters
        assert "prefix" in key1
        assert "arg1" in key1
        assert "param:value" in key1


@pytest.mark.integration
class TestCacheIntegration:
    """Integration tests for caching system."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_full_cache_pipeline(self, temp_cache_dir):
        """Test full caching pipeline with all levels."""
        mlc = MultiLevelCache(
            l1_config={"max_size": 2, "max_memory_mb": 1},
            l2_config={"redis_url": "redis://localhost:6379"},
            l3_config={"cache_dir": temp_cache_dir},
            enable_l2=False,  # Disable L2 for testing
            enable_l3=True
        )

        await mlc.initialize()

        # Test cache miss -> load -> cache hit scenario
        async def loader(key):
            return f"loaded_value_{key}"

        # First access - should load and cache
        result = await mlc.get("test_key")
        assert result is None

        # Set the value
        await mlc.set("test_key", "test_value")

        # Should now get cached value
        result = await mlc.get("test_key")
        assert result == "test_value"

        # Test promotion between levels
        # Clear L1, value should still be in L3
        await mlc.clear([CacheLevel.L1_MEMORY])

        # Get should hit L3 and promote to L1
        result = await mlc.get("test_key", promotion=True)
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_cache_under_load(self):
        """Test cache behavior under concurrent load."""
        mlc = MultiLevelCache(
            l1_config={"max_size": 100, "max_memory_mb": 10},
            enable_l2=False,
            enable_l3=False
        )

        await mlc.initialize()

        # Concurrent operations
        async def cache_operation(i):
            key = f"key_{i % 10}"  # 10 unique keys
            value = f"value_{i}"

            await mlc.set(key, value)
            result = await mlc.get(key)
            return result is not None

        # Run 100 concurrent operations
        tasks = [cache_operation(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        # All operations should succeed
        assert all(results)

        # Check statistics
        stats = await mlc.get_all_stats()
        assert stats["overall"]["hits"] > 0

    @pytest.mark.asyncio
    async def test_cache_performance_metrics(self):
        """Test cache performance metrics collection."""
        # Reset global metrics
        global cache_metrics
        cache_metrics.request_count = 0
        cache_metrics.cache_hits = 0
        cache_metrics.cache_misses = 0

        mlc = MultiLevelCache(
            l1_config={"max_size": 10, "max_memory_mb": 1},
            enable_l2=False,
            enable_l3=False
        )

        await mlc.initialize()

        # Generate some cache activity
        await mlc.set("perf_key", "perf_value")

        # Multiple gets (should be hits)
        for _ in range(5):
            result = await mlc.get("perf_key")
            assert result == "perf_value"

        # Get non-existent key (should be miss)
        result = await mlc.get("nonexistent")
        assert result is None

        # Check stats
        stats = await mlc.get_all_stats()
        assert stats["overall"]["hits"] >= 5
        assert stats["overall"]["misses"] >= 1
        assert stats["overall"]["hit_rate"] > 0

    @pytest.mark.asyncio
    async def test_cache_optimization(self, temp_cache_dir):
        """Test cache optimization functionality."""
        mlc = MultiLevelCache(
            l1_config={"max_size": 5, "max_memory_mb": 1},
            l3_config={"cache_dir": temp_cache_dir},
            enable_l2=False,
            enable_l3=True
        )

        await mlc.initialize()

        # Add some entries with short TTL
        await mlc.set("short1", "value1", ttl=0.1)
        await mlc.set("short2", "value2", ttl=0.1)
        await mlc.set("long1", "value3", ttl=10.0)

        # Wait for short TTL entries to expire
        await asyncio.sleep(0.2)

        # Optimize should clean up expired entries
        await mlc.optimize()

        # Long TTL entry should still be there
        result = await mlc.get("long1")
        assert result == "value3"

        # Short TTL entries should be gone
        result1 = await mlc.get("short1")
        result2 = await mlc.get("short2")
        assert result1 is None
        assert result2 is None