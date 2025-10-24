# 시스템 성능 분석 및 병목 지점 식별 보고서

**작성일**: 2025-10-02
**분석 방법**: 실제 운영 시스템 엔드포인트 테스트 및 프로파일링

---

## 🎯 핵심 발견사항 (Executive Summary)

### ✅ **잘 작동하는 부분**
1. **단순 질의 (뉴스 조회)**: ~200ms - 매우 빠름, 상업적 가치 높음
2. **적절한 라우팅 로직**: 복잡도 판단이 정확하게 작동
3. **답변 품질**: 구조화된 마크다운, 적절한 길이, 유용한 정보 제공

### ❌ **심각한 문제**
1. **LangGraph 타임아웃**: 복잡한 비교 질의 시 15초+ 소요 → **타임아웃 발생**
2. **사용자 경험 저하**: 비교/분석 질문에 답변을 못함
3. **상업화 불가**: 현재 상태로는 유료 서비스 제공 불가

---

## 📊 실제 테스트 결과

### Test 1: 단순 질의 - "삼성전자 뉴스"
```
✅ 성공
- 응답 시간: 192.8ms (처리 시간)
- 의도 분류: news_inquiry (신뢰도 0.36)
- 답변 길이: 약 1000자
- 뉴스 건수: 5건
- 구조: 마크다운 포맷, 링크 포함

평가: A급 - 매우 빠르고 유용한 답변
```

**실제 답변 예시**:
```markdown
## 📰 뉴스 조회 결과 - 삼성전자

### 🔍 핵심 요약
**삼성전자** 관련하여 5건의 뉴스를 찾았습니다.

### 📋 주요 뉴스
1. **이재용 삼성전자 회장 무죄 확정, 삼성전자 서초사옥 모습**
   *뉴시스 | 네이버*
   🔗 [기사 보기](https://n.news.naver.com/mnews/article/003/0013369363...)

2. **삼성전자 뉴욕서 테크포럼**
   *연합뉴스 | 네이버*
   ...
```

### Test 2: 중간 복잡도 질의 - "AI 반도체 시장"
```
✅ 성공
- 응답 시간: 208.4ms
- 의도 분류: news_inquiry
- 라우팅: 빠른 핸들러 사용 (올바른 판단)

평가: A급 - 복잡도 판단이 적절하게 작동
```

### Test 3: 복잡한 비교 질의 - "삼성전자와 SK하이닉스 비교"
```
❌ 실패 (타임아웃)
- 응답 시간: 15초+ (타임아웃)
- 라우팅: LangGraph Multi-Agent로 전달됨
- 결과: 응답 없음

평가: F급 - 사용 불가, 긴급 최적화 필요
```

### Test 4: 유사 질의를 빠른 핸들러로 처리 - "삼성전자 뉴스 SK하이닉스 뉴스"
```
✅ 성공
- 응답 시간: 947.7ms
- 의도 분류: news_inquiry
- 라우팅: 빠른 핸들러 사용

평가: B급 - 1초 이내, 비교는 아니지만 관련 정보 제공 가능
```

---

## 🔍 병목 지점 분석

### 1. **LangGraph Multi-Agent 워크플로우**

**문제**: "비교" 키워드가 포함된 질의에서 15초+ 타임아웃

**추정 원인** (우선순위 순):

#### A. **데이터 수집 단계가 느림** (가능성 70%)
```
예상 시나리오:
1. 복잡도 점수 계산 → 0.7+ (비교 키워드 감지)
2. LangGraph 워크플로우 시작
3. Research Agent: 삼성전자 데이터 수집 (5초)
4. Research Agent: SK하이닉스 데이터 수집 (5초)
5. Analysis Agent: 비교 분석 시작... (타임아웃)

문제점:
- 데이터 수집이 순차적으로 실행되고 있을 가능성
- Neo4j 쿼리가 복잡하거나 인덱스 부족
- OpenSearch 검색이 대용량 결과 반환
```

**검증 필요**:
- [ ] LangGraph 각 에이전트별 실행 시간 로깅
- [ ] Neo4j 쿼리 EXPLAIN 분석
- [ ] OpenSearch 쿼리 프로파일링

