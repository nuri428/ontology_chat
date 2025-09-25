"""Unit tests for analytics dashboard functionality."""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from api.routers.analytics_router import (
    get_analytics_dashboard,
    get_performance_snapshot,
    get_performance_history,
    get_cache_analysis,
    get_quality_analysis,
    _calculate_cache_efficiency,
    _get_l1_recommendation,
    _get_active_alerts
)


@pytest.mark.unit
class TestAnalyticsRouter:
    """Test suite for analytics router endpoints."""

    @pytest.mark.asyncio
    async def test_get_analytics_dashboard(self):
        """Test analytics dashboard endpoint."""
        with patch('api.routers.analytics_router.multi_level_cache') as mock_cache, \
             patch('api.routers.analytics_router.cached_chat_service') as mock_service:

            # Mock cache stats
            mock_cache.get_all_stats.return_value = {
                "overall": {
                    "hit_rate": 0.85,
                    "avg_response_time_ms": 45.0,
                    "hits": 1000,
                    "misses": 150
                },
                "l1": {
                    "hit_rate": 0.6,
                    "size": 500,
                    "memory_bytes": 50 * 1024 * 1024
                },
                "l2": {
                    "hit_rate": 0.3,
                    "connected": True,
                    "size": 200
                }
            }

            # Mock service metrics
            mock_service.get_cache_metrics.return_value = {
                "quality_impact": {
                    "total_quality_boost": 0.25,
                    "speed_contribution": 0.15
                },
                "recommendations": ["Cache performance is optimal"]
            }

            # Call endpoint
            result = await get_analytics_dashboard()

            # Verify response structure
            assert "summary" in result
            assert "real_time_metrics" in result
            assert "cache_analytics" in result
            assert "performance_trends" in result
            assert "system_health" in result

            # Verify real-time metrics
            real_time = result["real_time_metrics"]
            assert real_time["response_time_ms"] == 45.0
            assert real_time["cache_hit_rate"] == 0.85

    @pytest.mark.asyncio
    async def test_get_performance_snapshot(self):
        """Test performance snapshot endpoint."""
        with patch('api.routers.analytics_router.multi_level_cache') as mock_cache, \
             patch('api.routers.analytics_router.cached_chat_service') as mock_service:

            mock_cache.get_all_stats.return_value = {
                "overall": {
                    "hit_rate": 0.85,
                    "avg_response_time_ms": 45.0
                }
            }

            mock_service.get_cache_metrics.return_value = {
                "quality_impact": {
                    "total_quality_boost": 0.25
                }
            }

            result = await get_performance_snapshot()

            # Verify snapshot structure
            assert hasattr(result, 'timestamp')
            assert hasattr(result, 'quality_score')
            assert hasattr(result, 'response_time_ms')
            assert hasattr(result, 'cache_hit_rate')

            assert result.response_time_ms == 45.0
            assert result.cache_hit_rate == 0.85

    @pytest.mark.asyncio
    async def test_get_performance_history(self):
        """Test performance history endpoint."""
        result = await get_performance_history(period="24h")

        # Verify response structure
        assert "period" in result
        assert "data_points" in result
        assert "summary" in result

        assert result["period"] == "24h"
        assert isinstance(result["data_points"], list)

        # Verify summary statistics
        summary = result["summary"]
        assert "avg_quality_score" in summary
        assert "avg_response_time" in summary
        assert "avg_cache_hit_rate" in summary

    @pytest.mark.asyncio
    async def test_get_cache_analysis(self):
        """Test cache analysis endpoint."""
        with patch('api.routers.analytics_router.multi_level_cache') as mock_cache, \
             patch('api.routers.analytics_router.cached_chat_service') as mock_service:

            mock_cache.get_all_stats.return_value = {
                "overall": {"hit_rate": 0.85},
                "l1": {"hit_rate": 0.6, "memory_usage_percent": 70},
                "l2": {"hit_rate": 0.3, "connected": True},
                "l3": {"hit_rate": 0.15, "usage_percent": 40}
            }

            mock_service.get_cache_metrics.return_value = {
                "quality_impact": {"total_quality_boost": 0.25},
                "recommendations": ["Optimize cache warming"]
            }

            mock_service.get_hot_queries.return_value = [
                {"query": "AI technology", "count": 45}
            ]

            result = await get_cache_analysis()

            # Verify analysis structure
            assert "overall_performance" in result
            assert "level_analysis" in result
            assert "optimization_suggestions" in result

            # Verify level analysis
            level_analysis = result["level_analysis"]
            assert "l1_memory" in level_analysis
            assert "l2_redis" in level_analysis
            assert "l3_disk" in level_analysis

    @pytest.mark.asyncio
    async def test_get_quality_analysis(self):
        """Test quality analysis endpoint."""
        with patch('api.routers.analytics_router.multi_level_cache') as mock_cache, \
             patch('api.routers.analytics_router.cached_chat_service') as mock_service:

            mock_cache.get_all_stats.return_value = {
                "overall": {
                    "hit_rate": 0.85,
                    "avg_response_time_ms": 45.0
                }
            }

            mock_service.get_cache_metrics.return_value = {
                "quality_impact": {
                    "speed_contribution": 0.15
                }
            }

            result = await get_quality_analysis()

            # Verify quality analysis structure
            assert "current_score" in result
            assert "grade" in result
            assert "contributing_factors" in result
            assert "quality_risks" in result

            assert result["current_score"] == 0.949
            assert result["grade"] == "A"
            assert result["target_threshold"] == 0.900

    def test_calculate_cache_efficiency(self):
        """Test cache efficiency calculation."""
        # Test memory cache efficiency
        memory_data = {"hit_rate": 0.8, "memory_usage_percent": 60}
        efficiency = _calculate_cache_efficiency(memory_data, "memory")
        assert 0 <= efficiency <= 1

        # Test redis cache efficiency
        redis_data = {"hit_rate": 0.6, "connected": True}
        efficiency = _calculate_cache_efficiency(redis_data, "redis")
        assert efficiency == 0.6

        # Test disconnected redis
        redis_data_disconnected = {"hit_rate": 0.6, "connected": False}
        efficiency = _calculate_cache_efficiency(redis_data_disconnected, "redis")
        assert efficiency == 0.3

        # Test disk cache efficiency
        disk_data = {"hit_rate": 0.4, "usage_percent": 50}
        efficiency = _calculate_cache_efficiency(disk_data, "disk")
        assert 0 <= efficiency <= 1

        # Test empty data
        efficiency = _calculate_cache_efficiency({}, "memory")
        assert efficiency == 0.0

    def test_get_l1_recommendation(self):
        """Test L1 cache recommendation logic."""
        # Test excellent performance
        excellent_data = {"hit_rate": 0.9, "memory_usage_percent": 60}
        rec = _get_l1_recommendation(excellent_data)
        assert "Excellent performance" in rec

        # Test good performance
        good_data = {"hit_rate": 0.7, "memory_usage_percent": 60}
        rec = _get_l1_recommendation(good_data)
        assert "Good performance" in rec

        # Test memory pressure
        pressure_data = {"hit_rate": 0.8, "memory_usage_percent": 95}
        rec = _get_l1_recommendation(pressure_data)
        assert "Memory pressure" in rec

        # Test low performance
        low_data = {"hit_rate": 0.4, "memory_usage_percent": 50}
        rec = _get_l1_recommendation(low_data)
        assert "cache warming" in rec

        # Test empty data
        rec = _get_l1_recommendation({})
        assert "not available" in rec

    @pytest.mark.asyncio
    async def test_get_active_alerts(self):
        """Test active alerts retrieval."""
        with patch('api.routers.analytics_router.multi_level_cache') as mock_cache:

            # Test with various alert conditions
            mock_cache.get_all_stats.return_value = {
                "overall": {"hit_rate": 0.25},  # Low hit rate -> alert
                "l1": {"memory_usage_percent": 95},  # Memory pressure -> alert
                "l2": {"connected": False}  # Redis disconnected -> alert
            }

            alerts = await _get_active_alerts()

            # Should have alerts for low hit rate, memory pressure, and redis disconnection
            assert len(alerts) >= 3

            # Verify alert structure
            for alert in alerts:
                assert "id" in alert
                assert "severity" in alert
                assert "message" in alert
                assert "timestamp" in alert
                assert "category" in alert

            # Check specific alert types
            alert_ids = [alert["id"] for alert in alerts]
            assert "low_cache_hit_rate" in alert_ids
            assert "memory_pressure" in alert_ids
            assert "redis_disconnected" in alert_ids

    @pytest.mark.asyncio
    async def test_alerts_endpoint(self):
        """Test alerts endpoint."""
        from api.routers.analytics_router import get_active_alerts as get_alerts_endpoint

        result = await get_alerts_endpoint()

        # Verify response structure
        assert "active_alerts" in result
        assert "alert_summary" in result
        assert "system_status" in result
        assert "recommendations" in result

        # Verify alert summary
        summary = result["alert_summary"]
        assert "critical" in summary
        assert "warning" in summary
        assert "info" in summary

        # Verify system status
        status = result["system_status"]
        assert "overall" in status
        assert "quality_status" in status
        assert "cache_status" in status


