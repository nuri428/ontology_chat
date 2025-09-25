# Ontology Chat Test Suite

## Overview
Comprehensive test suite for the Ontology Chat application with unit, integration, and performance tests.

## Structure
```
tests/
├── unit/               # Unit tests for individual components
├── integration/        # Integration tests for API endpoints
├── performance/        # Performance benchmark tests
├── fixtures/           # Test fixtures and data
└── run_tests.sh       # Test runner script
```

## Running Tests

### Install Dependencies
```bash
pip install -e ".[dev]"  # Install with dev dependencies
```

### Run All Tests
```bash
pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# Performance tests
pytest -m performance

# Quick tests (exclude slow)
pytest -m "not slow"
```

### Run with Coverage
```bash
pytest --cov=api --cov-report=html
# View coverage report in htmlcov/index.html
```

### Using the Test Runner Script
```bash
./tests/run_tests.sh unit       # Run unit tests
./tests/run_tests.sh integration # Run integration tests
./tests/run_tests.sh performance # Run performance tests
./tests/run_tests.sh coverage    # Generate coverage report
./tests/run_tests.sh quick       # Run quick tests only
```

## Test Categories

### Unit Tests
- **Location**: `tests/unit/`
- **Purpose**: Test individual components in isolation
- **Components**: ChatService, ContextCache, etc.
- **Mocking**: Heavy use of mocks for external dependencies

### Integration Tests
- **Location**: `tests/integration/`
- **Purpose**: Test API endpoints and service interactions
- **Focus**: HTTP endpoints, database connections
- **Requirements**: May need services running

### Performance Tests
- **Location**: `tests/performance/`
- **Purpose**: Benchmark critical operations
- **Metrics**: Response time, throughput, memory usage
- **Targets**: <1.5s avg response, >60% cache hit rate

## Writing Tests

### Unit Test Example
```python
@pytest.mark.unit
class TestChatService:
    @pytest.mark.asyncio
    async def test_extract_keywords(self, chat_service):
        result = await chat_service.extract_keywords("test query")
        assert result is not None
```

### Integration Test Example
```python
@pytest.mark.integration
def test_health_endpoint(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
```

### Performance Test Example
```python
@pytest.mark.performance
async def test_response_time(chat_service, benchmark):
    result = await benchmark(chat_service.get_context, "query")
    assert benchmark.stats["mean"] < 1.5  # <1.5s average
```

## Test Configuration

### pytest.ini
Main pytest configuration with test discovery patterns and markers.

### pyproject.toml
Contains test dependencies and optional pytest configuration.

### conftest.py
Shared fixtures and test configuration (simplified to avoid import issues).

## Performance Targets
- **Response Time**: <1.5s average, <3s max
- **Cache Hit Rate**: >60%
- **Throughput**: >5 requests/second
- **Error Rate**: <1%
- **Test Coverage**: >70%

## CI/CD Integration
Tests are designed to run in CI/CD pipelines:
- Unit tests run on every commit
- Integration tests run on PR
- Performance tests run nightly
- Coverage reports generated automatically

## Known Issues
- Complex imports in conftest.py can cause timeouts
- Keep test fixtures minimal and focused
- Mock external services to avoid dependencies

## Contributing
1. Write tests for new features
2. Maintain >70% code coverage
3. Use appropriate markers for test categories
4. Keep tests fast and isolated
5. Mock external dependencies