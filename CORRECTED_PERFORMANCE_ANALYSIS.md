# 성능 분석 수정 보고서

**날짜**: 2025-10-02
**중요**: 이전 분석에서 잘못된 Neo4j 인스턴스를 확인한 오류를 수정합니다.

---

## ❌ 이전 분석의 오류

### 잘못된 부분
- **확인한 Neo4j**: localhost:7687 (빈 데이터베이스)
- **실제 Neo4j**: 192.168.0.10:7687/news-def-topology
- **결과**: "Neo4j에 데이터가 없다"는 잘못된 결론

---

## ✅ 수정된 분석

### 실제 Neo4j 상태 (192.168.0.10:7687/news-def-topology)

```
📊 데이터 규모:
- 총 노드: 52,848개
- 총 관계: 62,955개
- 레이블: 12개 (Company, News, Event, Evidence 등)
- 인덱스: 19개 (주요 필드 모두 인덱싱 완료)

📊 주요 레이블별 노드 수:
- Evidence: 27,927개
- News: 11,450개
- Program: 4,432개
- Event: 4,177개
- Company: 3,878개
- Agency: 398개
- Country: 283개
- Product: 183개
- Contract: 120개
```

### Neo4j 쿼리 성능 테스트 결과

| 쿼리 타입 | 평균 시간 | 평가 |
|---------|---------|------|
| 단순 회사 검색 | 46ms | ✅ 우수 |
| 부분 매칭 검색 | 44ms | ✅ 우수 |
| 회사-이벤트 관계 | 73ms | ✅ 우수 |
| 최근 뉴스 조회 | 67ms | ✅ 우수 |
| 비교 쿼리 | 225ms | ✅ 양호 |
| 집계 쿼리 | 56-137ms | ✅ 양호 |

**결론**: ✅ **Neo4j 쿼리는 병목이 아닙니다** (모두 < 250ms)

---

## 🔍 실제 병목 지점

### LangGraph 워크플로우 분석

```
LangGraph 실행 흐름 (comprehensive 모드):

1. analyze_query (쿼리 분석)
   - 키워드 추출: LLM 1회 (~1-2초)
   - 복잡도 판단: LLM 1회 (~1-2초)
   ⏱️ 소계: 2-4초

2. collect_parallel_data (데이터 수집)
   - Neo4j 쿼리: ~50-200ms ✅
   - OpenSearch 쿼리: ~100-300ms ✅
   ⏱️ 소계: ~0.2-0.5초

3. cross_validate_contexts (검증)
   ⏱️ 소계: ~0.1-0.3초

4. generate_insights (인사이트 생성)
   - 컨텍스트 타입별 LLM 호출: 3-5회 (~3-10초)
   ⏱️ 소계: 3-10초

5. analyze_relationships (관계 분석)
   ⏱️ 소계: ~0.5-1초

6. synthesize_report (보고서 합성)
   - LLM 1회 (~1-3초)
   ⏱️ 소계: 1-3초

7. quality_check (품질 검사)
   ⏱️ 소계: ~0.1-0.2초

8. enhance_report (보고서 개선)
   - LLM 1회 (~1-3초)
   ⏱️ 소계: 1-3초

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
총 예상 시간: 8-25초
LLM 호출 횟수: 7-10회
LLM 호출 총 시간: 7-20초 (전체의 80-90%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 병목의 근본 원인

#### 1. **과도한 LLM 호출** (가장 큰 문제)
```
- 총 7-10회 LLM 호출
- CPU 기반 Ollama: 1-3초/호출
- 총 LLM 시간: 7-30초 (전체의 80-90%)

→ 이것이 15초+ 타임아웃의 주범!
```

#### 2. **CPU 기반 Ollama** (두 번째 문제)
```
현재:
- 모델: llama3.1:8b
- 실행: CPU
- 응답 시간: 1-3초/호출

GPU 사용 시:
- 실행: CUDA GPU
- 응답 시간: 0.3-0.5초/호출
- 개선: 3-6배 빠름
```

#### 3. **워크플로우 복잡도**
```
- 8개 노드 순차 실행
- 각 노드가 이전 결과 대기
- 병렬화 제한적

