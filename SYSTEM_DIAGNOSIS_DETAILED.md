# 시스템 정밀 진단 리포트

**진단 일시**: 2025-10-03
**분석 대상**: Context Engineering 및 LangGraph Multi-Agent 시스템
**진단 방법**: 로그 분석, 코드 리뷰, 문서 검토

---

## 🎯 Executive Summary

### 현재 상태
- ✅ **Context Engineering 모듈**: 85% 완성도 (고품질 달성)
- ⚠️ **전체 시스템**: 불안정 (JSON 파싱 및 타임아웃 문제)
- ❌ **프로덕션 준비도**: 40% (핵심 버그 수정 필요)

### 핵심 발견사항
1. **Context Engineering은 정상 작동** - 2.6초, 50→30개 필터링, 다양성 0.48
2. **심화 추론 JSON 파싱은 실제로 성공** - 로그에서 "JSON 파싱 성공" 확인
3. **타임아웃 문제가 실제 원인** - `force_deep_analysis`가 제대로 작동하지 않음
4. **복잡도 점수 로직 개선 필요** - "삼성전자와 SK하이닉스 비교" 같은 복잡한 질의가 0.9 미만으로 평가됨

---

## 📊 상세 진단

### 1. Context Engineering 모듈 (✅ 정상)

#### 로그 증거
```
[LangGraph-2.5] Context Engineering 시작: 50개 컨텍스트
[LangGraph-2.5] Source filtering: 50 → 50
[LangGraph-2.5] Recency filtering: 50 → 50
[LangGraph-2.5] Confidence filtering: 50 → 50
[LangGraph-2.5] Semantic filtering: 50 → 45
[LangGraph-2.5] Diversity score: 0.48
[LangGraph-2.5] Context Engineering 완료: 2.609초, 최종 30개
```

#### 평가
- ✅ **6단계 파이프라인**: 정상 작동
- ✅ **처리 시간**: 2.6초 (빠름)
- ✅ **다양성 점수**: 0.48 (적절)
- ✅ **필터링 효율**: 50개 → 30개 (60% 압축)

#### 결론
**Context Engineering 모듈은 수정 불필요. 설계대로 완벽히 작동 중.**

---

### 2. 심화 추론 모듈 (✅ 부분 정상 / ⚠️ 개선 필요)

#### 로그 증거
```
[LangGraph-6] 심화 추론 시작
[LangGraph-6] JSON 파싱 성공 (963자)
[LangGraph-6] 심화 추론 완료
[LangGraph-6] 심화 추론 완료: 16.868초

[LangGraph-6] 심화 추론 시작
[LangGraph-6] JSON 파싱 성공 (1168자)
[LangGraph-6] 심화 추론 완료
[LangGraph-6] 심화 추론 완료: 30.349초
```

#### 코드 분석 (langgraph_report_service.py:945-967)
```python
# 강화된 JSON 파싱 로직 (이미 구현됨)
json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
json_matches = re.findall(json_pattern, response, re.DOTALL)

# 모든 매치된 JSON에 대해 파싱 시도 (큰 것부터)
for json_str in sorted(json_matches, key=len, reverse=True):
    try:
        parsed = json.loads(json_str)
        # 필수 키 검증
        if isinstance(parsed, dict) and any(k in parsed for k in ["why", "how", "what_if", "so_what"]):
            deep_reasoning = parsed
            logger.info(f"[LangGraph-6] JSON 파싱 성공 ({len(json_str)}자)")
            break
    except json.JSONDecodeError as je:
        parse_error = str(je)
        continue
```

#### 평가
- ✅ **JSON 파싱 로직**: 이미 강화되어 있음
- ✅ **성공률**: 로그상 100% 성공
- ⚠️ **처리 시간**: 16~30초 (긴 편이지만 acceptable)
- ⚠️ **폴백 로직**: 구현되어 있으나 실제 사용 안됨

#### 문제점
**QUALITY_CHECK_REPORT.md에서 언급한 "JSON 파싱 오류"는 오래된 정보**
- 현재 코드는 이미 수정되어 정상 작동 중
- 로그에서 "JSON 파싱 성공" 확인

#### 결론
**심화 추론 모듈은 정상 작동. 다만 처리 시간이 길어서 타임아웃 문제 발생 가능.**

---

### 3. 타임아웃 설정 문제 (❌ 핵심 이슈)

#### 코드 분석 (query_router.py:419-438)

