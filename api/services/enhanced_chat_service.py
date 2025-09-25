"""Enhanced ChatService with comprehensive error handling, circuit breakers, and graceful degradation."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
import traceback

from api.config import settings
from api.services.chat_service import ChatService
from api.utils.circuit_breaker import circuit_breaker, CircuitBreakerConfig, circuit_breaker_manager
from api.utils.retry_handler import retry_async, RetryConfig, BackoffStrategy
from api.utils.graceful_degradation import graceful_degradation, FallbackConfig, degradation_manager, ServiceLevel

logger = logging.getLogger(__name__)


class EnhancedChatService(ChatService):
    """ChatService with enhanced error handling and resilience mechanisms."""

    def __init__(self):
        super().__init__()

        # Configure circuit breakers for different services
        self._setup_circuit_breakers()

        # Register services for degradation management
        self._setup_degradation_management()

        # Performance tracking
        self._performance_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "circuit_breaker_trips": 0,
            "fallback_responses": 0
        }

    def _setup_circuit_breakers(self):
        """Configure circuit breakers for various services."""
        # Neo4j circuit breaker - more tolerant due to database nature
        self.neo4j_breaker = circuit_breaker_manager.get_circuit_breaker(
            "neo4j_service",
            CircuitBreakerConfig(
                failure_threshold=7,
                recovery_timeout=45.0,
                success_threshold=3,
                timeout=15.0,
                expected_exception=(Exception,)
            )
        )

        # OpenSearch circuit breaker - fast timeout for responsiveness
        self.opensearch_breaker = circuit_breaker_manager.get_circuit_breaker(
            "opensearch_service",
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=30.0,
                success_threshold=2,
                timeout=10.0,
                expected_exception=(Exception,)
            )
        )

        # LLM circuit breaker - longer timeout for complex processing
        self.llm_breaker = circuit_breaker_manager.get_circuit_breaker(
            "llm_service",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=60.0,
                success_threshold=2,
                timeout=30.0,
                expected_exception=(Exception,)
            )
        )

        logger.info("Circuit breakers configured for all services")

    def _setup_degradation_management(self):
        """Set up graceful degradation for different service components."""
        # Register services with initial levels
        degradation_manager.register_service("neo4j_search", ServiceLevel.FULL)
        degradation_manager.register_service("opensearch_search", ServiceLevel.FULL)
        degradation_manager.register_service("llm_processing", ServiceLevel.FULL)
        degradation_manager.register_service("context_engineering", ServiceLevel.FULL)

        logger.info("Degradation management initialized")

    @graceful_degradation(
        "chat_service",
        FallbackConfig(
            enable_cache_fallback=True,
            enable_default_response=True,
            cache_duration=600.0,  # 10 minutes cache
            timeout_threshold=8.0
        )
    )
    @retry_async(RetryConfig(
        max_attempts=3,
        initial_delay=1.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
        retryable_exceptions=(ConnectionError, TimeoutError, OSError),
        non_retryable_exceptions=(ValueError, TypeError)
    ))
    async def get_context(self, query: str, **kwargs) -> Dict[str, Any]:
        """Enhanced context retrieval with comprehensive error handling."""
        start_time = time.time()
        self._performance_metrics["total_requests"] += 1

        try:
            logger.info(f"Processing query with enhanced error handling: {query[:100]}")

            # Extract keywords with error handling
            try:
                keywords = await self._safe_extract_keywords(query)
            except Exception as e:
                logger.warning(f"Keyword extraction failed: {e}, using fallback")
                keywords = self._fallback_keyword_extraction(query)

            # Parallel search with circuit breakers
            search_tasks = [
                self._safe_neo4j_search(keywords, query),
                self._safe_opensearch_search(query, keywords)
            ]

            # Execute searches concurrently with timeout
            try:
                search_results = await asyncio.wait_for(
                    asyncio.gather(*search_tasks, return_exceptions=True),
                    timeout=12.0
                )

                neo4j_results, opensearch_results = search_results

                # Handle individual search failures
                if isinstance(neo4j_results, Exception):
                    logger.warning(f"Neo4j search failed: {neo4j_results}")
                    neo4j_results = []

                if isinstance(opensearch_results, Exception):
                    logger.warning(f"OpenSearch search failed: {opensearch_results}")
                    opensearch_results = []

            except asyncio.TimeoutError:
                logger.error("Search operations timed out, using fallback")
                neo4j_results, opensearch_results = [], []

            # Combine and process results with error handling
            all_contexts = []
            if neo4j_results:
                all_contexts.extend(neo4j_results)
            if opensearch_results:
                all_contexts.extend(opensearch_results)

            if not all_contexts:
                logger.warning("No search results found, using emergency fallback")
                return self._get_emergency_response(query, keywords)

            # Apply context engineering with degradation support
            processed_contexts = await self._safe_apply_context_engineering(
                all_contexts, query, keywords
            )

            # Format response
            response = self._format_enhanced_response(
                processed_contexts, query, keywords
            )

            # Update performance metrics
            response_time = time.time() - start_time
            self._update_performance_metrics(True, response_time)

            logger.info(f"Query processed successfully in {response_time:.2f}s")
            return response

        except Exception as e:
            response_time = time.time() - start_time
            self._update_performance_metrics(False, response_time)

            logger.error(f"Critical error in get_context: {e}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")

            # Return degraded response instead of raising
            return self._get_critical_error_response(query, str(e))

    async def _safe_extract_keywords(self, query: str) -> str:
        """Safely extract keywords with fallback mechanisms."""
        try:
            # Try LLM extraction if available and circuit is closed
            if (self.ollama_llm and
                self.llm_breaker.state.value != "open"):

                async def llm_extract():
                    return await self._fast_llm_keyword_extraction(query)

                return await self.llm_breaker(llm_extract)
            else:
                # Use rule-based extraction as primary fallback
                return self._fallback_keyword_extraction(query)

        except Exception as e:
            logger.warning(f"LLM keyword extraction failed: {e}")
            return self._fallback_keyword_extraction(query)

    def _fallback_keyword_extraction(self, query: str) -> str:
        """Rule-based keyword extraction fallback."""
        # Simple but effective fallback
        import re

        # Remove common stop words and extract meaningful terms
        stop_words = {'은', '는', '이', '가', '을', '를', '의', '에', '에서', '와', '과', '하는', '하고', '있는'}
        words = re.findall(r'\b\w{2,}\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 1]

        return ' '.join(keywords[:10])  # Limit to 10 keywords

    async def _safe_neo4j_search(self, keywords: str, query: str) -> List[Dict[str, Any]]:
        """Neo4j search with circuit breaker protection."""
        async def neo4j_search():
            try:
                return await self._search_neo4j_enhanced(keywords, query)
            except Exception as e:
                logger.warning(f"Neo4j search error: {e}")
                degradation_manager.update_service_metrics("neo4j_search", False, 5.0)
                raise

        try:
            results = await self.neo4j_breaker(neo4j_search)
            degradation_manager.update_service_metrics("neo4j_search", True, 1.0)
            return results
        except Exception as e:
            logger.warning(f"Neo4j circuit breaker activated or failed: {e}")
            return []

    async def _safe_opensearch_search(self, query: str, keywords: str) -> List[Dict[str, Any]]:
        """OpenSearch search with circuit breaker protection."""
        async def opensearch_search():
            try:
                return await self._search_opensearch_enhanced(query, keywords)
            except Exception as e:
                logger.warning(f"OpenSearch search error: {e}")
                degradation_manager.update_service_metrics("opensearch_search", False, 3.0)
                raise

        try:
            results = await self.opensearch_breaker(opensearch_search)
            degradation_manager.update_service_metrics("opensearch_search", True, 1.0)
            return results
        except Exception as e:
            logger.warning(f"OpenSearch circuit breaker activated or failed: {e}")
            return []

    async def _search_neo4j_enhanced(self, keywords: str, query: str) -> List[Dict[str, Any]]:
        """Enhanced Neo4j search with better error handling."""
        try:
            # Use existing Neo4j search logic from parent class
            results = await self._search_neo4j(keywords)
            return results[:20]  # Limit results
        except Exception as e:
            logger.error(f"Neo4j search failed: {e}")
            raise

    async def _search_opensearch_enhanced(self, query: str, keywords: str) -> List[Dict[str, Any]]:
        """Enhanced OpenSearch search with better error handling."""
        try:
            # Use existing OpenSearch search logic from parent class
            results = await self._search_opensearch(query)
            return results[:20]  # Limit results
        except Exception as e:
            logger.error(f"OpenSearch search failed: {e}")
            raise

    @graceful_degradation("context_engineering", FallbackConfig(enable_cache_fallback=True))
    async def _safe_apply_context_engineering(
        self,
        contexts: List[Dict[str, Any]],
        query: str,
        keywords: str
    ) -> List[Dict[str, Any]]:
        """Apply context engineering with graceful degradation."""
        try:
            service_level = degradation_manager.get_service_level("context_engineering")

            if service_level == ServiceLevel.EMERGENCY:
                # Return first few contexts without processing
                return contexts[:3]
            elif service_level == ServiceLevel.MINIMAL:
                # Basic filtering only
                return contexts[:5]
            elif service_level == ServiceLevel.DEGRADED:
                # Simplified processing
                return await self._simplified_context_processing(contexts, query)
            else:
                # Full context engineering pipeline
                return await self._full_context_processing(contexts, query, keywords)

        except Exception as e:
            logger.warning(f"Context engineering failed: {e}, using simplified processing")
            degradation_manager.update_service_metrics("context_engineering", False, 2.0)
            return contexts[:5]  # Return first 5 contexts as fallback

    async def _simplified_context_processing(
        self,
        contexts: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """Simplified context processing for degraded mode."""
        try:
            # Basic deduplication and scoring
            seen_titles = set()
            processed = []

            for ctx in contexts:
                title = ctx.get('title', '').lower()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    ctx['simplified_score'] = len(title) * 0.1  # Simple scoring
                    processed.append(ctx)

                if len(processed) >= 8:
                    break

            return sorted(processed, key=lambda x: x.get('simplified_score', 0), reverse=True)
        except Exception as e:
            logger.error(f"Simplified context processing failed: {e}")
            return contexts[:5]

    async def _full_context_processing(
        self,
        contexts: List[Dict[str, Any]],
        query: str,
        keywords: str
    ) -> List[Dict[str, Any]]:
        """Full context engineering pipeline."""
        try:
            # Apply semantic similarity filtering
            filtered_contexts = await self._apply_semantic_similarity(contexts, query)

            # Apply diversity optimization
            diverse_contexts = await self._apply_diversity_optimization(filtered_contexts, query)

            # Apply context pruning
            pruned_contexts = await self._apply_context_pruning(diverse_contexts, query)

            degradation_manager.update_service_metrics("context_engineering", True, 1.5)
            return pruned_contexts

        except Exception as e:
            logger.warning(f"Full context processing failed: {e}")
            degradation_manager.update_service_metrics("context_engineering", False, 3.0)
            return await self._simplified_context_processing(contexts, query)

    def _format_enhanced_response(
        self,
        contexts: List[Dict[str, Any]],
        query: str,
        keywords: str
    ) -> Dict[str, Any]:
        """Format enhanced response with metadata."""
        # Calculate quality metrics
        quality_score = self._calculate_quality_score(contexts, query)

        # Get system health info
        system_health = self._get_system_health_summary()

        return {
            "context": [self._format_context_item(ctx) for ctx in contexts],
            "sources": [self._format_source_item(ctx) for ctx in contexts],
            "metadata": {
                "query": query,
                "keywords": keywords,
                "total_results": len(contexts),
                "quality_score": quality_score,
                "processing_time": time.time(),
                "system_health": system_health,
                "circuit_breakers": circuit_breaker_manager.get_all_metrics(),
                "degradation_status": degradation_manager.get_degradation_status()
            },
            "performance": self._performance_metrics.copy()
        }

    def _get_emergency_response(self, query: str, keywords: str) -> Dict[str, Any]:
        """Generate emergency response when all systems fail."""
        self._performance_metrics["fallback_responses"] += 1

        return {
            "context": [
                "I apologize, but I'm experiencing technical difficulties and cannot provide a complete response at the moment."
            ],
            "sources": [],
            "metadata": {
                "query": query,
                "keywords": keywords,
                "emergency_mode": True,
                "message": "System is in emergency mode. Please try again in a few moments.",
                "quality_score": 0.3
            },
            "performance": self._performance_metrics.copy()
        }

    def _get_critical_error_response(self, query: str, error: str) -> Dict[str, Any]:
        """Generate response for critical errors."""
        self._performance_metrics["fallback_responses"] += 1

        return {
            "context": [
                "I'm currently experiencing technical issues and cannot process your request fully. Please try again shortly."
            ],
            "sources": [],
            "error": {
                "type": "critical_error",
                "message": "Service temporarily unavailable",
                "query": query[:100],  # Truncated for safety
                "timestamp": time.time()
            },
            "metadata": {
                "emergency_mode": True,
                "quality_score": 0.2
            },
            "performance": self._performance_metrics.copy()
        }

    def _calculate_quality_score(self, contexts: List[Dict[str, Any]], query: str) -> float:
        """Calculate quality score for the response."""
        if not contexts:
            return 0.0

        # Base score from number of contexts
        base_score = min(len(contexts) / 10.0, 1.0) * 0.3

        # Relevance score (simplified)
        relevance_score = min(sum(1 for ctx in contexts if ctx.get('score', 0) > 0.5) / len(contexts), 1.0) * 0.4

        # Diversity score (simplified)
        unique_sources = len(set(ctx.get('source', 'unknown') for ctx in contexts))
        diversity_score = min(unique_sources / 3.0, 1.0) * 0.2

        # System health impact
        degraded_services = len(degradation_manager.get_degradation_status().get('degraded_services', []))
        health_score = max(0.0, 1.0 - degraded_services * 0.1) * 0.1

        total_score = base_score + relevance_score + diversity_score + health_score
        return min(max(total_score, 0.0), 1.0)

    def _get_system_health_summary(self) -> Dict[str, Any]:
        """Get summary of system health."""
        cb_metrics = circuit_breaker_manager.get_all_metrics()
        degradation_status = degradation_manager.get_degradation_status()

        open_circuits = [name for name, metrics in cb_metrics.items() if metrics['state'] == 'open']
        degraded_services = degradation_status.get('degraded_services', [])

        return {
            "overall_status": "degraded" if (open_circuits or degraded_services) else "healthy",
            "open_circuit_breakers": open_circuits,
            "degraded_services": degraded_services,
            "total_requests": self._performance_metrics["total_requests"],
            "success_rate": (
                self._performance_metrics["successful_requests"] /
                max(self._performance_metrics["total_requests"], 1)
            )
        }

    def _update_performance_metrics(self, success: bool, response_time: float):
        """Update internal performance metrics."""
        if success:
            self._performance_metrics["successful_requests"] += 1
        else:
            self._performance_metrics["failed_requests"] += 1

        # Update average response time
        total = self._performance_metrics["total_requests"]
        current_avg = self._performance_metrics["avg_response_time"]
        new_avg = ((current_avg * (total - 1)) + response_time) / total
        self._performance_metrics["avg_response_time"] = new_avg

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the service."""
        return {
            "service_status": "healthy",
            "timestamp": time.time(),
            "circuit_breakers": circuit_breaker_manager.get_all_metrics(),
            "degradation_status": degradation_manager.get_degradation_status(),
            "performance_metrics": self._performance_metrics,
            "system_health": self._get_system_health_summary()
        }

    async def reset_error_handling(self):
        """Reset all error handling mechanisms."""
        await circuit_breaker_manager.reset_all()

        # Reset degradation levels
        for service_name in ["neo4j_search", "opensearch_search", "llm_processing", "context_engineering"]:
            degradation_manager.set_service_level(service_name, ServiceLevel.FULL)

        logger.info("All error handling mechanisms reset")


# Create enhanced service instance
enhanced_chat_service = EnhancedChatService()