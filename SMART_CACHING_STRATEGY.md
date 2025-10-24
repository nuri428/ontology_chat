# 스마트 캐싱 전략: 시계열 금융 데이터 대응

**문제**: 금융/뉴스 데이터는 시간에 따라 변하므로 단순 캐싱은 부적절

**해결**: 다층 캐싱 + 시의성 고려 전략

---

## 🎯 캐싱 가능/불가능 요소 분석

### ✅ 캐싱 가능 (변하지 않음)

#### 1. **쿼리 분석 결과**
```python
# 질문: "삼성전자 HBM 경쟁력"
캐시 대상:
  - 키워드 추출: ["삼성전자", "HBM", "경쟁력"]
  - 엔티티 인식: {companies: ["삼성전자"], products: ["HBM"]}
  - 의도 분류: "company_analysis"
  - 복잡도 점수: 0.87

TTL: 24시간 (질문 자체는 변하지 않음)
효과: 3초 절약 (LLM 호출 1회 제거)
```

#### 2. **기업 메타데이터**
```python
캐시 대상:
  - 삼성전자: {산업: "반도체", 주요제품: [...], 경쟁사: [...]}
  - SK하이닉스: {산업: "반도체", ...}

TTL: 7일 (기업 기본 정보는 자주 안 바뀜)
효과: Neo4j 쿼리 절약 (~200ms)
```

#### 3. **LLM 프롬프트 템플릿**
```python
캐시 대상:
  - 보고서 구조 템플릿
  - 분석 프레임워크
  - 시스템 프롬프트

TTL: 무제한 (코드 변경 시만 갱신)
```

### ❌ 캐싱 불가능 (실시간 데이터)

#### 1. **최신 뉴스 데이터**
```python
이유: 매일 새로운 뉴스 발생
해결: 캐싱 금지, 항상 실시간 조회
```

#### 2. **주가/재무 데이터**
```python
이유: 실시간으로 변동
해결: 캐싱 금지, 항상 실시간 조회
```

#### 3. **최종 보고서**
```python
이유: 최신 데이터 기반이므로 매번 달라짐
해결: 캐싱 금지 (하지만 예외 있음 - 아래 참조)
```

---

## 💡 스마트 캐싱 전략 3단계

### 전략 1: **레이어별 선택적 캐싱** ⭐ (추천)

```python
class SmartCache:
    """시의성을 고려한 다층 캐싱"""

    # Layer 1: 쿼리 이해 캐싱 (변하지 않음)
    async def cache_query_analysis(self, query: str):
        cache_key = f"query_analysis:{hash(query)}"
        ttl = 86400  # 24시간

        if cached := await redis.get(cache_key):
            logger.info("✅ Query analysis cache HIT")
            return cached

        result = await llm.analyze_query(query)
        await redis.setex(cache_key, ttl, result)
        return result

    # Layer 2: 데이터 조회 (시의성 고려)
    async def fetch_news_with_recency(self, query: str, lookback_days: int):
        """뉴스는 절대 캐싱하지 않음 - 항상 실시간"""
        return await opensearch.search(query, lookback_days)

    # Layer 3: 부분 보고서 캐싱 (준실시간)
    async def cache_partial_report(self, query: str, data_timestamp: str):
        """데이터 수집 시간 기준으로 캐싱"""
        # 같은 시간대(1시간 단위) + 같은 질문 = 캐시 가능
        hour_key = datetime.now().strftime("%Y%m%d_%H")
        cache_key = f"report:{hash(query)}:{hour_key}"
        ttl = 3600  # 1시간

        if cached := await redis.get(cache_key):
            logger.info(f"✅ Report cache HIT (시간: {hour_key})")
            return cached

        report = await generate_report(query)
        await redis.setex(cache_key, ttl, report)
        return report
```

**효과**:
- Query Analysis: 3초 절약 (캐시 히트율 70%)
- 뉴스 데이터: 캐싱 안 함 (시의성 보장)
- 보고서: 1시간 단위 캐싱 (준실시간)

**장점**:
- ✅ 시의성 유지 (최신 뉴스 반영)
- ✅ 속도 향상 (반복 질문 시)
- ✅ 비용 절감 (LLM 호출 감소)

---

### 전략 2: **시간 기반 차등 캐싱** (추천)

```python
class TimeBasedCache:
    """시간대별로 다른 TTL 적용"""

    def get_ttl_by_hour(self) -> int:
        """시간대별 TTL 결정"""
        hour = datetime.now().hour

        if 9 <= hour <= 15:  # 장중 (9:00-15:00)
            return 300  # 5분 (시장 변동성 높음)
        elif 15 < hour <= 18:  # 장 마감 후
            return 1800  # 30분 (뉴스 정리 시간)
        else:  # 장 마감 (저녁/밤/새벽)
            return 3600  # 1시간 (변동 적음)

    async def cache_with_market_hours(self, query: str):
        """시장 시간 고려 캐싱"""
        ttl = self.get_ttl_by_hour()
        cache_key = f"report:{hash(query)}:{datetime.now().strftime('%Y%m%d_%H')}"

        # 캐시 조회
        if cached := await redis.get(cache_key):
            age = await redis.ttl(cache_key)
            logger.info(f"✅ Cache HIT (남은 시간: {age}초, TTL: {ttl}초)")
            return cached

        # 신규 생성
        result = await generate_report(query)
        await redis.setex(cache_key, ttl, result)
        return result
```