→ 최소 실행 시간이 높음
```

---

## 📊 성능 개선 우선순위 (수정됨)

### ❌ 불필요한 최적화
- ~~Neo4j 인덱스 추가~~ (이미 충분히 빠름)
- ~~Neo4j 쿼리 최적화~~ (병목이 아님)
- ~~OpenSearch 최적화~~ (병목이 아님)

### ✅ 필수 최적화 (효과 큰 순서)

#### 1. **GPU 기반 Ollama** 🔥 **최우선**
```
예상 효과:
- LLM 응답: 1-3초 → 0.3-0.5초/호출
- 10회 호출: 10-30초 → 3-5초
- 개선율: 70-85% 단축

구현 난이도: 중간 (Docker Compose 수정)
소요 시간: 1-2시간
```

#### 2. **LLM 호출 횟수 감소** ⚡ **높음**
```
현재:
- analyze_query: 2회 (키워드 + 복잡도)
- generate_insights: 3-5회

개선:
- analyze_query: 1회로 통합
- generate_insights: 1-2회로 축소

예상 효과:
- 10회 → 4-5회 (50% 감소)
- 시간: 10-30초 → 5-15초

구현 난이도: 쉬움
소요 시간: 2-3시간
```

#### 3. **불필요한 노드 제거** ✂️ **중간**
```
제거 가능:
- cross_validate_contexts (효과 미미)
- enhance_report (조건부 실행)

예상 효과:
- 8개 → 6개 노드
- 시간: 1-2초 단축

구현 난이도: 쉬움
소요 시간: 1-2시간
```

#### 4. **프롬프트 길이 최적화** 📝 **중간**
```
현재: 전체 컨텍스트 전달 (10KB+)
개선: 요약된 핵심 정보 (2-3KB)

예상 효과:
- LLM 응답 시간: 30-40% 단축
- 각 호출: 1-3초 → 0.7-2초

구현 난이도: 중간
소요 시간: 2-3시간
```

---

## 🎯 예상 성능 (단계별)

### 현재 (Phase 1 완료)
```
✅ 타임아웃 핸들링: 완료
✅ 빠른 핸들러 폴백: 동작

LangGraph: 15-30초 (타임아웃)
→ 폴백으로 1-3초 응답 제공
```

### Phase 2A: GPU Ollama 적용 (1일)
```
LangGraph: 15-30초 → 5-8초
✅ 대부분 8초 이내 완료
✅ 타임아웃 대폭 감소
```

### Phase 2B: LLM 호출 최적화 (1일)
```
LangGraph: 5-8초 → 3-5초
✅ 모든 질의 5초 이내
✅ A급 성능 달성
```

### Phase 2C: 추가 최적화 (1일)
```
LangGraph: 3-5초 → 2-3초
✅ 프리미엄 서비스 수준
✅ 90점 이상 품질
```

---

## 💡 즉시 적용 가능한 조치

### 1. GPU Ollama 설정 (최우선)
```dockerfile
# docker-compose.yml
services:
  ollama:
    image: ollama/ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - ollama:/root/.ollama
    ports:
      - "11434:11434"
```

### 2. LLM 호출 통합 (즉시 적용)
```python
# langgraph_report_service.py - analyze_query 개선

# 현재 (2회 호출)
keyword_response = await llm.invoke(keyword_prompt)
complexity_response = await llm.invoke(complexity_prompt)

# 개선 (1회 호출)
combined_prompt = """
다음 질의를 분석하여 JSON 형식으로 답하세요:
{
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "complexity": "shallow|standard|deep|comprehensive"
}

질의: {query}
"""
response = await llm.invoke(combined_prompt)
result = json.loads(response)
```

---

## 📝 수정된 결론

### 주요 발견 (수정)
1. ✅ **Neo4j는 빠름** (모든 쿼리 < 250ms)
2. ✅ **데이터 구조 양호** (52K 노드, 63K 관계, 19개 인덱스)
3. ⚠️ **실제 병목: LLM 호출** (7-10회 × 1-3초 = 7-30초)
4. 🔥 **근본 원인: CPU 기반 Ollama**

### 최우선 조치
1. **GPU Ollama 적용** → **70-85% 성능 향상**
2. **LLM 호출 감소** → **50% 호출 횟수 감소**
3. **불필요한 노드 제거** → **추가 1-2초 단축**

### 예상 최종 성능
- **현재**: 15-30초 (타임아웃)
- **GPU 적용**: 5-8초
- **완전 최적화**: 2-3초
- **목표 달성**: ✅ A급 (3초 이내)

---

**작성**: 2025-10-02
**중요**: 이 보고서가 정확한 분석입니다. 이전 보고서의 "Neo4j 데이터 없음"은 오류였습니다.
