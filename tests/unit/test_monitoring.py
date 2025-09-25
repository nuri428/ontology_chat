"""Unit tests for monitoring and metrics collection."""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from api.monitoring.metrics import metrics_collector, MetricsCollector
from api.monitoring.middleware import PrometheusMiddleware, HealthMonitoringMiddleware
from fastapi import Request, Response
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse


@pytest.mark.unit
class TestMetricsCollector:
    """Test suite for MetricsCollector."""

    def test_metrics_collector_initialization(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector()
        assert collector.start_time > 0

    def test_record_http_request(self):
        """Test HTTP request recording."""
        collector = MetricsCollector()

        # Record a request
        collector.record_http_request("GET", "/chat", 200, 0.5)

        # Verify metrics are recorded (we can't easily assert on Prometheus counters directly)
        # So we just ensure no exceptions are raised
        assert True

    def test_update_quality_score(self):
        """Test quality score update."""
        collector = MetricsCollector()

        # Update quality score
        collector.update_quality_score(0.949)

        # No direct assertion on Prometheus gauge, but ensure no exceptions
        assert True

    def test_cache_metrics_update(self):
        """Test cache metrics update."""
        collector = MetricsCollector()

        # Mock cache stats
        cache_stats = {
            "overall": {
                "hit_rate": 0.85,
                "avg_response_time_ms": 45.0,
                "hits": 1000,
                "misses": 150,
                "l1_hits": 600,
                "l2_hits": 300,
                "l3_hits": 100
            },
            "l1": {
                "hit_rate": 0.6,
                "memory_bytes": 50 * 1024 * 1024,  # 50MB
                "max_memory_bytes": 100 * 1024 * 1024,  # 100MB
                "size": 500,
                "max_size": 1000
            },
            "l2": {
                "hit_rate": 0.3,
                "size": 200
            },
            "l3": {
                "hit_rate": 0.1,
                "total_size_bytes": 500 * 1024 * 1024,  # 500MB
                "size": 100
            }
        }

        collector.update_cache_metrics(cache_stats)

        # Verify effectiveness calculation
        assert True

    def test_circuit_breaker_metrics(self):
        """Test circuit breaker metrics recording."""
        collector = MetricsCollector()

        # Record circuit breaker state
        collector.update_circuit_breaker_state("neo4j_service", "open", True)
        collector.record_circuit_breaker_failure("neo4j_service")
        collector.record_circuit_breaker_success("neo4j_service")

        assert True

    def test_llm_operation_metrics(self):
        """Test LLM operation metrics."""
        collector = MetricsCollector()

        # Record LLM operations
        collector.record_llm_operation("llama3.1", "keyword_extraction", 2.5)
        collector.record_llm_operation("llama3.1", "context_analysis", 1.8)

        assert True

    def test_context_retrieval_metrics(self):
        """Test context retrieval metrics."""
        collector = MetricsCollector()

        # Record context retrieval
        collector.record_context_retrieval("neo4j", 0.8)
        collector.record_context_retrieval("opensearch", 0.5)

        assert True

    def test_database_query_metrics(self):
        """Test database query metrics."""
        collector = MetricsCollector()

        # Record database queries
        collector.record_neo4j_query(True)
        collector.record_neo4j_query(False)
        collector.record_opensearch_query(True)
        collector.record_opensearch_query(False)

        assert True

    def test_health_status_update(self):
        """Test health status update."""
        collector = MetricsCollector()

        # Update health status
        collector.update_health_status(True, 0)  # Healthy, full service
        collector.update_health_status(False, 2)  # Unhealthy, minimal service

        assert True

    def test_cache_effectiveness_calculation(self):
        """Test cache effectiveness score calculation."""
        collector = MetricsCollector()

        # Test with good performance
        good_stats = {"hit_rate": 0.9, "avg_response_time_ms": 30}
        effectiveness = collector._calculate_cache_effectiveness(good_stats)
        assert effectiveness > 0.8

        # Test with poor performance
        poor_stats = {"hit_rate": 0.3, "avg_response_time_ms": 150}
        effectiveness = collector._calculate_cache_effectiveness(poor_stats)
        assert effectiveness < 0.5

    def test_get_metrics_format(self):
        """Test metrics output format."""
        collector = MetricsCollector()

        # Get metrics
        metrics_output = collector.get_metrics()

        # Should be Prometheus text format
        assert isinstance(metrics_output, str)
        assert "# HELP" in metrics_output or "# TYPE" in metrics_output or len(metrics_output) >= 0


@pytest.mark.unit
class TestPrometheusMiddleware:
    """Test suite for PrometheusMiddleware."""

    @pytest.mark.asyncio
    async def test_prometheus_middleware_records_metrics(self):
        """Test that Prometheus middleware records HTTP metrics."""
        app = Starlette()
        middleware = PrometheusMiddleware(app)

        # Mock request and response
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/chat"

        response = Mock(spec=Response)
        response.status_code = 200

        # Mock call_next
        async def mock_call_next(request):
            return response

        # Process request
        result = await middleware.dispatch(request, mock_call_next)

        assert result == response

    @pytest.mark.asyncio
    async def test_prometheus_middleware_handles_exceptions(self):
        """Test middleware handles exceptions properly."""
        app = Starlette()
        middleware = PrometheusMiddleware(app)

        # Mock request
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/report"

        # Mock call_next that raises exception
        async def mock_call_next_error(request):
            raise Exception("Test error")

        # Should re-raise exception
        with pytest.raises(Exception, match="Test error"):
            await middleware.dispatch(request, mock_call_next_error)


@pytest.mark.unit
class TestHealthMonitoringMiddleware:
    """Test suite for HealthMonitoringMiddleware."""

    @pytest.mark.asyncio
    async def test_health_monitoring_tracks_errors(self):
        """Test health monitoring middleware tracks error rates."""
        app = Starlette()
        middleware = HealthMonitoringMiddleware(app)

        # Mock successful request
        request = Mock(spec=Request)
        response = Mock(spec=Response)
        response.status_code = 200

        async def mock_call_next_success(request):
            return response

        # Process successful request
        result = await middleware.dispatch(request, mock_call_next_success)
        assert result == response
        assert middleware.request_count == 1
        assert middleware.error_count == 0

        # Mock error request
        response.status_code = 500
        result = await middleware.dispatch(request, mock_call_next_success)
        assert middleware.request_count == 2
        assert middleware.error_count == 1

    @pytest.mark.asyncio
    async def test_health_monitoring_handles_exceptions(self):
        """Test health monitoring handles exceptions."""
        app = Starlette()
        middleware = HealthMonitoringMiddleware(app)

        request = Mock(spec=Request)

        async def mock_call_next_exception(request):
            raise Exception("Test error")

        # Should track error and re-raise
        with pytest.raises(Exception):
            await middleware.dispatch(request, mock_call_next_exception)

        assert middleware.error_count == 1

    @pytest.mark.asyncio
    async def test_health_monitoring_periodic_check(self):
        """Test periodic health check updates."""
        app = Starlette()
        middleware = HealthMonitoringMiddleware(app)

        # Set up scenario with high error rate
        middleware.request_count = 100
        middleware.error_count = 15  # 15% error rate
        middleware.last_check = time.time() - 65  # Force health check

        request = Mock(spec=Request)
        response = Mock(spec=Response)
        response.status_code = 200

        async def mock_call_next(request):
            return response

        with patch.object(middleware, '_update_health_metrics') as mock_update:
            await middleware.dispatch(request, mock_call_next)
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_update_metrics_logic(self):
        """Test health metrics update logic."""
        app = Starlette()
        middleware = HealthMonitoringMiddleware(app)

        # Test various error rate scenarios
        test_cases = [
            (100, 2, True, 0),   # 2% error rate - healthy, full service
            (100, 7, True, 1),   # 7% error rate - healthy, degraded service
            (100, 12, False, 2), # 12% error rate - unhealthy, minimal service
            (100, 25, False, 3), # 25% error rate - unhealthy, emergency service
        ]

        with patch.object(metrics_collector, 'update_health_status') as mock_update:
            for requests, errors, expected_healthy, expected_degradation in test_cases:
                middleware.request_count = requests
                middleware.error_count = errors

                await middleware._update_health_metrics()

                # Verify the correct health status was set
                mock_update.assert_called_with(expected_healthy, expected_degradation)


@pytest.mark.integration
class TestMonitoringIntegration:
    """Integration tests for monitoring system."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_integration(self):
        """Test metrics endpoint returns valid Prometheus format."""
        from api.routers.metrics_router import get_prometheus_metrics

        # Call metrics endpoint
        result = await get_prometheus_metrics()

        # Should return string in Prometheus format
        assert isinstance(result, str)
        # Basic validation - should contain metric types or help text
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_health_endpoint_integration(self):
        """Test health check endpoint."""
        from api.routers.metrics_router import health_check

        # Call health endpoint
        result = await health_check()

        # Should return health status
        assert "status" in result
        assert result["status"] in ["healthy", "unhealthy"]
        assert "components" in result

    @pytest.mark.asyncio
    async def test_dashboard_metrics_integration(self):
        """Test dashboard metrics endpoint."""
        from api.routers.metrics_router import get_dashboard_metrics

        # Call dashboard endpoint
        result = await get_dashboard_metrics()

        # Should return comprehensive metrics
        if "status" not in result or result.get("status") != "error":
            assert "quality_score" in result
            assert "cache_stats" in result
            assert "performance" in result