**효과**:
- 장중: 5분 캐싱 (실시간성 유지)
- 장 마감 후: 1시간 캐싱 (속도 향상)
- 평균 응답 시간: 2-3초 (캐시 히트 시)

---

### 전략 3: **데이터 신선도 표시** (완벽한 해결책)

```python
class FreshnessAwareCache:
    """캐시 사용하되 데이터 신선도 명시"""

    async def generate_report_with_freshness(self, query: str):
        """보고서에 데이터 시점 명시"""

        # 1. 캐시 확인
        cache_key = f"report:{hash(query)}:{datetime.now().strftime('%Y%m%d_%H')}"
        cached = await redis.get(cache_key)

        if cached:
            cached_time = await redis.get(f"{cache_key}:timestamp")
            data_age_minutes = (datetime.now() - datetime.fromisoformat(cached_time)).seconds // 60

            # 캐시된 보고서에 신선도 정보 추가
            report = f"""# {query} 분석 보고서

> 📅 **데이터 기준 시점**: {cached_time}
> ⏰ **데이터 경과 시간**: {data_age_minutes}분 전
> 🔄 **다음 업데이트**: {60 - data_age_minutes}분 후

{cached['content']}

---
*본 보고서는 {cached_time} 시점의 데이터를 기반으로 작성되었습니다.*
*최신 정보 반영을 위해 {60 - data_age_minutes}분 후 재조회를 권장합니다.*
"""
            logger.info(f"✅ Cache HIT (데이터 나이: {data_age_minutes}분)")
            return report

        # 2. 신규 생성
        current_time = datetime.now().isoformat()
        report = await generate_report(query)

        # 신선도 정보 포함
        report_with_meta = f"""# {query} 분석 보고서

> 📅 **데이터 기준 시점**: {current_time}
> ✅ **실시간 분석**: 최신 데이터 기반

{report}

---
*본 보고서는 실시간 데이터를 기반으로 작성되었습니다.*
"""

        # 캐시 저장
        await redis.setex(cache_key, 3600, {"content": report, "timestamp": current_time})
        await redis.setex(f"{cache_key}:timestamp", 3600, current_time)

        return report_with_meta
```

**효과**:
- ✅ 속도 향상 (캐시 사용)
- ✅ 투명성 (데이터 나이 명시)
- ✅ 사용자 신뢰 (언제 데이터인지 명확)

**사용자 경험**:
```markdown
# 삼성전자 HBM 경쟁력 분석 보고서

> 📅 **데이터 기준 시점**: 2025-10-02 14:30:00
> ⏰ **데이터 경과 시간**: 15분 전
> 🔄 **다음 업데이트**: 45분 후

## Executive Summary
- 삼성전자 HBM3E 16단 개발 중...
```

---

## 📊 전략별 비교

| 전략 | 시의성 | 속도 | 구현 난이도 | 추천도 |
|------|--------|------|-------------|--------|
| 레이어별 선택적 캐싱 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 보통 | ⭐⭐⭐⭐⭐ |
| 시간 기반 차등 캐싱 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 쉬움 | ⭐⭐⭐⭐ |
| 데이터 신선도 표시 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 보통 | ⭐⭐⭐⭐⭐ |

---

## 🚀 실전 적용 방안

### Phase 1: Query Analysis 캐싱 (즉시 적용 가능)

```python
# api/services/langgraph_report_service.py

class LangGraphReportService:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6380, decode_responses=True)

    async def _analyze_query(self, state):
        """1단계: 통합 쿼리 분석 (캐싱 적용)"""

        # 캐시 확인
        cache_key = f"query_analysis:{hash(state['query'])}"
        cached = self.redis.get(cache_key)

        if cached:
            logger.info("✅ Query analysis cache HIT - 3초 절약!")
            analysis = json.loads(cached)
            state["query_analysis"] = analysis
            state["analysis_depth"] = AnalysisDepth(analysis["complexity"])
            return state

        # 기존 LLM 호출 (캐시 미스)
        logger.info("❌ Query analysis cache MISS - LLM 호출")
        # ... 기존 코드 ...

        # 결과 캐싱 (24시간)
        self.redis.setex(cache_key, 86400, json.dumps(analysis))

        return state
```

**예상 효과**:
- 첫 번째 질문: 11.6초 (변화 없음)
- 두 번째 동일 질문: **8.6초** (3초 절약!) ✅
- 캐시 히트율: 30-40% (반복 질문 많음)