@pytest.mark.integration
class TestAnalyticsDashboardIntegration:
    """Integration tests for analytics dashboard."""

    @pytest.mark.asyncio
    async def test_dashboard_endpoint_integration(self):
        """Test dashboard endpoint with mock services."""
        with patch('api.routers.analytics_router.multi_level_cache') as mock_cache, \
             patch('api.routers.analytics_router.cached_chat_service') as mock_service:

            # Set up comprehensive mock data
            mock_cache.get_all_stats.return_value = {
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
                    "size": 500,
                    "memory_bytes": 50 * 1024 * 1024,
                    "max_memory_bytes": 100 * 1024 * 1024,
                    "memory_usage_percent": 50
                },
                "l2": {
                    "hit_rate": 0.3,
                    "connected": True,
                    "size": 200
                },
                "l3": {
                    "hit_rate": 0.15,
                    "total_size_mb": 500,
                    "total_size_bytes": 500 * 1024 * 1024,
                    "usage_percent": 40,
                    "size": 100
                }
            }

            mock_service.get_cache_metrics.return_value = {
                "quality_impact": {
                    "total_quality_boost": 0.25,
                    "speed_contribution": 0.15,
                    "consistency_contribution": 0.10
                },
                "recommendations": [
                    "Cache performance is optimal",
                    "A-grade quality maintained"
                ]
            }

            # Test dashboard endpoint
            result = await get_analytics_dashboard()

            # Comprehensive validation
            assert result is not None
            assert isinstance(result, dict)

            # Validate all major sections exist
            required_sections = [
                "summary", "real_time_metrics", "cache_analytics",
                "performance_trends", "system_health", "quality_analysis", "usage_patterns"
            ]

            for section in required_sections:
                assert section in result, f"Missing section: {section}"

            # Validate cache analytics detail
            cache_analytics = result["cache_analytics"]
            assert "overall_stats" in cache_analytics
            assert "level_breakdown" in cache_analytics

            level_breakdown = cache_analytics["level_breakdown"]
            assert "l1_memory" in level_breakdown
            assert "l2_redis" in level_breakdown
            assert "l3_disk" in level_breakdown

            # Validate quality analysis
            quality_analysis = result["quality_analysis"]
            assert "a_grade_maintenance" in quality_analysis
            assert quality_analysis["a_grade_maintenance"]["current_score"] == 0.949

    @pytest.mark.asyncio
    async def test_performance_history_periods(self):
        """Test performance history with different time periods."""
        periods = ["1h", "6h", "24h", "7d", "30d"]

        for period in periods:
            result = await get_performance_history(period=period)

            assert result["period"] == period
            assert isinstance(result["data_points"], list)
            assert len(result["data_points"]) > 0

            # Verify data point structure
            for point in result["data_points"][:3]:  # Check first 3 points
                required_fields = [
                    "timestamp", "quality_score", "response_time_ms",
                    "cache_hit_rate", "error_rate", "requests_count"
                ]
                for field in required_fields:
                    assert field in point, f"Missing field {field} in data point"

    @pytest.mark.asyncio
    async def test_cache_analysis_comprehensive(self):
        """Test comprehensive cache analysis."""
        with patch('api.routers.analytics_router.multi_level_cache') as mock_cache, \
             patch('api.routers.analytics_router.cached_chat_service') as mock_service:

            # Detailed cache stats
            mock_cache.get_all_stats.return_value = {
                "overall": {"hit_rate": 0.85},
                "l1": {"hit_rate": 0.6, "memory_usage_percent": 70},
                "l2": {"hit_rate": 0.3, "connected": True},
                "l3": {"hit_rate": 0.15, "usage_percent": 40}
            }

            mock_service.get_cache_metrics.return_value = {
                "quality_impact": {"total_quality_boost": 0.25},
                "recommendations": ["Optimize L1 cache size", "Consider Redis tuning"]
            }

            mock_service.get_hot_queries.return_value = [
                {"query": "AI technology", "count": 45, "avg_quality": 0.952},
                {"query": "machine learning", "count": 38, "avg_quality": 0.947}
            ]

            result = await get_cache_analysis()

            # Verify comprehensive analysis
            assert "overall_performance" in result
            assert "level_analysis" in result
            assert "optimization_suggestions" in result
            assert "cache_patterns" in result

            # Verify optimization suggestions
            suggestions = result["optimization_suggestions"]
            assert len(suggestions) >= 2
            assert any("L1" in suggestion for suggestion in suggestions)

            # Verify cache patterns
            patterns = result["cache_patterns"]
            assert "hot_queries" in patterns
            assert len(patterns["hot_queries"]) == 2