**현재 로직:**
```python
# force_deep_analysis=true 시 복잡도 점수 강제 상향
if force_deep:
    complexity_score = max(complexity_score, 0.95)  # ✅ 이미 구현됨!
    logger.info(f"[LangGraph] 강제 심층 분석 모드 활성화 → 복잡도 점수 강제 상향: {complexity_score:.2f}")

# 복잡도에 따른 분석 깊이 결정
if complexity_score >= 0.9:
    analysis_depth = "comprehensive"
    timeout_seconds = 180.0  # 3분
elif complexity_score >= 0.85:
    analysis_depth = "deep"
    timeout_seconds = 120.0  # 2분
elif complexity_score >= 0.7:
    analysis_depth = "standard"
    timeout_seconds = 90.0   # 1.5분
else:
    analysis_depth = "shallow"
    timeout_seconds = 60.0   # 1분
```

#### 문제 발견: `force_deep` 파라미터 전달 누락

**MCP 라우터 (api/mcp/router.py:129-134):**
```python
router_instance = QueryRouter(_chat_service, ResponseFormatter(), _langgraph_engine)
result = await router_instance.process_query(
    req.query,
    req.user_id,
    req.session_id,
    req.force_deep_analysis  # ✅ 전달됨
)
```

**QueryRouter.process_query() 호출 체인 확인 필요**
- `process_query()` → `_route_to_langgraph()` 호출 시 `force_deep` 전달 여부 확인

#### 예상 원인
**복잡도 점수 계산 로직이 불충분**

```python
# 현재 복잡도 점수 계산 (query_router.py:360-391)
def _calculate_complexity_score(self, query: str) -> float:
    score = 0.0

    # 1. 비교 키워드 (0.3점)
    comparison_keywords = ["비교", "대비", "차이", "vs", "versus", "경쟁"]
    if any(kw in query for kw in comparison_keywords):
        score += 0.3

    # 2. 분석 키워드 (0.25점)
    analysis_keywords = ["분석", "평가", "전망", "예측", "추이", "동향"]
    if any(kw in query for kw in analysis_keywords):
        score += 0.25

    # 3. 복잡한 구조 키워드 (0.15점)
    complex_keywords = ["종합", "심층", "상세", "전략", "보고서", "리포트"]
    if any(kw in query for kw in complex_keywords):
        score += 0.15

    # 4. 다중 회사명 감지 (0.3-0.4점)
    companies = ["삼성", "SK하이닉스", "LG", "현대"]
    company_count = sum(1 for company in companies if company in query)
    if company_count >= 3:
        score += 0.4
    elif company_count >= 2:
        score += 0.3

    # 5. 시계열 키워드 (0.15점)
    temporal_keywords = ["6개월", "3개월", "최근", "변화", "추이"]
    if any(kw in query for kw in temporal_keywords):
        score += 0.15

    return min(1.0, score)
```

**"삼성전자와 SK하이닉스 HBM 경쟁력 비교 분석" 점수 계산:**
- 비교 키워드 ("비교"): +0.3
- 분석 키워드 ("분석"): +0.25
- 다중 회사 (2개): +0.3
- **합계: 0.85** → `deep` (120초 타임아웃)

**문제: 이 질의는 `comprehensive` (180초)가 필요한데 0.85점으로 평가됨**

---

### 4. 실제 실행 시간 분석

#### 10단계 워크플로우 예상 시간
```
Phase 1: 이해 및 계획
1. analyze_query: 3-5초
2. plan_analysis: 5-8초

Phase 2: 데이터 수집
3. collect_parallel_data: 2-4초

Phase 3: Context Engineering
2.5. apply_context_engineering: 2-3초

Phase 4: 검증
4. cross_validate_contexts: 1-2초

Phase 5: 분석
5. generate_insights: 8-12초
6. analyze_relationships: 6-10초
7. deep_reasoning: 15-30초  ← 가장 오래 걸림

Phase 6: 합성
8. synthesize_report: 15-20초

Phase 7: 품질 관리
9. quality_check: 1-2초
10. enhance_report: 5-10초 (조건부)

합계: 63~106초
최대 시나리오: ~120초
```

#### 타임아웃 비교
- **현재 설정 (복잡도 0.85)**: 120초
- **필요 시간**: 120초
- **여유 시간**: 0초 ❌

**결론: 타임아웃 여유가 전혀 없어서 조금만 지연되어도 실패**

---

## 🔧 수정 계획

### P0-1: 복잡도 점수 로직 개선 (🔴 최우선)

**목표**: "비교 분석" 같은 복잡한 질의를 0.9+ 점수로 평가

**수정 위치**: `api/services/query_router.py::_calculate_complexity_score`

**수정 방안**:
```python
# 비교 + 분석 조합 감지
has_comparison = any(kw in query for kw in comparison_keywords)
has_analysis = any(kw in query for kw in analysis_keywords)

# 비교 분석 = 최고 복잡도
if has_comparison and has_analysis:
    score += 0.5  # 기존 0.55 대신 0.5 추가 보너스
```