### Phase 2: 시간 기반 보고서 캐싱 (1-2일)

```python
async def generate_langgraph_report(self, query: str, **kwargs):
    """LangGraph 기반 고급 리포트 생성 (스마트 캐싱)"""

    # 시간 기반 캐시 키 (1시간 단위)
    hour_key = datetime.now().strftime("%Y%m%d_%H")
    cache_key = f"report:{hash(query)}:{hour_key}"

    # 캐시 확인
    cached = self.redis.get(cache_key)
    if cached:
        cached_data = json.loads(cached)
        cached_time = cached_data["timestamp"]
        age_minutes = (datetime.now() - datetime.fromisoformat(cached_time)).seconds // 60

        logger.info(f"✅ Report cache HIT (나이: {age_minutes}분)")

        # 보고서에 신선도 정보 추가
        report = cached_data["report"]
        report["markdown"] = f"""> 📅 데이터 시점: {age_minutes}분 전\n\n{report['markdown']}"""
        return report

    # 캐시 미스 - 신규 생성
    logger.info("❌ Report cache MISS - 신규 생성")
    report = await self._generate_report_internal(query, **kwargs)

    # 캐싱 (1시간)
    cache_data = {
        "report": report,
        "timestamp": datetime.now().isoformat()
    }
    self.redis.setex(cache_key, 3600, json.dumps(cache_data, ensure_ascii=False))

    return report
```

**예상 효과**:
- 첫 질문: 11.6초
- 1시간 내 같은 질문: **0.5초** (95% 절약!) ✅
- 시의성: 유지 (1시간마다 갱신)

### Phase 3: 데이터 신선도 UI 표시 (2-3일)

프론트엔드에서 사용자에게 명확히 표시:

```markdown
# 보고서 상단 배너
┌─────────────────────────────────────────────────┐
│ 📅 데이터 기준: 14:30 (25분 전)                │
│ 🔄 다음 업데이트: 35분 후                      │
│ [지금 새로고침] 버튼                            │
└─────────────────────────────────────────────────┘
```

---

## 💰 캐싱 효과 추정

### 시나리오: 1일 1,000회 질문

| 구분 | 캐싱 전 | 캐싱 후 | 개선 |
|------|---------|---------|------|
| 평균 응답 시간 | 11.6초 | **4.5초** | **61% 개선** ✅ |
| LLM 호출 횟수 | 2,000회 | **1,400회** | 30% 감소 |
| 서버 부하 | 100% | **40%** | 60% 감소 |
| 사용자 만족도 | 보통 | **높음** | 체감 속도 ↑ |

**캐시 히트 가정**:
- Query Analysis: 70% 히트율
- Report: 30% 히트율 (1시간 내 동일 질문)

---

## ⚠️ 주의사항

### 1. **명확한 캐시 정책 표시**
```python
# 사용자에게 투명하게 공개
"본 보고서는 14:30 시점의 데이터를 기반으로 작성되었습니다."
"최신 뉴스 반영을 위해 30분마다 자동 갱신됩니다."
```

### 2. **강제 새로고침 옵션**
```python
# API에 force_refresh 파라미터 추가
POST /mcp/chat
{
  "query": "삼성전자 HBM",
  "force_refresh": true  # 캐시 무시하고 실시간 분석
}
```

### 3. **캐시 무효화 전략**
```python
# 중요 뉴스 발생 시 즉시 캐시 클리어
async def invalidate_cache_on_breaking_news(company: str):
    """특정 기업 관련 캐시 즉시 무효화"""
    pattern = f"*:{company}:*"
    keys = redis.keys(pattern)
    redis.delete(*keys)
    logger.info(f"🔥 Breaking news! Cache invalidated for {company}")
```

---

## 🎯 최종 권장안

### ✅ 즉시 적용 (오늘)
1. **Query Analysis 캐싱** (TTL: 24시간)
   - 효과: 3초 절약
   - 리스크: 없음 (쿼리는 변하지 않음)

### ✅ 단기 적용 (1-2일)
2. **시간 기반 보고서 캐싱** (TTL: 1시간)
   - 효과: 평균 4-5초로 단축
   - 리스크: 낮음 (신선도 표시 필수)

### ✅ 중기 적용 (1주일)
3. **데이터 신선도 UI 표시**
   - 효과: 사용자 신뢰 향상
   - 리스크: 없음

**예상 최종 성능**:
```yaml
캐시 미스 (첫 질문): 11.6초
캐시 히트 (반복 질문): 2-4초

평균 (캐시 히트율 30%):
  = 11.6 * 0.7 + 3 * 0.3
  = 8.1 + 0.9
  = 9초

체감 속도 (자주 묻는 질문): 2-4초 ✅
```

**결론**: 시의성을 완벽히 보장하면서도 **평균 22% 속도 향상** 가능! ✅