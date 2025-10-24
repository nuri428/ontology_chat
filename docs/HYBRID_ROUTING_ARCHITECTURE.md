# 하이브리드 라우팅 아키텍처

**날짜:** 2025-10-02
**버전:** 1.0
**작성자:** Claude Code

---

## 📋 목차

1. [개요](#개요)
2. [아키텍처 설계](#아키텍처-설계)
3. [핵심 컴포넌트](#핵심-컴포넌트)
4. [복잡도 판단 로직](#복잡도-판단-로직)
5. [엔드포인트 명세](#엔드포인트-명세)
6. [사용 예시](#사용-예시)
7. [성능 특성](#성능-특성)

---

## 개요

### 🎯 목적

사용자 질문의 복잡도에 따라 최적의 처리 경로를 자동으로 선택하는 하이브리드 라우팅 시스템

### 🔑 핵심 가치

- **단순 질문:** 빠른 응답 (1.5초 이내, A급 품질)
- **복잡한 질문:** Multi-Agent LangGraph (5초+, 심층 분석 보고서)
- **자동 판단:** 사용자가 의식하지 못하도록 투명한 라우팅
- **MCP 통합:** 외부 클라이언트에서도 동일한 기능 사용 가능

---

## 아키텍처 설계

### 전체 흐름도

```
사용자 질문
    ↓
QueryRouter (복잡도 분석)
    ↓
┌───────────────┬──────────────────┐
│               │                  │
│ 복잡도 < 0.7  │  복잡도 ≥ 0.7   │
│               │   또는           │
│               │  심층분석 키워드 │
│               │                  │
↓               ↓                  ↓
빠른 핸들러     LangGraph Multi-Agent
(1.5초)        (5초+, 7단계 파이프라인)
│               │
├─ NewsHandler  ├─ analyze_query
├─ StockHandler ├─ collect_parallel_data
└─ GeneralQA   ├─ cross_validate_contexts
                ├─ generate_insights
                ├─ analyze_relationships
                ├─ synthesize_report
                └─ quality_check
                        ↓
                   (재시도 or 완료)
```

### 기술 스택

| 레이어 | 기술 |
|--------|------|
| 라우팅 | QueryRouter (자체 구현) |
| 의도 분류 | IntentClassifier (규칙 기반) |
| 빠른 핸들러 | NewsHandler, StockHandler |
| Multi-Agent | LangGraph (StateGraph) |
| 데이터 소스 | Neo4j, OpenSearch, RDB (MCP Adapters) |
| LLM | OllamaLLM (llama3.1:8b) |

---

## 핵심 컴포넌트

### 1. QueryRouter

**파일:** `api/services/query_router.py`

**역할:**
- 질문 복잡도 분석
- 의도 분류 (뉴스, 주식분석, 일반QA)
- 최적 핸들러로 라우팅

**주요 메서드:**

```python
class QueryRouter:
    def __init__(self, chat_service, response_formatter, langgraph_engine=None):
        """
        Args:
            chat_service: 빠른 응답용 서비스
            response_formatter: 응답 포맷터
            langgraph_engine: Multi-Agent 엔진 (선택)
        """

    async def process_query(
        self,
        query: str,
        user_id: str = "anonymous",
        session_id: str = None,
        force_deep_analysis: bool = False
    ) -> Dict[str, Any]:
        """
        메인 엔트리포인트

        Returns:
            {
                "type": "news_inquiry" | "langgraph_analysis",
                "markdown": "응답 텍스트",
                "meta": {
                    "processing_method": "multi_agent_langgraph" | "legacy",
                    "complexity_score": 0.0-1.0,
                    "analysis_depth": "shallow" | "standard" | "deep" | "comprehensive"
                }
            }
        """
```

### 2. LangGraphReportEngine

**파일:** `api/services/langgraph_report_service.py`

**역할:**
- Multi-Agent 워크플로우 실행
- 7단계 분석 파이프라인

**워크플로우:**

1. **analyze_query** - 쿼리 분석 및 전략 수립
2. **collect_parallel_data** - 병렬 데이터 수집 (Neo4j + OpenSearch + Stock)
3. **cross_validate_contexts** - 컨텍스트 교차 검증
4. **generate_insights** - 인사이트 생성
5. **analyze_relationships** - 관계 분석
6. **synthesize_report** - 보고서 통합 작성
7. **quality_check** - 품질 검증 (필요시 재시도)

---

## 복잡도 판단 로직

### 계산 공식

```python
def _analyze_query_complexity(self, query: str, intent_result) -> float:
    """
    복잡도 점수 계산 (0.0 - 1.0)

    Returns:
        0.0-0.5: 단순 질문
        0.5-0.7: 중간 복잡도
        0.7-1.0: 복잡한 질문 (Multi-Agent 필요)
    """
    score = 0.0

    # 1. 길이 기반 (최대 0.3)
    if len(query) > 80:
        score += 0.3
    elif len(query) > 50:
        score += 0.2

    # 2. 복잡한 키워드 감지 (최대 0.4)
    complex_keywords = ["비교", "분석", "전망", "트렌드", "보고서", "종합"]
    matched = sum(1 for kw in complex_keywords if kw in query)
    score += min(0.4, matched * 0.15)

    # 3. 의도 신뢰도 (최대 0.3)
    if intent_result.confidence < 0.6:
        score += 0.2

    # 4. 다중 엔티티 (최대 0.3)
    companies = ["삼성", "LG", "SK", "현대", ...]
    if sum(1 for c in companies if c in query) >= 2:
        score += 0.3

    return min(1.0, score)
```

### 심층분석 키워드

자동으로 LangGraph 사용하는 키워드:

```python
deep_keywords = [
    "상세히", "자세히", "보고서", "종합 분석", "비교 분석",
    "심층", "깊이", "전문적", "완벽한", "전체적"
]
```

### 예시

| 질문 | 복잡도 | 라우팅 |
|------|--------|--------|
| "삼성전자 뉴스" | 0.20 | ⚡ 빠른 핸들러 |
| "2차전지 관련 뉴스" | 0.20 | ⚡ 빠른 핸들러 |
| "삼성전자와 SK하이닉스 비교 분석" | 0.80 | 🤖 LangGraph |
| "HBM 시장 전망 보고서 작성" | 0.50 (키워드) | 🤖 LangGraph |
| "삼성 LG SK 비교 분석 보고서" | 0.90 | 🤖 LangGraph |

---

## 엔드포인트 명세

### 1. `/chat` (메인 엔드포인트)

**하이브리드 라우팅 채팅**

```bash
POST /chat
Content-Type: application/json

{
  "query": "사용자 질문",
  "user_id": "user123",
  "session_id": "session456",
  "force_deep_analysis": false
}
```

**응답:**

```json
{
  "type": "news_inquiry" | "langgraph_analysis",
  "markdown": "# 응답 내용\n...",
  "meta": {
    "processing_time_ms": 1500,
    "processing_method": "multi_agent_langgraph",
    "complexity_score": 0.85,
    "analysis_depth": "deep",
    "quality_score": 0.92
  }
}
```

### 2. `/mcp/chat` (MCP 클라이언트용)

**외부 MCP 클라이언트에서 사용**

```bash
POST /mcp/chat
Content-Type: application/json

{
  "query": "삼성전자 뉴스",
  "user_id": "mcp_client",
  "force_deep_analysis": false
}
```

**응답:**

```json
{
  "ok": true,
  "result": {
    "type": "news_inquiry",
    "markdown": "...",
    "meta": {...}
  }
}
```

### 3. `/mcp/report/langgraph` (보고서 생성)

**명시적 Multi-Agent 보고서 요청**

```bash
POST /mcp/report/langgraph
Content-Type: application/json

{
  "query": "삼성전자 분석",
  "analysis_depth": "standard",
  "lookback_days": 30,
  "symbol": "005930"
}
```

**분석 깊이:**
- `shallow`: 기본 정보만
- `standard`: 일반 분석 (기본값)
- `deep`: 심화 분석
- `comprehensive`: 종합 분석

### 4. `/mcp/report/simple` (간단한 보고서)

**템플릿 기반 빠른 보고서**

```bash
POST /mcp/report/simple
Content-Type: application/json

{
  "query": "2차전지 시장",
  "lookback_days": 30
}
```

---

## 사용 예시

### Python 클라이언트

```python
import requests

# 1. 단순 질문 (빠른 응답)
response = requests.post("http://localhost:8000/chat", json={
    "query": "삼성전자 뉴스"
})
print(response.json()["markdown"])

# 2. 복잡한 질문 (자동 Multi-Agent)
response = requests.post("http://localhost:8000/chat", json={
    "query": "삼성전자와 SK하이닉스 HBM 시장 비교 분석 보고서"
})
result = response.json()
print(f"처리 방식: {result['meta']['processing_method']}")
print(f"품질 점수: {result['meta']['quality_score']}")

# 3. 강제 심층 분석
response = requests.post("http://localhost:8000/chat", json={
    "query": "2차전지",
    "force_deep_analysis": True
})

# 4. MCP 엔드포인트 사용
response = requests.post("http://localhost:8000/mcp/chat", json={
    "query": "삼성전자 뉴스",
    "user_id": "external_client"
})
print(response.json()["result"]["markdown"])
```

### cURL

```bash
# 단순 질문
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "삼성전자 뉴스"}'

# 복잡한 질문 (자동 Multi-Agent)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "삼성전자와 SK하이닉스 비교 분석"}'

# MCP 보고서
curl -X POST http://localhost:8000/mcp/report/langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "query": "삼성전자 분석",
    "analysis_depth": "deep",
    "lookback_days": 30
  }'
```

---

## 성능 특성

### 응답 시간

| 처리 경로 | 평균 응답 시간 | 품질 |
|----------|--------------|------|
| 빠른 핸들러 | 1.5초 | A급 (0.9+) |
| LangGraph (shallow) | 3-5초 | 높음 (0.85+) |
| LangGraph (standard) | 5-8초 | 매우 높음 (0.90+) |
| LangGraph (deep) | 8-15초 | 최고 (0.95+) |
| LangGraph (comprehensive) | 15-30초 | 최고 (0.95+) |

### 비용 (LLM 호출 횟수)

| 처리 경로 | LLM 호출 횟수 |
|----------|--------------|
| 빠른 핸들러 | 0-1회 |
| LangGraph (shallow) | 3-5회 |
| LangGraph (standard) | 5-8회 |
| LangGraph (deep) | 8-12회 |

### 적용 비율 (예상)

- **빠른 핸들러:** 90% (단순 질문)
- **LangGraph:** 10% (복잡한 질문)

---

## 테스트

### 빠른 테스트 실행

```bash
# 복잡도 계산 및 라우팅 로직 테스트
uv run python test_quick_hybrid.py

# pytest 기반 통합 테스트
uv run pytest tests/test_hybrid_routing.py -v
```

### 테스트 결과 예시

```
📊 복잡도 계산 테스트
============================================================

📝 질문: 삼성전자 뉴스
   예상: 단순
   복잡도: 0.20
   라우팅: ⚡ 빠른 핸들러

📝 질문: 삼성전자와 SK하이닉스 비교 분석
   예상: 복잡
   복잡도: 0.80
   라우팅: 🤖 LangGraph Multi-Agent
```

---

## 향후 개선 방향

1. **복잡도 판단 개선**
   - 사용자 피드백 기반 학습
   - ML 모델 도입 (BERT 기반 분류기)

2. **캐싱 전략**
   - 유사 질문 캐싱
   - LangGraph 중간 결과 캐싱

3. **성능 최적화**
   - LangGraph 병렬화 강화
   - 빠른 핸들러 속도 개선 (1초 이내)

4. **품질 개선**
   - LangGraph 프롬프트 최적화
   - 컨텍스트 엔지니어링 강화

---

## 참고 문서

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [MCP 프로토콜](https://modelcontextprotocol.io/)
- `CLAUDE.md` - 프로젝트 규칙
- `README_MCP.md` - MCP 통합 가이드

---

**마지막 업데이트:** 2025-10-02
**버전:** 1.0
