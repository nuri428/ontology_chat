# Ontology Chat Test Suite

## Overview
Comprehensive test suite for the Ontology Chat application with unit, integration, and performance tests.

## Structure
```
tests/
├── unit/               # Unit tests for individual components
├── integration/        # Integration tests for API endpoints
├── performance/        # Performance benchmark tests
├── analysis/           # Analysis and quality assessment tests
├── experimental/       # Experimental and development tests
├── fixtures/           # Test fixtures and data
└── run_tests.sh       # Test runner script
```

### Directory Descriptions

- **unit/**: 개별 컴포넌트의 단위 테스트 (키워드 추출, LLM, 캐시 등)
- **integration/**: API 엔드포인트 및 서비스 통합 테스트 (FastAPI, MCP, 검색 등)
- **performance/**: 성능 벤치마크 및 부하 테스트
- **analysis/**: 시스템 품질 분석 및 개선점 도출 테스트
- **experimental/**: 실험적 기능 및 프로토타입 테스트 (LangGraph, 품질 실험 등)
- **fixtures/**: 테스트용 데이터 및 픽스처

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

# Analysis tests
pytest tests/analysis/ -v

# Experimental tests
pytest tests/experimental/ -v

# Quick tests (exclude slow)
pytest -m "not slow"

# Neo4j specific tests
docker exec ontology-chat-api-dev uv run python tests/integration/test_neo4j_samsung.py
docker exec ontology-chat-api-dev uv run python tests/integration/test_neo4j_direct.py

# Shell script tests
./tests/integration/test_various_queries.sh
./tests/integration/test_final.sh
./tests/integration/test_cache_api.sh
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

#### Integration Test Files
- `test_neo4j_samsung.py`: Neo4j 삼성전자 검색 직접 테스트
- `test_neo4j_direct.py`: Neo4j 쿼리 성능 직접 테스트
- `test_comprehensive_queries.py`: 종합 질의 품질 테스트
- `test_simple_chat.py`: 간단한 채팅 API 테스트
- `test_various_queries.sh`: 다양한 질의 통합 테스트 (Shell 스크립트)
- `test_final.sh`: 최종 통합 테스트 (Shell 스크립트)
- `test_cache_api.sh`: 캐시 API 테스트 (Shell 스크립트)
- `create_neo4j_indexes.cypher`: Neo4j 인덱스 생성 스크립트
- `reports/`: 테스트 결과 리포트 저장 디렉토리

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