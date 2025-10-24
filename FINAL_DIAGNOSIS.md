# 최종 성능 진단 보고서

**날짜**: 2025-10-02
**핵심 발견**: GPU Ollama는 빠름 (0.5초), 그런데 왜 LangGraph는 느린가?

---

## 🔬 실제 측정 결과

### 1. Neo4j (192.168.0.10:7687/news-def-topology)
```
✅ 매우 빠름
- 노드: 52,848개
- 관계: 62,955개
- 모든 쿼리 < 250ms
- 인덱스 19개 (잘 구성됨)
```

### 2. Ollama LLM (192.168.0.11:11434 - RTX 4070 TI)
```
✅ GPU 사용, 매우 빠름
- 모델: llama3.1:8b
- 실제 추론 시간: 0.52초
- 전체 HTTP 요청: 2초
```

### 3. 그런데 왜 LangGraph는 15초+?

---

## 🕵️ 문제의 근본 원인

### 가능한 설명

#### 1. **LangGraph가 LLM을 8-10회 호출**
```
단일 LLM 호출: 0.5-2초
10회 호출: 5-20초

→ 이것만으로도 15초 가까이 소요 가능
```

#### 2. **Streaming vs Non-streaming**
```
측정한 테스트: stream=false (2초)
LangChain: stream=true 기본값

→ Streaming은 더 오래 걸릴 수 있음
```

#### 3. **LangChain 오버헤드**
```
직접 Ollama API: 2초
LangChain 래퍼: ?초 (추가 처리)

→ 래핑 레이어의 오버헤드 가능성
```

#### 4. **프롬프트 길이**
```
테스트 프롬프트: "키워드 3개 추출: 삼성전자 실적" (짧음)
실제 LangGraph 프롬프트: 컨텍스트 포함 (길 수 있음)

→ 긴 프롬프트는 처리 시간 증가
```

#### 5. **여러 처리 단계**
```
LangGraph 워크플로우:
1. analyze_query → LLM 2회
2. collect_parallel_data → Neo4j + OpenSearch
3. cross_validate_contexts
4. generate_insights → LLM 3-5회
5. analyze_relationships
6. synthesize_report → LLM 1회
7. quality_check
8. enhance_report → LLM 1회

각 단계 간 데이터 처리 및 변환 시간 누적
```

---

## 📊 시간 분해 추정

### 단일 LangGraph 실행 (comprehensive 모드)

| 단계 | LLM 호출 | 추정 시간 | 누적 |
|-----|---------|---------|------|
| 1. analyze_query | 2회 | 4초 | 4초 |
| 2. collect_parallel_data | 0회 | 0.5초 | 4.5초 |
| 3. cross_validate_contexts | 0회 | 0.2초 | 4.7초 |
| 4. generate_insights | 3-5회 | 6-10초 | 10.7-14.7초 |
| 5. analyze_relationships | 0회 | 0.5초 | 11.2-15.2초 |
| 6. synthesize_report | 1회 | 2초 | 13.2-17.2초 |
| 7. quality_check | 0회 | 0.2초 | 13.4-17.4초 |
| 8. enhance_report | 1회 | 2초 | **15.4-19.4초** |

**결론**: LLM이 빠르더라도 (0.5-2초/호출), **8-10회 호출하면 15-20초** 소요!

---

## ✅ 최종 결론

### GPU Ollama는 정상 작동 중
- ✅ RTX 4070 TI 사용
- ✅ 추론 속도 빠름 (0.5초)
- ✅ 서버 응답 정상 (2초)

### 실제 문제: LangGraph 설계
```
문제: 너무 많은 LLM 호출 (8-10회)
원인: 복잡한 워크플로우 설계
결과: 개별 호출이 빠르더라도 누적 시간이 길어짐
```

---

## 🎯 해결 방안 (우선순위)

### 1. **LLM 호출 횟수 대폭 감소** 🔥 최우선
```
현재: 8-10회
목표: 2-3회

방법:
A. 여러 작업을 하나의 프롬프트로 통합
   예) "키워드 추출 + 복잡도 판단 + 인사이트 생성"을 한 번에

B. 배치 처리
   예) 여러 컨텍스트를 한 번에 분석

예상 효과: 15-20초 → 4-6초 (70% 단축)
구현 시간: 반나절
```

