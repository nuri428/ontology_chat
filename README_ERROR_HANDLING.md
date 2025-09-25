# Enhanced Error Handling and Resilience

## Overview
Comprehensive error handling system implementing Circuit Breaker pattern, advanced retry mechanisms, and graceful service degradation to ensure system reliability and A-grade quality standards.

## Components

### 🔧 Circuit Breaker (`api/utils/circuit_breaker.py`)
Prevents cascading failures by failing fast when services are unavailable.

**Features:**
- Three states: CLOSED, OPEN, HALF_OPEN
- Configurable failure thresholds
- Automatic recovery testing
- Performance metrics tracking
- Thread-safe async implementation

**Usage:**
```python
from api.utils import circuit_breaker, CircuitBreakerConfig

@circuit_breaker("service_name", CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60.0,
    timeout=30.0
))
async def unreliable_service():
    # Service implementation
    pass
```

**Configuration:**
```python
CircuitBreakerConfig(
    failure_threshold=5,      # Failures to open circuit
    recovery_timeout=60.0,    # Seconds before half-open retry
    success_threshold=3,      # Successes to close circuit
    timeout=30.0,            # Request timeout
    expected_exception=(Exception,)  # Exceptions that count as failures
)
```

### 🔄 Retry Handler (`api/utils/retry_handler.py`)
Advanced retry mechanisms with multiple backoff strategies.

**Features:**
- Multiple backoff strategies (Fixed, Linear, Exponential, Exponential with Jitter)
- Configurable retry conditions
- Success/failure metrics
- Conditional retries based on return values
- Support for both sync and async functions

**Usage:**
```python
from api.utils import retry_async, RetryConfig, BackoffStrategy

@retry_async(RetryConfig(
    max_attempts=3,
    backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
    retryable_exceptions=(ConnectionError, TimeoutError),
    non_retryable_exceptions=(ValueError,)
))
async def flaky_operation():
    # Operation that might fail
    pass
```

**Pre-configured Decorators:**
```python
@retry_on_connection_error(max_attempts=3)
@retry_on_http_error(max_attempts=5)
@retry_database_operation(max_attempts=5)
```

### 🛡️ Graceful Degradation (`api/utils/graceful_degradation.py`)
Manages service degradation levels and fallback mechanisms.

**Service Levels:**
- **FULL**: All features available
- **DEGRADED**: Some features disabled
- **MINIMAL**: Only core features
- **EMERGENCY**: Emergency mode only

**Features:**
- Automatic degradation based on error rates
- Fallback response caching
- Service recovery mechanisms
- Performance-based level adjustments

**Usage:**
```python
from api.utils import graceful_degradation, FallbackConfig

@graceful_degradation("service_name", FallbackConfig(
    enable_cache_fallback=True,
    cache_duration=300.0,
    timeout_threshold=5.0
))
async def service_function():
    # Service implementation
    pass
```

## Enhanced ChatService

### 📡 `EnhancedChatService` (`api/services/enhanced_chat_service.py`)
Integrates all error handling mechanisms into the core chat service.

**Key Features:**
- Circuit breakers for Neo4j, OpenSearch, and LLM services
- Graceful degradation for each service component
- Comprehensive fallback responses
- Performance metrics tracking
- Health status monitoring

**Error Handling Flow:**
```
Request → Circuit Breaker Check → Service Call → Retry Logic → Degradation Check → Fallback Response
```

**Fallback Strategies:**
1. **Cache Fallback**: Return cached results from previous successful calls
2. **Simplified Processing**: Use rule-based processing instead of LLM
3. **Default Responses**: Provide informative default responses
4. **Emergency Mode**: Minimal functionality with user notifications

## Health Monitoring

### 🏥 Health Router (`api/routers/health_router.py`)
Comprehensive health check endpoints for monitoring system status.

**Endpoints:**
- `GET /health/` - Basic health check
- `GET /health/detailed` - Detailed system health with all components
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/circuit-breakers` - Circuit breaker status
- `GET /health/degradation` - Service degradation status
- `GET /health/performance` - Performance metrics
- `POST /health/reset` - Reset all error handling mechanisms

**Health Status Levels:**
- **healthy**: All systems operational
- **degraded**: Some services degraded but functional
- **critical**: Critical services down

## Configuration Examples

### Production Configuration
```python
# Circuit Breaker for Neo4j
neo4j_config = CircuitBreakerConfig(
    failure_threshold=7,
    recovery_timeout=45.0,
    success_threshold=3,
    timeout=15.0
)