#### B. **LLM 호출 횟수가 많음** (가능성 20%)
```
예상 시나리오:
- Research Agent: 각 회사별 데이터 분석 (2회 LLM 호출, 각 3초)
- Analysis Agent: 비교 분석 (1회 LLM 호출, 3초)
- Report Agent: 최종 보고서 (1회 LLM 호출, 3초)
→ 총 4회 × 3초 = 12초+

문제점:
- Ollama 응답이 느림 (CPU 기반?)
- 프롬프트가 너무 길어서 처리 시간 증가
```

**검증 필요**:
- [ ] Ollama 모델 응답 시간 측정
- [ ] GPU 사용 여부 확인
- [ ] 프롬프트 길이 최적화

#### C. **워크플로우 설계 문제** (가능성 10%)
```
가능성:
- 불필요한 에이전트 실행
- 에이전트 간 데이터 전달 오버헤드
- 동기적 실행 (병렬 처리 미적용)
```

---

## 💡 최적화 방안 (우선순위)

### 🔥 **즉시 적용 (긴급)**

#### 1. **타임아웃 핸들링 추가**
```python
# api/services/query_router.py

async def _route_to_langgraph(self, query, intent_result, tracker, complexity_score):
    """LangGraph 라우팅 with timeout"""
    try:
        result = await asyncio.wait_for(
            self.langgraph_engine.generate_langgraph_report(query),
            timeout=10.0  # 10초 타임아웃
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"[라우터] LangGraph 타임아웃 → 빠른 핸들러로 폴백")
        # 폴백: 빠른 핸들러 사용
        return await self._handle_fallback_fast(query, tracker)
```

**효과**: 타임아웃 시 최소한 답변 제공 가능
**구현 시간**: 10분
**우선순위**: ⚠️ **최우선**

#### 2. **복잡도 임계값 상향 조정**
```python
# api/services/query_router.py

# 현재: 0.7 이상 → LangGraph
# 변경: 0.85 이상 → LangGraph

if force_deep_analysis or complexity_score >= 0.85 or requires_deep:
    # LangGraph 사용
```

**효과**: 대부분의 비교 질의를 빠른 핸들러로 처리
**구현 시간**: 5분
**우선순위**: ⚠️ **최우선**

#### 3. **LangGraph 실행 로깅 추가**
```python
# api/services/langgraph_report_service.py

async def generate_langgraph_report(self, query, ...):
    logger.info(f"[LangGraph] 시작: {query}")
    start = time.time()

    # Research Agent
    logger.info(f"[LangGraph] Research Agent 시작")
    research_start = time.time()
    research_result = await self.research_agent(...)
    logger.info(f"[LangGraph] Research Agent 완료: {time.time() - research_start:.3f}초")

    # Analysis Agent
    logger.info(f"[LangGraph] Analysis Agent 시작")
    ...
```

**효과**: 실제 병목 지점 정확히 파악
**구현 시간**: 15분
**우선순위**: 🔥 **긴급**

### 📈 **단기 최적화 (1-2일)**

#### 4. **데이터 수집 병렬화**
```python
# 순차 실행 (현재 - 추정)
samsung_data = await research_agent("삼성전자")  # 5초
sk_data = await research_agent("SK하이닉스")      # 5초

# 병렬 실행 (최적화)
samsung_task = research_agent("삼성전자")
sk_task = research_agent("SK하이닉스")
samsung_data, sk_data = await asyncio.gather(samsung_task, sk_task)  # 5초
```

**효과**: 50% 시간 단축 (10초 → 5초)
**우선순위**: 🚀 **높음**

#### 5. **Neo4j 쿼리 최적화**
```cypher
-- 인덱스 확인 및 추가
SHOW INDEXES;

-- 필요시 인덱스 생성
CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name);
CREATE INDEX news_published IF NOT EXISTS FOR (n:News) ON (n.published_at);
```

**효과**: 데이터 수집 속도 향상
**우선순위**: 🚀 **높음**

#### 6. **LLM 프롬프트 최적화**
```python
# 현재 (추정)
prompt = f"""
다음 데이터를 분석하세요:
{전체_뉴스_내용}  # 10KB+
...
"""

# 최적화
prompt = f"""
다음 요약을 분석하세요:
{요약된_핵심_정보}  # 2KB
...
"""
```

