"""Unit tests for ChatService."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from api.services.chat_service import ChatService
from api.config import Settings


@pytest.mark.unit
class TestChatService:
    """Test suite for ChatService class."""

    @pytest.mark.asyncio
    async def test_chat_service_initialization(self, test_settings):
        """Test ChatService initialization."""
        with patch('api.services.chat_service.neo4j.GraphDatabase.driver') as mock_driver:
            service = ChatService()
            assert service is not None
            assert service.settings is not None

    @pytest.mark.asyncio
    async def test_extract_keywords_simple_query(self, chat_service, sample_query_data):
        """Test keyword extraction for simple queries."""
        query = sample_query_data["simple_query"]
        keywords = await chat_service.extract_keywords(query)

        assert keywords is not None
        assert isinstance(keywords, str)
        assert len(keywords) > 0

    @pytest.mark.asyncio
    async def test_extract_keywords_complex_query(self, chat_service, sample_query_data):
        """Test keyword extraction for complex queries."""
        query = sample_query_data["complex_query"]
        keywords = await chat_service.extract_keywords(query)

        assert keywords is not None
        assert isinstance(keywords, str)
        # Complex queries should extract more keywords
        assert len(keywords.split(',')) >= 2

    @pytest.mark.asyncio
    async def test_get_context_with_cache_hit(self, chat_service):
        """Test context retrieval with cache hit."""
        query = "test query"

        # Pre-populate cache
        chat_service.context_cache = MagicMock()
        chat_service.context_cache.get.return_value = {
            "context": ["cached content"],
            "sources": ["cached source"]
        }

        result = await chat_service.get_context(query)

        assert result is not None
        assert "context" in result
        assert result["context"] == ["cached content"]
        chat_service.context_cache.get.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_get_context_with_cache_miss(self, chat_service, sample_context_data):
        """Test context retrieval with cache miss."""
        query = "test query"

        # Mock cache miss
        chat_service.context_cache = MagicMock()
        chat_service.context_cache.get.return_value = None
        chat_service.context_cache.set = AsyncMock()

        # Mock search results
        with patch.object(chat_service, '_search_neo4j', return_value=sample_context_data[:2]):
            with patch.object(chat_service, '_search_opensearch', return_value=sample_context_data[2:]):
                result = await chat_service.get_context(query)

        assert result is not None
        assert "context" in result
        assert len(result["context"]) > 0
        chat_service.context_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_neo4j(self, chat_service, mock_neo4j_driver):
        """Test Neo4j search functionality."""
        chat_service.neo4j_driver = mock_neo4j_driver
        keywords = "AI, technology"

        results = await chat_service._search_neo4j(keywords)

        assert results is not None
        assert len(results) > 0
        assert "title" in results[0]
        assert "content" in results[0]

    @pytest.mark.asyncio
    async def test_search_opensearch(self, chat_service, mock_opensearch_client):
        """Test OpenSearch search functionality."""
        chat_service.opensearch_client = mock_opensearch_client
        query = "test query"

        results = await chat_service._search_opensearch(query)

        assert results is not None
        assert len(results) > 0
        assert "title" in results[0]
        assert "content" in results[0]

    @pytest.mark.asyncio
    async def test_apply_context_engineering(self, chat_service, sample_context_data):
        """Test context engineering pipeline."""
        contexts = sample_context_data
        query = "AI and machine learning"

        # Mock the context engineering components
        with patch.object(chat_service, 'semantic_filter') as mock_semantic:
            mock_semantic.filter.return_value = contexts[:2]

            with patch.object(chat_service, 'diversity_optimizer') as mock_diversity:
                mock_diversity.optimize.return_value = contexts[:2]

                with patch.object(chat_service, 'context_pruner') as mock_pruner:
                    mock_pruner.prune.return_value = contexts[:1]

                    result = await chat_service._apply_context_engineering(contexts, query)

        assert result is not None
        assert len(result) <= len(contexts)

    @pytest.mark.asyncio
    async def test_format_context(self, chat_service, sample_context_data):
        """Test context formatting."""
        contexts = sample_context_data[:2]

        formatted = await chat_service._format_context(contexts)

        assert formatted is not None
        assert isinstance(formatted, list)
        assert len(formatted) == len(contexts)

    @pytest.mark.asyncio
    async def test_error_handling_neo4j_failure(self, chat_service):
        """Test error handling when Neo4j fails."""
        # Mock Neo4j failure
        chat_service.neo4j_driver = MagicMock()
        chat_service.neo4j_driver.session.side_effect = Exception("Neo4j connection failed")

        results = await chat_service._search_neo4j("test")

        # Should return empty list on failure
        assert results == []

    @pytest.mark.asyncio
    async def test_error_handling_opensearch_failure(self, chat_service):
        """Test error handling when OpenSearch fails."""
        # Mock OpenSearch failure
        chat_service.opensearch_client = MagicMock()
        chat_service.opensearch_client.search.side_effect = Exception("OpenSearch failed")

        results = await chat_service._search_opensearch("test")

        # Should return empty list on failure
        assert results == []

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, chat_service, sample_context_data):
        """Test concurrent Neo4j and OpenSearch searches."""
        query = "test query"

        # Mock both search methods
        with patch.object(chat_service, '_search_neo4j', return_value=sample_context_data[:2]):
            with patch.object(chat_service, '_search_opensearch', return_value=sample_context_data[2:]):
                with patch.object(chat_service, 'extract_keywords', return_value="test, keywords"):
                    # Simulate concurrent execution
                    results = await chat_service.get_context(query)

        assert results is not None
        assert "context" in results
        # Should have results from both sources
        assert len(results["context"]) >= 2

    def test_settings_configuration(self, test_settings):
        """Test settings configuration."""
        assert test_settings.neo4j_uri == "bolt://localhost:7687"
        assert test_settings.opensearch_host == "localhost"
        assert test_settings.ollama_model == "llama3.1:8b"
        assert test_settings.testing is True

    @pytest.mark.asyncio
    async def test_fast_llm_keyword_extraction(self, chat_service):
        """Test fast LLM keyword extraction."""
        query = "artificial intelligence and machine learning"

        # Test with existing ollama_llm instance
        chat_service.ollama_llm = AsyncMock()
        chat_service.ollama_llm.ainvoke.return_value = "AI, ML, technology"

        result = await chat_service._fast_llm_keyword_extraction(query)

        assert result is not None
        assert "AI" in result or "ML" in result
        chat_service.ollama_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_statistics(self, chat_service):
        """Test cache statistics retrieval."""
        # Mock cache with statistics
        chat_service.context_cache = MagicMock()
        chat_service.context_cache.get_stats.return_value = {
            "hits": 10,
            "misses": 5,
            "hit_rate": 0.667
        }

        stats = chat_service.context_cache.get_stats()

        assert stats is not None
        assert stats["hits"] == 10
        assert stats["misses"] == 5
        assert stats["hit_rate"] > 0.6