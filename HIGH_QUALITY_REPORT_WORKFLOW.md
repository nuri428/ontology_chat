# 고품질 보고서 생성 워크플로우 설계

## 설계 원칙
- **시간보다 품질 우선**: 60초 이상 걸려도 A급 보고서 생성
- **충분한 검증 단계**: 각 단계마다 품질 검증
- **다단계 분석**: 단순 → 심화 → 종합 → 정제
- **명확한 근거**: 모든 인사이트에 데이터 출처 명시

## 새로운 12단계 워크플로우

### Phase 1: 이해 및 계획 (Understanding & Planning)
1. **analyze_query** - 쿼리 분석 및 의도 파악
2. **plan_analysis** - 분석 전략 수립 (NEW)
   - 어떤 데이터가 필요한가?
   - 어떤 관점에서 분석할 것인가?
   - 예상되는 인사이트는?

### Phase 2: 데이터 수집 (Data Collection)
3. **collect_parallel_data** - 병렬 데이터 수집
4. **enrich_context** - 컨텍스트 보강 (NEW)
   - 추가 데이터 검색 (부족한 영역)
   - 시계열 데이터 확보
   - 경쟁사 비교 데이터

### Phase 3: 검증 및 필터링 (Validation & Filtering)
5. **cross_validate_contexts** - 교차 검증
6. **fact_check** - 사실 확인 및 신뢰도 평가 (NEW)
   - 출처 신뢰성 검증
   - 상호 모순 확인
   - 최신성 검증

### Phase 4: 분석 (Analysis)
7. **generate_insights** - 인사이트 생성 (복원)
   - 데이터 기반 발견사항 도출
   - 패턴 및 트렌드 분석
8. **analyze_relationships** - 관계 분석 (복원)
   - 엔티티 간 연결성
   - 인과관계 파악
   - 시장 포지셔닝
9. **deep_reasoning** - 심화 추론 (NEW)
   - Why & How 분석
   - 시나리오 예측
   - 리스크/기회 평가

### Phase 5: 합성 (Synthesis)
10. **synthesize_report** - 보고서 초안 작성 (복원)
11. **structure_refinement** - 구조 및 논리 개선 (NEW)
    - 논리적 흐름 검증
    - 섹션 간 일관성 확인
    - Executive Summary 강화

### Phase 6: 품질 관리 (Quality Assurance)
12. **quality_check** - 품질 검사
13. **enhance_report** - 보고서 개선 (조건부)

## 각 단계별 상세 설명

### 2. plan_analysis (NEW)
**목적**: 분석 방향성 설정 및 데이터 요구사항 명확화

**입력**:
- 쿼리 분석 결과
- 감지된 엔티티

**출력**:
```python
{
    "analysis_strategy": {
        "primary_focus": ["재무 성과", "기술 경쟁력"],
        "comparison_axes": ["HBM 시장점유율", "R&D 투자"],
        "required_data_types": ["재무제표", "뉴스", "특허"],
        "expected_insights": ["시장 포지션", "성장 전망"]
    },
    "data_gaps": ["SK하이닉스 최근 3개월 재무"],
    "risk_factors": ["데이터 신선도", "편향된 보도"]
}
```

**LLM 호출**: 1회 (전략 수립)

### 4. enrich_context (NEW)
**목적**: 초기 수집에서 부족한 데이터 보강

**동작**:
1. Phase 2 결과 분석
2. 데이터 갭 식별
3. 추가 검색 쿼리 생성
4. 타겟 검색 실행

**예시**:
```python
# 초기 수집: 삼성전자 30건, SK하이닉스 5건
# → 불균형 감지 → SK하이닉스 추가 검색
```

### 6. fact_check (NEW)
**목적**: 데이터 신뢰성 및 일관성 검증

**검증 항목**:
- 출처 신뢰도 (언론사 등급)
- 날짜 최신성 (7일 이내 = 높음)
- 교차 검증 (여러 출처에서 동일 사실)
- 수치 일관성 (재무 데이터 검산)

**LLM 호출**: 1회 (모순 감지)

### 7. generate_insights (복원)
**목적**: 데이터에서 의미 있는 발견 도출

**분석 유형**:
- Quantitative: 수치 기반 비교
- Qualitative: 정성적 평가
- Temporal: 시간에 따른 변화
- Comparative: 경쟁사 대비

**LLM 호출**: 2-3회 (각 유형별)

### 8. analyze_relationships (복원)
**목적**: 엔티티 간 연결성 및 영향 관계 파악

**분석 대상**:
- 공급망 관계
- 경쟁 구도
- 이벤트 간 인과관계
- 시장 의존성

**LLM 호출**: 1-2회

### 9. deep_reasoning (NEW)
**목적**: 단순 사실을 넘어 심층 추론

**분석 질문**:
- Why: 왜 이런 현상이 발생했는가?
- How: 어떤 메커니즘으로 작동하는가?
- What if: 만약 X가 발생하면?
- So what: 투자자에게 의미하는 바는?

**LLM 호출**: 2-3회 (복잡한 추론)

### 11. structure_refinement (NEW)
**목적**: 보고서 논리 구조 및 가독성 최적화

**개선 항목**:
- Executive Summary 강화
- 섹션 간 전환 자연스럽게
- 핵심 메시지 명확화
- 데이터 시각화 제안
- 투자 권고 구체화

**LLM 호출**: 1회 (편집자 관점)

## 예상 성능

### 시간 (복잡도: comprehensive)
- Phase 1 (이해): 8-10초
- Phase 2 (수집): 5-8초
- Phase 3 (검증): 3-5초
- Phase 4 (분석): 20-30초
- Phase 5 (합성): 10-15초
- Phase 6 (품질): 5-8초
**합계: 51-76초** (1분 ~ 1분 15초)

### LLM 호출 횟수
- 기존: 2-3회
- 신규: 10-15회
- **품질 우선, 시간 무관**

### 품질 목표
- A급 (0.9+): 80% 이상
- 평균 점수: 0.92+
- 재시도율: < 5%

## 타임아웃 정책
```python
# 품질 우선: 타임아웃 대폭 증가
if analysis_depth == "comprehensive":
    timeout_seconds = 120.0  # 2분
elif analysis_depth == "deep":
    timeout_seconds = 90.0   # 1.5분
elif analysis_depth == "standard":
    timeout_seconds = 60.0   # 1분
else:
    timeout_seconds = 45.0   # 45초
```

## 품질 지표

### 1. 데이터 커버리지
- 모든 주요 엔티티 언급
- 다양한 출처 (뉴스, 재무, 이벤트)
- 시계열 분석 포함

### 2. 분석 깊이
- 단순 사실 나열 (X)
- Why/How 설명 (O)
- 시나리오 예측 포함

### 3. 구조 완결성
- Executive Summary (필수)
- 섹션별 명확한 주제
- 데이터 기반 결론
- 실행 가능한 권고

### 4. 신뢰성
- 모든 주장에 출처 명시
- 수치 검증 완료
- 편향 최소화

## 구현 우선순위

### P0 (즉시)
- plan_analysis 추가
- generate_insights 복원
- analyze_relationships 복원
- 타임아웃 증가

### P1 (다음)
- enrich_context 구현
- fact_check 구현
- deep_reasoning 구현
- structure_refinement 구현

### P2 (향후)
- 시각화 제안 기능
- 다국어 보고서
- 템플릿 커스터마이징
