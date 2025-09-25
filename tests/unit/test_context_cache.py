"""Unit tests for ContextCache."""

import pytest
import asyncio
import time
from datetime import datetime, timedelta

from api.services.context_cache import ContextCache


@pytest.mark.unit
class TestContextCache:
    """Test suite for ContextCache class."""

    @pytest.mark.asyncio
    async def test_cache_initialization(self):
        """Test cache initialization with default parameters."""
        cache = ContextCache(capacity=100, ttl=300)

        assert cache is not None
        assert cache.capacity == 100
        assert cache.ttl == 300
        assert len(cache.cache) == 0

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, context_cache):
        """Test basic cache set and get operations."""
        key = "test_query"
        value = {"context": ["test content"], "sources": ["test source"]}

        # Set value
        await context_cache.set(key, value)

        # Get value
        retrieved = context_cache.get(key)

        assert retrieved is not None
        assert retrieved["context"] == value["context"]
        assert retrieved["sources"] == value["sources"]

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test TTL expiration of cached items."""
        cache = ContextCache(capacity=10, ttl=1)  # 1 second TTL
        key = "test_query"
        value = {"context": ["test"], "sources": ["source"]}

        # Set value
        await cache.set(key, value)
        assert cache.get(key) is not None

        # Wait for TTL expiration
        await asyncio.sleep(1.5)

        # Value should be expired
        assert cache.get(key) is None

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self):
        """Test LRU eviction when capacity is exceeded."""
        cache = ContextCache(capacity=3, ttl=300)

        # Add items to fill capacity
        await cache.set("query1", {"data": "1"})
        await cache.set("query2", {"data": "2"})
        await cache.set("query3", {"data": "3"})

        # Access query1 to make it recently used
        cache.get("query1")

        # Add new item, should evict query2 (least recently used)
        await cache.set("query4", {"data": "4"})

        assert cache.get("query1") is not None  # Recently accessed
        assert cache.get("query2") is None      # Evicted (LRU)
        assert cache.get("query3") is not None  # Still in cache
        assert cache.get("query4") is not None  # Newly added

    @pytest.mark.asyncio
    async def test_cache_clear(self, context_cache):
        """Test cache clear functionality."""
        # Add multiple items
        await context_cache.set("query1", {"data": "1"})
        await context_cache.set("query2", {"data": "2"})
        await context_cache.set("query3", {"data": "3"})

        assert len(context_cache.cache) == 3

        # Clear cache
        await context_cache.clear()

        assert len(context_cache.cache) == 0
        assert context_cache.get("query1") is None

    @pytest.mark.asyncio
    async def test_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = ContextCache(capacity=10, ttl=300)

        # Perform operations
        await cache.set("query1", {"data": "1"})
        await cache.set("query2", {"data": "2"})

        # Generate hits and misses
        cache.get("query1")  # Hit
        cache.get("query1")  # Hit
        cache.get("query2")  # Hit
        cache.get("query3")  # Miss
        cache.get("query4")  # Miss

        stats = cache.get_stats()

        assert stats["hits"] == 3
        assert stats["misses"] == 2
        assert stats["total_requests"] == 5
        assert stats["hit_rate"] == 0.6
        assert stats["size"] == 2

    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self, context_cache):
        """Test concurrent access to cache."""
        async def set_value(key, value):
            await context_cache.set(key, value)

        async def get_value(key):
            return context_cache.get(key)

        # Concurrent writes
        tasks = [
            set_value(f"query{i}", {"data": str(i)})
            for i in range(10)
        ]
        await asyncio.gather(*tasks)

        # Concurrent reads
        read_tasks = [
            get_value(f"query{i}")
            for i in range(10)
        ]
        results = await asyncio.gather(*read_tasks)

        # All values should be retrievable
        for i, result in enumerate(results):
            assert result is not None
            assert result["data"] == str(i)

    @pytest.mark.asyncio
    async def test_cache_hot_queries(self):
        """Test tracking of hot queries."""
        cache = ContextCache(capacity=10, ttl=300)

        # Generate access pattern
        await cache.set("popular_query", {"data": "popular"})
        await cache.set("rare_query", {"data": "rare"})

        # Access popular query multiple times
        for _ in range(10):
            cache.get("popular_query")

        # Access rare query once
        cache.get("rare_query")

        hot_queries = cache.get_hot_queries(top_n=2)

        assert len(hot_queries) <= 2
        if hot_queries:
            # Most accessed should be first
            assert "popular_query" in [q[0] for q in hot_queries]

    @pytest.mark.asyncio
    async def test_cache_memory_efficiency(self):
        """Test cache memory efficiency with size limits."""
        cache = ContextCache(capacity=100, ttl=300)

        # Add many items
        for i in range(100):
            await cache.set(f"query{i}", {
                "context": [f"content{i}"],
                "sources": [f"source{i}"]
            })

        # Check size doesn't exceed capacity
        assert len(cache.cache) <= 100

        # Add one more item
        await cache.set("query100", {"data": "extra"})

        # Should still be at capacity
        assert len(cache.cache) <= 100

    @pytest.mark.asyncio
    async def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = ContextCache(capacity=10, ttl=1)

        # Add items with short TTL
        await cache.set("query1", {"data": "1"})
        await cache.set("query2", {"data": "2"})

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Add new item to trigger cleanup
        await cache.set("query3", {"data": "3"})

        # Run cleanup
        cache._cleanup_expired()

        # Only non-expired item should remain
        assert cache.get("query1") is None
        assert cache.get("query2") is None
        assert cache.get("query3") is not None

    @pytest.mark.asyncio
    async def test_cache_thread_safety(self):
        """Test cache thread safety with async operations."""
        cache = ContextCache(capacity=100, ttl=300)
        errors = []

        async def stress_test(worker_id):
            try:
                for i in range(10):
                    key = f"worker{worker_id}_item{i}"
                    await cache.set(key, {"data": f"{worker_id}-{i}"})
                    result = cache.get(key)
                    assert result is not None
                    assert result["data"] == f"{worker_id}-{i}"
            except Exception as e:
                errors.append(e)

        # Run multiple workers concurrently
        workers = [stress_test(i) for i in range(10)]
        await asyncio.gather(*workers)

        # No errors should occur
        assert len(errors) == 0

    def test_cache_key_validation(self, context_cache):
        """Test cache key validation."""
        # Test with various key types
        valid_keys = ["query", "test_123", "한글쿼리", "query with spaces"]

        for key in valid_keys:
            # Should not raise exception
            result = context_cache.get(key)
            assert result is None  # Key doesn't exist yet

    @pytest.mark.asyncio
    async def test_cache_value_immutability(self, context_cache):
        """Test that cached values are not modified."""
        key = "test_query"
        original_value = {"context": ["test"], "sources": ["source"]}

        await context_cache.set(key, original_value)

        # Modify the original
        original_value["context"].append("modified")

        # Cached value should remain unchanged
        cached = context_cache.get(key)
        assert len(cached["context"]) == 1
        assert cached["context"][0] == "test"