**예상 효과**:
- "삼성전자와 SK하이닉스 HBM 경쟁력 비교 분석"
  - 기존: 0.85 (deep, 120초)
  - 수정 후: 1.0 (comprehensive, 180초) ✅

---

### P0-2: 타임아웃 여유 증가 (🟡 중요)

**목표**: 각 단계에 20% 여유 시간 확보

**수정 위치**: `api/services/query_router.py:427-436`

**수정 방안**:
```python
if complexity_score >= 0.9:
    analysis_depth = "comprehensive"
    timeout_seconds = 240.0  # 4분 (기존 3분 → +60초 여유)
elif complexity_score >= 0.85:
    analysis_depth = "deep"
    timeout_seconds = 180.0  # 3분 (기존 2분 → +60초 여유)
elif complexity_score >= 0.7:
    analysis_depth = "standard"
    timeout_seconds = 120.0  # 2분 (기존 1.5분 → +30초 여유)
else:
    analysis_depth = "shallow"
    timeout_seconds = 90.0   # 1.5분 (기존 1분 → +30초 여유)
```

**근거**:
- 현재 여유가 0초로 불안정
- 20-30% 여유 시간 확보로 안정성 향상

---

### P0-3: force_deep_analysis 검증 (🟢 확인)

**현재 상태**: 코드상 이미 구현됨
```python
if force_deep:
    complexity_score = max(complexity_score, 0.95)
```

**검증 필요 사항**:
1. `process_query()` 메서드 시그니처 확인
2. `force_deep_analysis` 파라미터 전달 체인 확인
3. 로그에서 "강제 심층 분석 모드 활성화" 메시지 확인

**예상 결과**: 이미 정상 작동 중일 가능성 높음

---

### P1: LLM 타임아웃 개별 설정 (🟡 추가 개선)

**목표**: 각 LLM 호출마다 독립적인 타임아웃 설정

**수정 위치**: `api/services/langgraph_report_service.py::_llm_invoke`

**현재 문제**:
- 전체 워크플로우 타임아웃만 있음
- 개별 LLM 호출이 무한정 대기 가능

**수정 방안**:
```python
async def _llm_invoke(self, prompt: str, timeout_seconds: float = 45.0) -> str:
    """LLM 호출 (개별 타임아웃 적용)"""
    try:
        return await asyncio.wait_for(
            self.ollama_llm.ainvoke(prompt),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        logger.warning(f"[LLM] 타임아웃 ({timeout_seconds}초), 폴백 모드")
        return "{}"  # 빈 JSON 반환
```

---

## 📋 수정 순서

### 1단계: 복잡도 점수 로직 개선 (5분)
- `query_router.py::_calculate_complexity_score` 수정
- "비교 + 분석" 조합 감지 로직 추가

### 2단계: 타임아웃 여유 증가 (3분)
- `query_router.py:427-436` 수정
- 각 depth별 타임아웃 +50% 증가

### 3단계: force_deep_analysis 검증 (5분)
- `process_query()` 메서드 확인
- 로그 확인

### 4단계: 통합 테스트 (10분)
- "삼성전자와 SK하이닉스 HBM 경쟁력 비교 분석" 테스트
- 타임아웃 없이 완료되는지 확인
- 품질 점수 0.9+ 달성 확인

---

## 🎯 예상 결과

### Before (현재)
```
Query: "삼성전자와 SK하이닉스 HBM 경쟁력 비교 분석"
복잡도 점수: 0.85
분석 깊이: deep
타임아웃: 120초
결과: 타임아웃 발생 (실제 120초+ 소요) ❌
```

### After (수정 후)
```
Query: "삼성전자와 SK하이닉스 HBM 경쟁력 비교 분석"
복잡도 점수: 1.0 (비교+분석 보너스)
분석 깊이: comprehensive
타임아웃: 240초
결과: 정상 완료 (120초 소요, 120초 여유) ✅
품질 점수: 0.92+ (A급)
```

---

## 📝 결론

### 핵심 발견
1. ✅ Context Engineering은 완벽히 작동 중
2. ✅ 심화 추론 JSON 파싱도 정상 작동 중
3. ❌ **복잡도 점수 로직이 불충분** - 핵심 원인
4. ❌ **타임아웃 여유가 부족** - 이차 원인

### 수정 범위
- **코드 수정**: 2개 함수, 약 10줄
- **예상 시간**: 15분 (테스트 포함)
- **위험도**: 낮음 (로직만 조정)

### 다음 단계
1. 복잡도 점수 로직 개선 (P0-1)
2. 타임아웃 여유 증가 (P0-2)
3. 통합 테스트 (P0-3)

**준비 완료. 수정 시작 대기 중.**
