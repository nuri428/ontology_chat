# API 문서

Ontology Chat API의 상세한 사용법을 안내합니다.

## 🔗 기본 정보

- **Base URL**: `http://localhost:8000`
- **API 문서**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc`

## 📋 엔드포인트 목록

### 1. 채팅 API

#### POST /chat
채팅 질의를 처리하고 종합적인 답변을 반환합니다.

**Request:**
```json
{
  "query": "최근 지상무기 관련 수출 기사로 유망한 종목은?"
}
```

**Response:**
```json
{
  "query": "최근 지상무기 관련 수출 기사로 유망한 종목은?",
  "answer": "## 🔍 질의 분석\n**원본 질의**: 최근 지상무기 관련 수출 기사로 유망한 종목은?\n...",
  "sources": [
    {
      "title": "로봇에 꽂힌 기업들… 정부도 규제 없앤다",
      "url": "https://v.daum.net/v/20250916001848465",
      "created_date": "2025-09-16"
    }
  ],
  "graph_samples": [...],
  "graph_summary": {...},
  "stock": {...},
  "meta": {
    "total_latency_ms": 1250.5,
    "services_attempted": ["opensearch", "neo4j", "stock_api"],
    "system_health": {...}
  }
}
```

### 2. MCP 도구 API

#### POST /mcp/call
MCP 도구를 직접 호출합니다.

**Request:**
```json
{
  "tool": "search_news",
  "args": {
    "query": "한화",
    "limit": 5
  }
}
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "took": 3,
    "hits": {
      "total": {"value": 3045},
      "hits": [...]
    }
  }
}
```

#### POST /mcp/query_graph_default
기본 그래프 검색을 수행합니다.

**Request:**
```json
{
  "q": "한화",
  "domain": "방산",
  "lookback_days": 180,
  "limit": 10
}
```

**Response:**
```json
{
  "ok": true,
  "data": [
    {
      "n": {...},
      "labels": ["Company"],
      "ts": "2025-09-16T00:00:00Z",
      "all_relationships": [...]
    }
  ]
}
```

#### GET /mcp/describe
사용 가능한 MCP 도구 목록을 반환합니다.

**Response:**
```json
{
  "tools": [
    {
      "name": "search_news",
      "description": "뉴스 검색 도구",
      "parameters": {...}
    }
  ]
}
```

### 3. 헬스 체크 API

#### GET /health/live
기본 서비스 상태를 확인합니다.

**Response:**
```json
{
  "status": "ok"
}
```

#### GET /health/ready
모든 서비스의 준비 상태를 확인합니다.

**Response:**
```json
{
  "status": "ready",
  "neo4j": {
    "database": "news-def-topology",
    "ok": true,
    "current_database": [{"name": "news-def-topology"}],
    "databases": [...]
  },
  "opensearch": true,
  "stock": true
}
```

## 🔧 사용 예시

### cURL 예시

```bash
# 기본 채팅
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "한화 관련 최근 뉴스는?"}'

# 뉴스 검색
curl -X POST "http://localhost:8000/mcp/call" \
  -H "Content-Type: application/json" \
  -d '{"tool": "search_news", "args": {"query": "지상무기", "limit": 3}}'

# 그래프 검색
curl -X POST "http://localhost:8000/mcp/query_graph_default" \
  -H "Content-Type: application/json" \
  -d '{"q": "한화", "limit": 5}'

# 헬스 체크
curl http://localhost:8000/health/ready
```

### Python 예시

```python
import requests

# 채팅 API 호출
response = requests.post(
    "http://localhost:8000/chat",
    json={"query": "최근 지상무기 관련 수출 기사로 유망한 종목은?"}
)
data = response.json()
print(data["answer"])

# 뉴스 검색
response = requests.post(
    "http://localhost:8000/mcp/call",
    json={
        "tool": "search_news",
        "args": {"query": "한화", "limit": 5}
    }
)
news_data = response.json()
```

### JavaScript 예시

```javascript
// 채팅 API 호출
const response = await fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: '한화 관련 최근 뉴스는?'
  })
});

const data = await response.json();
console.log(data.answer);
```

## 📊 응답 형식

### 성공 응답
- **HTTP Status**: 200
- **Content-Type**: `application/json`
- **Body**: 요청에 따른 데이터

### 오류 응답
- **HTTP Status**: 4xx, 5xx
- **Content-Type**: `application/json`
- **Body**:
  ```json
  {
    "detail": "오류 메시지",
    "error_code": "ERROR_CODE"
  }
  ```

## ⚡ 성능 지표

| 엔드포인트 | 평균 응답시간 | 최대 처리량 |
|------------|---------------|-------------|
| `/chat` | 1.2초 | 10 req/s |
| `/mcp/call` | 50ms | 100 req/s |
| `/mcp/query_graph_default` | 100ms | 50 req/s |
| `/health/*` | 10ms | 1000 req/s |

## 🔒 인증

현재 버전에서는 인증이 구현되지 않았습니다. 향후 버전에서 JWT 기반 인증이 추가될 예정입니다.

## 📝 제한사항

- **요청 크기**: 최대 1MB
- **응답 크기**: 최대 10MB
- **동시 연결**: 최대 100개
- **Rate Limiting**: 분당 1000 요청

## 🐛 오류 코드

| 코드 | 설명 | 해결 방법 |
|------|------|-----------|
| 400 | 잘못된 요청 | 요청 형식 확인 |
| 404 | 리소스 없음 | 엔드포인트 확인 |
| 500 | 서버 오류 | 서버 로그 확인 |
| 503 | 서비스 불가 | 의존성 서비스 확인 |

## 📞 지원

API 사용 중 문제가 발생하면:
1. GitHub Issues에 버그 리포트
2. 로그 확인: `docker logs ontology-chat-api-dev`
3. 헬스 체크: `curl http://localhost:8000/health/ready`