### 2. **불필요한 LLM 호출 제거** ⚡ 높음
```
제거 가능:
- analyze_query의 복잡도 판단 (규칙 기반으로 대체)
- cross_validate_contexts (효과 미미)
- enhance_report (조건부만 실행)

예상 효과: 추가 2-4초 단축
구현 시간: 2-3시간
```

### 3. **프롬프트 최적화** 📝 중간
```
현재: 긴 컨텍스트 전체 전달
개선: 핵심 정보만 요약하여 전달

예상 효과: 각 호출 20-30% 단축
구현 시간: 3-4시간
```

### 4. **워크플로우 간소화** ✂️ 중간
```
현재: 8단계
개선: 4-5단계로 축소

노드 통합:
- analyze_query + collect_parallel_data
- generate_insights + synthesize_report

예상 효과: 처리 오버헤드 감소
구현 시간: 반나절
```

---

## 🚀 즉시 적용 가능한 Quick Win

### Quick Win 1: LLM 호출 통합 (30분)
```python
# 현재: langgraph_report_service.py
# analyze_query에서 2회 호출
keyword_response = await llm.ainvoke(keyword_prompt)  # 1회
complexity_response = await llm.ainvoke(complexity_prompt)  # 2회

# 개선: 1회로 통합
combined_prompt = """
질의: {query}

다음을 JSON 형식으로 답하세요:
{{
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "complexity": "shallow|standard|deep|comprehensive"
}}
"""
response = await llm.ainvoke(combined_prompt)
```

**예상 효과**: 4초 → 2초 (2초 단축)

### Quick Win 2: 복잡도 판단을 규칙 기반으로 (15분)
```python
# LLM 호출 제거, 규칙 기반 판단
def determine_complexity(query: str) -> str:
    if len(query) > 100 or "비교" in query and "분석" in query:
        return "comprehensive"
    elif len(query) > 50 or "분석" in query or "비교" in query:
        return "deep"
    elif len(query) > 30:
        return "standard"
    else:
        return "shallow"
```

**예상 효과**: 추가 2초 단축

### Quick Win 3: enhance_report 조건부 실행 (10분)
```python
# quality_score가 낮을 때만 enhance 실행
if quality_score < 0.7:
    enhanced = await enhance_report(report)
else:
    enhanced = report  # 그대로 사용
```

**예상 효과**: 50% 케이스에서 2초 단축

---

## 📈 최종 예상 성능

### 현재
```
LangGraph: 15-20초 → 타임아웃
→ 빠른 핸들러 폴백: 1-3초
```

### Quick Wins 적용 후 (1시간 작업)
```
LangGraph: 15-20초 → 8-10초
→ 10초 타임아웃 내에 완료 가능
→ 성공률 대폭 향상
```

### 전체 최적화 후 (1일 작업)
```
LangGraph: 8-10초 → 4-6초
→ 안정적으로 5초 타임아웃 내 완료
→ A급 성능 달성
```

---

## 🎬 Action Plan

### 즉시 (오늘 1시간)
1. ✅ analyze_query LLM 호출 통합 (2회 → 1회)
2. ✅ 복잡도 판단 규칙 기반으로 변경
3. ✅ enhance_report 조건부 실행

**예상 결과**: 15-20초 → 8-10초

### 단기 (내일 반나절)
4. generate_insights 최적화 (5회 → 2-3회)
5. 프롬프트 길이 축소
6. 불필요한 노드 제거

**예상 결과**: 8-10초 → 4-6초

### 목표
- ✅ 모든 LangGraph 질의 5초 이내
- ✅ 타임아웃 없이 안정적 응답
- ✅ A급 성능 달성

---

**핵심 메시지**:
- GPU는 이미 빠름 ✅
- 문제는 너무 많은 LLM 호출 ⚠️
- LLM 호출 횟수만 줄이면 즉시 개선 🚀