# Retry for API calls
api_retry_config = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=30.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
    retryable_exceptions=(ConnectionError, TimeoutError)
)

# Degradation for chat service
chat_degradation_config = FallbackConfig(
    enable_cache_fallback=True,
    cache_duration=600.0,  # 10 minutes
    timeout_threshold=8.0
)
```

## Performance Metrics

### Circuit Breaker Metrics
```json
{
  "name": "neo4j_service",
  "state": "closed",
  "total_requests": 1000,
  "total_failures": 5,
  "failure_rate": 0.005,
  "circuit_open_calls": 0,
  "last_failure_time": null
}
```

### Retry Metrics
```json
{
  "total_attempts": 150,
  "total_successes": 145,
  "total_failures": 5,
  "success_rate": 0.967
}
```

### Degradation Status
```json
{
  "services": {
    "neo4j_search": {"level": "full"},
    "opensearch_search": {"level": "degraded"},
    "llm_processing": {"level": "minimal"}
  },
  "degraded_services": ["opensearch_search", "llm_processing"]
}
```

## A-Grade Quality Impact

### Quality Score Calculation
The error handling system contributes to A-grade quality (0.900+ score) through:

```python
quality_score = (
    relevance_score * 0.4 +          # Enhanced by fallback accuracy
    diversity_score * 0.35 +         # Maintained through degraded processing
    speed_score * 0.15 +             # Improved by circuit breakers
    reliability_score * 0.1          # Enhanced by error handling
)
```

### Quality Targets
- **Response Time**: <1.5s average (maintained through circuit breakers)
- **Error Rate**: <1% (achieved through retry mechanisms)
- **Availability**: >99.5% (ensured by graceful degradation)
- **User Experience**: Consistent (fallback responses prevent errors)

## Testing

### Unit Tests (`tests/unit/test_error_handling.py`)
Comprehensive test suite covering:
- Circuit breaker state transitions
- Retry logic and backoff strategies
- Degradation level changes
- Integration between components
- Performance under load

**Run Tests:**
```bash
pytest tests/unit/test_error_handling.py -v
```

### Integration Tests
```bash
pytest tests/integration/ -m error_handling
```

## Monitoring and Alerts

### Key Metrics to Monitor
- Circuit breaker state changes
- Retry attempt rates
- Service degradation events
- Response time percentiles
- Error rate trends

### Alert Conditions
- Circuit breaker opens (immediate alert)
- Service degrades to MINIMAL level
- Error rate > 5% for 5 minutes
- Response time > 3 seconds average

## Best Practices

### 1. Service Design
- Design services to fail fast
- Implement proper timeout handling
- Use idempotent operations where possible
- Provide meaningful error messages

### 2. Configuration
- Set realistic timeout values
- Configure appropriate retry attempts
- Use exponential backoff with jitter
- Implement proper circuit breaker thresholds

### 3. Monitoring
- Monitor circuit breaker states
- Track retry success rates
- Alert on degradation events
- Measure end-to-end response times

### 4. Testing
- Test failure scenarios regularly
- Validate fallback responses
- Perform chaos engineering tests
- Verify recovery mechanisms

## Troubleshooting

### Common Issues

1. **Circuit Breaker Stuck Open**
   - Check service health
   - Verify recovery timeout settings
   - Review failure threshold configuration

2. **Excessive Retries**
   - Adjust max retry attempts
   - Review retryable exceptions
   - Check backoff strategy

3. **Service Always Degraded**
   - Check error rate calculations
   - Verify service metrics
   - Review degradation thresholds

### Debug Commands
```bash
# Check circuit breaker status
curl /health/circuit-breakers

# View degradation status
curl /health/degradation

# Reset error handling
curl -X POST /health/reset

# View detailed health
curl /health/detailed
```

## Future Enhancements

### Planned Features
1. **Adaptive Thresholds**: Machine learning-based threshold adjustment
2. **Distributed Circuit Breakers**: Cross-instance circuit breaker state
3. **Advanced Metrics**: Histograms and percentile tracking
4. **Custom Fallback Strategies**: Service-specific fallback logic
5. **Integration with Alerting**: Direct integration with monitoring systems

### Performance Optimizations
1. **Async Metrics Collection**: Non-blocking metrics updates
2. **Memory-Efficient State Storage**: Optimized state management
3. **Batch Health Checks**: Efficient health monitoring
4. **Intelligent Preemptive Degradation**: Proactive service degradation

This comprehensive error handling system ensures the Ontology Chat application maintains A-grade quality standards even under adverse conditions, providing users with consistent and reliable service.