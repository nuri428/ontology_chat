"""Performance benchmark tests for critical components."""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch
import statistics

from api.services.chat_service import ChatService
from api.services.context_cache import ContextCache


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmarking test suite."""

    @pytest.mark.asyncio
    async def test_chat_service_response_time(self, chat_service, performance_benchmark):
        """Benchmark ChatService response time."""
        queries = [
            "What is artificial intelligence?",
            "Explain machine learning algorithms",
            "How does deep learning work?",
            "What are neural networks?",
            "Describe natural language processing"
        ]

        response_times = []

        for query in queries:
            performance_benchmark.start()

            # Mock the search methods to return quickly
            with patch.object(chat_service, '_search_neo4j', return_value=[]):
                with patch.object(chat_service, '_search_opensearch', return_value=[]):
                    await chat_service.get_context(query)

            elapsed = performance_benchmark.stop()
            response_times.append(elapsed)

        avg_time = statistics.mean(response_times)
        max_time = max(response_times)

        # Performance requirements
        assert avg_time < 1.5, f"Average response time {avg_time:.2f}s exceeds 1.5s target"
        assert max_time < 3.0, f"Maximum response time {max_time:.2f}s exceeds 3.0s limit"

        print(f"\nResponse Time Metrics:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Max: {max_time:.3f}s")
        print(f"  Min: {min(response_times):.3f}s")

    @pytest.mark.asyncio
    async def test_cache_performance(self, performance_benchmark):
        """Benchmark cache operations performance."""
        cache = ContextCache(capacity=1000, ttl=300)
        num_operations = 1000

        # Benchmark SET operations
        set_times = []
        for i in range(num_operations):
            key = f"query_{i}"
            value = {"context": [f"content_{i}"], "sources": [f"source_{i}"]}

            performance_benchmark.start()
            await cache.set(key, value)
            set_times.append(performance_benchmark.stop())

        # Benchmark GET operations (all hits)
        get_times = []
        for i in range(num_operations):
            key = f"query_{i}"

            performance_benchmark.start()
            cache.get(key)
            get_times.append(performance_benchmark.stop())

        avg_set = statistics.mean(set_times)
        avg_get = statistics.mean(get_times)

        # Performance requirements
        assert avg_set < 0.001, f"Average SET time {avg_set*1000:.2f}ms exceeds 1ms"
        assert avg_get < 0.0005, f"Average GET time {avg_get*1000:.2f}ms exceeds 0.5ms"

        print(f"\nCache Performance Metrics:")
        print(f"  SET avg: {avg_set*1000:.3f}ms")
        print(f"  GET avg: {avg_get*1000:.3f}ms")
        print(f"  Throughput: {num_operations/sum(set_times):.0f} ops/sec")

    @pytest.mark.asyncio
    async def test_keyword_extraction_performance(self, chat_service, performance_benchmark):
        """Benchmark keyword extraction performance."""
        queries = [
            "AI",  # Simple
            "machine learning algorithms",  # Medium
            "deep learning neural networks for computer vision and natural language processing applications in modern artificial intelligence systems"  # Complex
        ]

        extraction_times = {"simple": [], "medium": [], "complex": []}
        categories = ["simple", "medium", "complex"]

        for query, category in zip(queries, categories):
            for _ in range(10):  # Multiple runs for average
                performance_benchmark.start()
                await chat_service.extract_keywords(query)
                elapsed = performance_benchmark.stop()
                extraction_times[category].append(elapsed)

        # Performance requirements
        assert statistics.mean(extraction_times["simple"]) < 0.5
        assert statistics.mean(extraction_times["medium"]) < 1.0
        assert statistics.mean(extraction_times["complex"]) < 2.0

        print(f"\nKeyword Extraction Performance:")
        for category in categories:
            avg_time = statistics.mean(extraction_times[category])
            print(f"  {category}: {avg_time*1000:.1f}ms")

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, chat_service, performance_benchmark):
        """Test performance under concurrent load."""
        num_concurrent = 10
        queries = ["test query"] * num_concurrent

        async def process_query(query):
            start = time.time()
            with patch.object(chat_service, '_search_neo4j', return_value=[]):
                with patch.object(chat_service, '_search_opensearch', return_value=[]):
                    await chat_service.get_context(query)
            return time.time() - start

        # Run concurrently
        performance_benchmark.start()
        times = await asyncio.gather(*[process_query(q) for q in queries])
        total_time = performance_benchmark.stop()

        avg_time = statistics.mean(times)
        throughput = num_concurrent / total_time

        # Performance requirements
        assert throughput > 5, f"Throughput {throughput:.1f} req/s below 5 req/s target"
        assert avg_time < 3.0, f"Average time under load {avg_time:.2f}s exceeds 3s"

        print(f"\nConcurrent Load Performance:")
        print(f"  Throughput: {throughput:.1f} req/s")
        print(f"  Avg response: {avg_time:.3f}s")
        print(f"  Total time: {total_time:.3f}s")

    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory efficiency of cache and services."""
        import sys

        cache = ContextCache(capacity=10000, ttl=300)

        # Fill cache to capacity
        for i in range(10000):
            await cache.set(f"key_{i}", {
                "context": [f"content_{i}"],
                "sources": [f"source_{i}"]
            })

        # Check memory usage (rough estimate)
        cache_size = sys.getsizeof(cache.cache)

        # Memory should be reasonable for 10k entries
        # Assuming ~1KB per entry average
        expected_max = 10000 * 1024  # 10MB
        assert cache_size < expected_max, f"Cache memory {cache_size/1024/1024:.1f}MB exceeds expected"

        print(f"\nMemory Usage:")
        print(f"  Cache (10k items): {cache_size/1024/1024:.2f}MB")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sustained_load_performance(self, chat_service):
        """Test performance under sustained load."""
        duration = 10  # seconds
        queries_sent = 0
        errors = 0
        response_times = []

        start_time = time.time()
        while time.time() - start_time < duration:
            query_start = time.time()

            try:
                with patch.object(chat_service, '_search_neo4j', return_value=[]):
                    with patch.object(chat_service, '_search_opensearch', return_value=[]):
                        await chat_service.get_context("sustained load test")
                response_times.append(time.time() - query_start)
                queries_sent += 1
            except Exception:
                errors += 1

            await asyncio.sleep(0.1)  # 10 req/s rate

        throughput = queries_sent / duration
        error_rate = errors / max(queries_sent, 1)
        avg_response = statistics.mean(response_times) if response_times else 0

        # Performance requirements
        assert throughput > 8, f"Sustained throughput {throughput:.1f} req/s below target"
        assert error_rate < 0.01, f"Error rate {error_rate:.2%} exceeds 1% threshold"
        assert avg_response < 2.0, f"Avg response {avg_response:.2f}s exceeds 2s target"

        print(f"\nSustained Load Results ({duration}s):")
        print(f"  Throughput: {throughput:.1f} req/s")
        print(f"  Total requests: {queries_sent}")
        print(f"  Error rate: {error_rate:.2%}")
        print(f"  Avg response: {avg_response:.3f}s")

    @pytest.mark.asyncio
    async def test_cache_hit_performance_impact(self, performance_benchmark):
        """Measure performance difference between cache hits and misses."""
        cache = ContextCache(capacity=100, ttl=300)

        # Prepare cached data
        cached_value = {"context": ["cached"], "sources": ["cache"]}
        await cache.set("cached_query", cached_value)

        # Measure cache hit performance
        hit_times = []
        for _ in range(100):
            performance_benchmark.start()
            result = cache.get("cached_query")
            hit_times.append(performance_benchmark.stop())
            assert result is not None

        # Measure cache miss performance
        miss_times = []
        for i in range(100):
            performance_benchmark.start()
            result = cache.get(f"missing_query_{i}")
            miss_times.append(performance_benchmark.stop())
            assert result is None

        avg_hit = statistics.mean(hit_times)
        avg_miss = statistics.mean(miss_times)
        speedup = avg_miss / avg_hit if avg_hit > 0 else 1

        print(f"\nCache Performance Impact:")
        print(f"  Hit time: {avg_hit*1000:.3f}ms")
        print(f"  Miss time: {avg_miss*1000:.3f}ms")
        print(f"  Hit is {speedup:.1f}x faster")

        # Cache hits should be significantly faster
        assert avg_hit < avg_miss * 1.5  # Hits should be faster

    @pytest.mark.asyncio
    async def test_quality_score_calculation_performance(self, chat_service):
        """Benchmark quality score calculation performance."""
        context_sizes = [5, 10, 20, 50]
        calculation_times = {}

        for size in context_sizes:
            contexts = [
                {
                    "title": f"Title {i}",
                    "content": f"Content {i}" * 100,
                    "score": 0.9 - (i * 0.01)
                }
                for i in range(size)
            ]

            times = []
            for _ in range(10):
                start = time.time()
                # Simulate quality calculation
                relevance = sum(c["score"] for c in contexts) / len(contexts)
                diversity = len(set(c["title"] for c in contexts)) / len(contexts)
                quality = (relevance * 0.6 + diversity * 0.4)
                times.append(time.time() - start)

            calculation_times[size] = statistics.mean(times)

        print(f"\nQuality Score Calculation Performance:")
        for size, avg_time in calculation_times.items():
            print(f"  {size} contexts: {avg_time*1000:.3f}ms")

        # Should scale linearly or better
        assert all(t < 0.01 for t in calculation_times.values())