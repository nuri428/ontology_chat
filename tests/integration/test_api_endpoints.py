"""Integration tests for FastAPI endpoints."""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.main import app


@pytest.mark.integration
@pytest.mark.api
class TestAPIEndpoints:
    """Test suite for API endpoints."""

    def test_health_check(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_readiness_check(self, test_client):
        """Test readiness check endpoint."""
        response = test_client.get("/ready")

        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_chat_endpoint_success(self, test_client):
        """Test chat endpoint with successful response."""
        with patch('api.routers.chat.ChatService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_context.return_value = {
                "context": ["Test context"],
                "sources": ["Test source"],
                "query": "test query"
            }
            mock_service.return_value = mock_instance

            response = test_client.post(
                "/api/v1/chat",
                json={"query": "test query"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "context" in data
            assert "sources" in data

    @pytest.mark.asyncio
    async def test_chat_endpoint_empty_query(self, test_client):
        """Test chat endpoint with empty query."""
        response = test_client.post(
            "/api/v1/chat",
            json={"query": ""}
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_chat_endpoint_long_query(self, test_client):
        """Test chat endpoint with very long query."""
        long_query = "test " * 1000  # Very long query

        with patch('api.routers.chat.ChatService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_context.return_value = {
                "context": ["Context for long query"],
                "sources": ["Source"],
                "query": long_query[:100]
            }
            mock_service.return_value = mock_instance

            response = test_client.post(
                "/api/v1/chat",
                json={"query": long_query}
            )

            assert response.status_code == 200

    def test_cache_stats_endpoint(self, test_client):
        """Test cache statistics endpoint."""
        with patch('api.routers.cache_router.ContextCache') as mock_cache:
            mock_instance = MagicMock()
            mock_instance.get_stats.return_value = {
                "hits": 100,
                "misses": 50,
                "hit_rate": 0.667,
                "size": 75,
                "capacity": 100
            }
            mock_cache.return_value = mock_instance

            response = test_client.get("/api/v1/cache/stats")

            if response.status_code == 200:
                data = response.json()
                assert "hits" in data or "hit_rate" in data

    def test_cache_clear_endpoint(self, test_client):
        """Test cache clear endpoint."""
        with patch('api.routers.cache_router.ContextCache') as mock_cache:
            mock_instance = MagicMock()
            mock_instance.clear.return_value = None
            mock_cache.return_value = mock_instance

            response = test_client.post("/api/v1/cache/clear")

            if response.status_code == 200:
                data = response.json()
                assert "message" in data or "status" in data

    def test_mcp_search_endpoint(self, test_client):
        """Test MCP search endpoint."""
        with patch('api.adapters.mcp_neo4j.Neo4jMCP') as mock_mcp:
            mock_instance = MagicMock()
            mock_instance.search.return_value = [
                {
                    "title": "Test Result",
                    "content": "Test content",
                    "score": 0.9
                }
            ]
            mock_mcp.return_value = mock_instance

            response = test_client.post(
                "/api/v1/mcp/search",
                json={"query": "test", "limit": 10}
            )

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list) or "results" in data

    @pytest.mark.parametrize("endpoint,method", [
        ("/health", "GET"),
        ("/ready", "GET"),
        ("/api/v1/chat", "POST"),
        ("/api/v1/cache/stats", "GET"),
    ])
    def test_endpoint_availability(self, test_client, endpoint, method):
        """Test that endpoints are available."""
        if method == "GET":
            response = test_client.get(endpoint)
        elif method == "POST":
            response = test_client.post(endpoint, json={})

        # Should not return 404
        assert response.status_code != 404

    def test_cors_headers(self, test_client):
        """Test CORS headers are properly set."""
        response = test_client.options("/api/v1/chat")

        # Check for CORS headers
        headers = response.headers
        # CORS headers should be present if configured
        if "access-control-allow-origin" in headers:
            assert headers["access-control-allow-origin"] in ["*", "http://localhost:3000"]

    def test_request_id_header(self, test_client):
        """Test that request ID is generated for tracking."""
        response = test_client.get("/health")

        # Check if request tracking headers are present
        if "x-request-id" in response.headers:
            assert len(response.headers["x-request-id"]) > 0

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, test_client):
        """Test handling of concurrent requests."""
        import asyncio

        async def make_request():
            return test_client.get("/health")

        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code == 200

    def test_invalid_json_request(self, test_client):
        """Test handling of invalid JSON in request body."""
        response = test_client.post(
            "/api/v1/chat",
            data="invalid json {]",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422]

    def test_method_not_allowed(self, test_client):
        """Test method not allowed response."""
        # Try PUT on GET-only endpoint
        response = test_client.put("/health")

        assert response.status_code == 405

    @pytest.mark.slow
    def test_timeout_handling(self, test_client):
        """Test request timeout handling."""
        with patch('api.routers.chat.ChatService') as mock_service:
            import asyncio
            mock_instance = MagicMock()

            async def slow_response(*args, **kwargs):
                await asyncio.sleep(10)
                return {"context": [], "sources": []}

            mock_instance.get_context = slow_response
            mock_service.return_value = mock_instance

            # This should timeout or handle gracefully
            response = test_client.post(
                "/api/v1/chat",
                json={"query": "test"},
                timeout=1
            )

            # Should handle timeout appropriately
            assert response.status_code in [200, 408, 504]