**효과**: LLM 응답 시간 30-50% 단축
**우선순위**: 🚀 **높음**

### 🔧 **중기 최적화 (1주)**

#### 7. **캐싱 도입**
```python
from functools import lru_cache
from datetime import datetime, timedelta

@cache_decorator.cached(ttl=300)  # 5분 캐시
async def research_agent(company_name: str):
    # 동일한 회사 조회 시 캐시 사용
    ...
```

**효과**: 반복 질의 시 10배+ 속도 향상
**우선순위**: 중간

#### 8. **GPU 기반 Ollama 사용**
```bash
# 현재 (CPU)
ollama run llama3.1:8b

# 최적화 (GPU)
# Docker에서 GPU 활성화
docker run --gpus all -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

**효과**: LLM 응답 시간 3-5배 단축
**우선순위**: 중간

---

## 📈 상업적 가치 평가

### 현재 상태

| 질의 유형 | 응답 시간 | 품질 | 상업화 가능성 |
|---------|---------|-----|------------|
| 단순 뉴스 조회 | ~200ms | A급 | ✅ **즉시 가능** |
| 중간 복잡도 | ~200ms | A급 | ✅ **즉시 가능** |
| 복잡한 비교/분석 | 15초+ (타임아웃) | F급 | ❌ **불가능** |

### 최적화 후 예상

| 질의 유형 | 응답 시간 | 품질 | 상업화 가능성 |
|---------|---------|-----|------------|
| 단순 뉴스 조회 | ~200ms | A급 | ✅ **프리미엄** |
| 중간 복잡도 | ~200ms | A급 | ✅ **프리미엄** |
| 복잡한 비교/분석 (빠른 핸들러) | ~1초 | B급 | ✅ **가능** |
| 복잡한 비교/분석 (LangGraph 최적화) | ~5초 | A급 | ✅ **프리미엄+** |

### 수익 모델 제안

#### 무료 티어
- 단순 뉴스 조회: 무제한
- 일일 질의 제한: 10회

#### 프리미엄 티어 ($9.99/월)
- 모든 질의: 무제한
- 빠른 응답 보장
- 심층 분석 제외

#### 프로 티어 ($29.99/월)
- 모든 기능 무제한
- LangGraph 심층 분석 포함
- API 액세스 제공

---

## 🎯 Action Plan

### Phase 1: 긴급 수정 (오늘)
- [ ] 타임아웃 핸들링 추가 (10분)
- [ ] 복잡도 임계값 조정 (5분)
- [ ] LangGraph 로깅 추가 (15분)
- [ ] 실제 병목 지점 측정 (30분)

### Phase 2: 단기 최적화 (1-2일)
- [ ] 데이터 수집 병렬화
- [ ] Neo4j 쿼리 최적화
- [ ] LLM 프롬프트 최적화
- [ ] 목표: 복잡한 질의 5초 이내

### Phase 3: 중기 최적화 (1주)
- [ ] 캐싱 도입
- [ ] GPU 기반 Ollama
- [ ] 목표: 복잡한 질의 3초 이내

### Phase 4: 상업화 준비 (2주)
- [ ] 성능 모니터링 대시보드
- [ ] 품질 메트릭 자동화
- [ ] 부하 테스트 (100 req/s)
- [ ] SLA 정의 (99.9% uptime)

---

## 📝 결론

**현재 시스템**:
- ✅ 단순 질의: 상업화 즉시 가능 (A급 성능)
- ❌ 복잡한 질의: 상업화 불가 (타임아웃 문제)

**긴급 조치** (오늘 필수):
1. 타임아웃 핸들링으로 최소한 답변 제공
2. 복잡도 임계값 조정으로 더 많은 질의를 빠른 핸들러로 처리
3. 실제 병목 지점 측정 및 확인

**목표** (1주 내):
- 모든 질의 5초 이내 응답
- 품질 B급 이상 유지
- 상업화 가능한 수준 달성

**예상 결과**:
- Phase 1 완료 시: 80% 질의 응답 가능
- Phase 2 완료 시: 100% 질의 5초 이내 응답
- Phase 3 완료 시: 프리미엄 서비스 제공 가능
