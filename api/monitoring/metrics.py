"""Prometheus metrics for Ontology Chat application."""

import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from prometheus_client.core import REGISTRY

# Create custom registry for our metrics
ONTOLOGY_REGISTRY = CollectorRegistry()

# HTTP Request Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=ONTOLOGY_REGISTRY
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=ONTOLOGY_REGISTRY
)

# A-Grade Quality Metrics
ontology_chat_quality_score = Gauge(
    'ontology_chat_quality_score',
    'Current A-grade quality score',
    registry=ONTOLOGY_REGISTRY
)

# Cache Metrics
ontology_chat_cache_hits_total = Counter(
    'ontology_chat_cache_hits_total',
    'Total cache hits',
    ['level'],
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_misses_total = Counter(
    'ontology_chat_cache_misses_total',
    'Total cache misses',
    ['level'],
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_sets_total = Counter(
    'ontology_chat_cache_sets_total',
    'Total cache sets',
    ['level'],
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_evictions_total = Counter(
    'ontology_chat_cache_evictions_total',
    'Total cache evictions',
    ['level'],
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_hit_rate = Gauge(
    'ontology_chat_cache_hit_rate',
    'Overall cache hit rate',
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_l1_hit_rate = Gauge(
    'ontology_chat_cache_l1_hit_rate',
    'L1 cache hit rate',
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_l2_hit_rate = Gauge(
    'ontology_chat_cache_l2_hit_rate',
    'L2 cache hit rate',
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_l3_hit_rate = Gauge(
    'ontology_chat_cache_l3_hit_rate',
    'L3 cache hit rate',
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_l1_memory_usage_bytes = Gauge(
    'ontology_chat_cache_l1_memory_usage_bytes',
    'L1 cache memory usage in bytes',
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_l1_max_memory_bytes = Gauge(
    'ontology_chat_cache_l1_max_memory_bytes',
    'L1 cache memory limit in bytes',
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_l3_disk_usage_bytes = Gauge(
    'ontology_chat_cache_l3_disk_usage_bytes',
    'L3 cache disk usage in bytes',
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_operation_duration_seconds = Histogram(
    'ontology_chat_cache_operation_duration_seconds',
    'Cache operation duration in seconds',
    ['level', 'operation'],
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_cache_effectiveness_score = Gauge(
    'ontology_chat_cache_effectiveness_score',
    'Cache effectiveness score (0-1)',
    registry=ONTOLOGY_REGISTRY
)

# Circuit Breaker Metrics
ontology_chat_circuit_breaker_state = Gauge(
    'ontology_chat_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['name', 'state'],
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_circuit_breaker_failures_total = Counter(
    'ontology_chat_circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['name'],
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_circuit_breaker_successes_total = Counter(
    'ontology_chat_circuit_breaker_successes_total',
    'Total circuit breaker successes',
    ['name'],
    registry=ONTOLOGY_REGISTRY
)

# LLM and Processing Metrics
ontology_chat_llm_duration_seconds = Histogram(
    'ontology_chat_llm_duration_seconds',
    'LLM processing duration in seconds',
    ['model', 'operation'],
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_context_duration_seconds = Histogram(
    'ontology_chat_context_duration_seconds',
    'Context retrieval duration in seconds',
    ['source'],
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_neo4j_queries_total = Counter(
    'ontology_chat_neo4j_queries_total',
    'Total Neo4j queries',
    ['status'],
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_opensearch_queries_total = Counter(
    'ontology_chat_opensearch_queries_total',
    'Total OpenSearch queries',
    ['status'],
    registry=ONTOLOGY_REGISTRY
)

# System Health Metrics
ontology_chat_healthy = Gauge(
    'ontology_chat_healthy',
    'Service health status (1=healthy, 0=unhealthy)',
    registry=ONTOLOGY_REGISTRY
)

ontology_chat_degradation_level = Gauge(
    'ontology_chat_degradation_level',
    'Service degradation level (0=full, 1=degraded, 2=minimal, 3=emergency)',
    registry=ONTOLOGY_REGISTRY
)


class MetricsCollector:
    """Centralized metrics collection and reporting."""

    def __init__(self):
        self.start_time = time.time()

    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        status_class = f"{status_code // 100}xx"
        http_requests_total.labels(method=method, endpoint=endpoint, status=status_class).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

    def update_quality_score(self, score: float):
        """Update A-grade quality score."""
        ontology_chat_quality_score.set(score)

    def record_cache_hit(self, level: str):
        """Record cache hit."""
        ontology_chat_cache_hits_total.labels(level=level).inc()

    def record_cache_miss(self, level: str):
        """Record cache miss."""
        ontology_chat_cache_misses_total.labels(level=level).inc()

    def record_cache_set(self, level: str):
        """Record cache set operation."""
        ontology_chat_cache_sets_total.labels(level=level).inc()

    def record_cache_eviction(self, level: str):
        """Record cache eviction."""
        ontology_chat_cache_evictions_total.labels(level=level).inc()

    def update_cache_metrics(self, stats: Dict[str, Any]):
        """Update cache metrics from cache statistics."""
        overall = stats.get("overall", {})

        # Hit rates
        ontology_chat_cache_hit_rate.set(overall.get("hit_rate", 0))

        if "l1" in stats:
            l1_stats = stats["l1"]
            ontology_chat_cache_l1_hit_rate.set(l1_stats.get("hit_rate", 0))
            ontology_chat_cache_l1_memory_usage_bytes.set(l1_stats.get("memory_bytes", 0))
            ontology_chat_cache_l1_max_memory_bytes.set(l1_stats.get("max_memory_bytes", 0))

        if "l2" in stats:
            l2_stats = stats["l2"]
            ontology_chat_cache_l2_hit_rate.set(l2_stats.get("hit_rate", 0))

        if "l3" in stats:
            l3_stats = stats["l3"]
            ontology_chat_cache_l3_hit_rate.set(l3_stats.get("hit_rate", 0))
            ontology_chat_cache_l3_disk_usage_bytes.set(l3_stats.get("total_size_bytes", 0))

        # Calculate effectiveness score
        effectiveness = self._calculate_cache_effectiveness(overall)
        ontology_chat_cache_effectiveness_score.set(effectiveness)

    def record_cache_operation(self, level: str, operation: str, duration: float):
        """Record cache operation duration."""
        ontology_chat_cache_operation_duration_seconds.labels(
            level=level, operation=operation
        ).observe(duration)

    def update_circuit_breaker_state(self, name: str, state: str, is_active: bool):
        """Update circuit breaker state metrics."""
        state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state, 0)
        ontology_chat_circuit_breaker_state.labels(name=name, state=state).set(
            1 if is_active else 0
        )

    def record_circuit_breaker_failure(self, name: str):
        """Record circuit breaker failure."""
        ontology_chat_circuit_breaker_failures_total.labels(name=name).inc()

    def record_circuit_breaker_success(self, name: str):
        """Record circuit breaker success."""
        ontology_chat_circuit_breaker_successes_total.labels(name=name).inc()

    def record_llm_operation(self, model: str, operation: str, duration: float):
        """Record LLM operation duration."""
        ontology_chat_llm_duration_seconds.labels(model=model, operation=operation).observe(duration)

    def record_context_retrieval(self, source: str, duration: float):
        """Record context retrieval duration."""
        ontology_chat_context_duration_seconds.labels(source=source).observe(duration)

    def record_neo4j_query(self, success: bool):
        """Record Neo4j query."""
        status = "success" if success else "failure"
        ontology_chat_neo4j_queries_total.labels(status=status).inc()

    def record_opensearch_query(self, success: bool):
        """Record OpenSearch query."""
        status = "success" if success else "failure"
        ontology_chat_opensearch_queries_total.labels(status=status).inc()

    def update_health_status(self, is_healthy: bool, degradation_level: int = 0):
        """Update service health metrics."""
        ontology_chat_healthy.set(1 if is_healthy else 0)
        ontology_chat_degradation_level.set(degradation_level)

    def _calculate_cache_effectiveness(self, stats: Dict[str, Any]) -> float:
        """Calculate cache effectiveness score."""
        hit_rate = stats.get("hit_rate", 0)
        avg_response_time = stats.get("avg_response_time_ms", 100)

        # Effectiveness based on hit rate and response time
        hit_score = hit_rate
        time_score = max(0, 1 - (avg_response_time / 100))  # 100ms baseline

        return (hit_score * 0.7 + time_score * 0.3)

    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        return generate_latest(ONTOLOGY_REGISTRY).decode('utf-8')


# Global metrics collector instance
metrics_collector = MetricsCollector()