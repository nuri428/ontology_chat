# 고도화된 프롬프트 전략 (LLM 호출 8-10회 → 2-3회)

**목표**: 호출 횟수를 줄이고 각 호출의 품질과 정보 밀도를 극대화

---

## 📊 현재 LLM 호출 패턴 분석

### Phase 1: Query Analysis (2회 호출)
```python
# 호출 1: 키워드 추출
"다음 질의에서 핵심 키워드 3-5개를 추출하세요..."

# 호출 2: 복잡도 판단
"다음 질의의 분석 복잡도를 판단하세요..."
```

### Phase 2: Insights Generation (3-5회 호출)
```python
# 각 컨텍스트 타입별로 개별 호출
for ctx_type in ["news", "company", "financial"]:
    insight = await llm.invoke(generate_insight_prompt(ctx_type, data))
```

### Phase 3: Relationship Analysis (0-3회 호출)
```python
# 관계 타입별로 개별 호출
await analyze_news_company_relationship()
await analyze_financial_news_relationship()
await analyze_business_news_relationship()
```

### Phase 4: Report Generation (2회 호출)
```python
# 호출 1: 보고서 합성
final_report = await synthesize_report()

# 호출 2: 보고서 개선
enhanced_report = await enhance_report()
```

**총 8-10회 × 0.5-2초 = 4-20초**

---

## 🚀 최적화 전략: 통합 멀티태스크 프롬프트

### 전략 1: 초기 분석 통합 (2회 → 1회)

#### Before (2회 호출)
```python
# 호출 1
keywords = await llm.invoke("키워드 추출...")

# 호출 2
complexity = await llm.invoke("복잡도 판단...")
```

#### After (1회 통합 호출)
```python
unified_analysis_prompt = """
당신은 금융 시장 분석 전문가입니다. 다음 질의를 종합적으로 분석하세요.

질의: "{query}"

다음 JSON 형식으로 응답하세요:
{{
  "keywords": ["키워드1", "키워드2", "키워드3", "..."],
  "entities": {{
    "companies": ["회사명1", "회사명2"],
    "products": ["제품명1"],
    "sectors": ["산업1"]
  }},
  "complexity": "shallow|standard|deep|comprehensive",
  "analysis_requirements": {{
    "需요_시계열_분석": true/false,
    "需요_비교_분석": true/false,
    "需要_재무_분석": true/false,
    "需요_산업_동향": true/false
  }},
  "focus_areas": ["분석 초점 영역1", "영역2", "..."],
  "expected_output_type": "뉴스_요약|비교_보고서|재무_분석|시장_전망"
}}

분석 시 고려사항:
- 투자자 관점의 핵심 정보
- 시장 영향도가 높은 키워드 우선
- 분석 깊이는 질의의 구체성과 복잡도에 비례
"""

response = await llm.invoke(unified_analysis_prompt)
analysis = json.loads(response)

# 하나의 호출로 모든 정보 획득
keywords = analysis["keywords"]
complexity = analysis["complexity"]
focus_areas = analysis["focus_areas"]
requirements = analysis["analysis_requirements"]
```

**효과**:
- 4초 → 2초 (50% 단축)
- 더 풍부한 컨텍스트 (entities, requirements 추가)

---

### 전략 2: 인사이트 & 관계 분석 통합 (3-8회 → 1회)

#### Before (여러 개별 호출)
```python
# news 타입 인사이트
news_insight = await llm.invoke(news_prompt)

# company 타입 인사이트
company_insight = await llm.invoke(company_prompt)

# financial 타입 인사이트
financial_insight = await llm.invoke(financial_prompt)

# 뉴스-기업 관계
news_company_rel = await llm.invoke(relationship_prompt_1)

# 재무-뉴스 관계
financial_news_rel = await llm.invoke(relationship_prompt_2)
```

#### After (1회 통합 호출)
```python
comprehensive_analysis_prompt = """
당신은 금융 시장의 수석 애널리스트입니다. 다음 데이터를 종합 분석하여 투자 인사이트를 도출하세요.

## 질의
{query}

## 수집된 데이터

### 뉴스 데이터 (최신순 10개)
{news_contexts_summary}

### 기업 데이터
{company_contexts_summary}

### 재무 데이터
{financial_contexts_summary}

### 시장 이벤트
{event_contexts_summary}

## 분석 과제

다음 JSON 형식으로 종합 분석 결과를 제공하세요:

{{
  "market_overview": {{
    "current_situation": "시장 현황 요약 (2-3문장)",
    "key_drivers": ["주요 동인 1", "동인 2", "동인 3"],
    "sentiment": "긍정|중립|부정",
    "confidence_level": 0.0-1.0
  }},

  "company_insights": [
    {{
      "company": "회사명",
      "strengths": ["강점 1", "강점 2"],
      "weaknesses": ["약점 1", "약점 2"],
      "opportunities": ["기회 1", "기회 2"],
      "threats": ["위협 1", "위협 2"],
      "investment_thesis": "투자 논리 (100자 이내)",
      "risk_factors": ["리스크 1", "리스크 2"]
    }}
  ],

  "competitive_analysis": {{
    "market_position": {{
      "leader": ["선도 기업"],
      "challenger": ["도전 기업"],
      "follower": ["후발 기업"]
    }},
    "key_differentiators": ["차별화 요소 1", "요소 2"],
    "market_share_trends": "시장 점유율 변화 설명"
  }},

  "financial_implications": {{
    "revenue_impact": "매출 영향 예상",
    "margin_impact": "마진 영향 예상",
    "valuation_change": "밸류에이션 변화 방향",
    "key_metrics_to_watch": ["지표 1", "지표 2"]
  }},

  "relationships": [
    {{
      "type": "뉴스-기업|재무-뉴스|이벤트-시장",
      "entities": ["엔티티1", "엔티티2"],
      "relationship": "관계 설명",
      "impact": "영향도 (high|medium|low)",
      "implication": "시사점"
    }}
  ],

  "actionable_insights": [
    {{
      "insight": "핵심 인사이트 (1문장)",
      "evidence": ["근거 1", "근거 2"],
      "action": "권장 행동",
      "timeframe": "단기|중기|장기"
    }}
  ],

  "future_outlook": {{
    "short_term": "1-3개월 전망",
    "medium_term": "3-12개월 전망",
    "key_catalysts": ["촉매 요인 1", "요인 2"],
    "risks": ["주요 리스크 1", "리스크 2"]
  }}
}}

## 분석 지침

1. **데이터 기반 분석**: 제공된 데이터에서 명확한 근거를 찾아 분석
2. **투자자 관점**: 실제 투자 결정에 도움이 되는 실용적 인사이트
3. **균형 잡힌 시각**: 긍정/부정 요인 모두 고려
4. **구체적 수치**: 가능한 경우 정량적 데이터 활용
5. **시간성**: 단기/중기/장기 관점 구분
6. **리스크 강조**: 주요 불확실성과 리스크 요인 명시

분석 깊이: {complexity}
중점 영역: {focus_areas}
"""

# 단 1회 호출로 모든 인사이트와 관계 분석 완료
response = await llm.invoke(comprehensive_analysis_prompt)
comprehensive_analysis = json.loads(response)

# 풍부한 구조화된 결과
insights = comprehensive_analysis["actionable_insights"]
relationships = comprehensive_analysis["relationships"]
company_analysis = comprehensive_analysis["company_insights"]
outlook = comprehensive_analysis["future_outlook"]
```

**효과**:
- 5-8회 호출 → 1회 (80-90% 단축)
- 10-16초 → 2-3초
- **더 일관성 있는 분석** (한 번의 사고 흐름)
- **관계를 고려한 통합 인사이트** (개별 분석보다 품질 높음)

---

### 전략 3: 보고서 생성 최적화 (2회 → 1회)

#### Before (2회)
```python
# 호출 1: 초기 보고서
draft = await synthesize_report(insights, relationships)

# 호출 2: 보고서 개선
final = await enhance_report(draft)
```

#### After (1회 고품질 생성)
```python
final_report_prompt = """
당신은 투자 리서치 보고서 작성 전문가입니다. 다음 분석 결과를 바탕으로 최종 보고서를 작성하세요.

## 입력 데이터

### 종합 분석 결과
{comprehensive_analysis_json}

### 원본 질의
{original_query}

## 보고서 요구사항

출력 형식: Markdown

보고서 구조:
1. **Executive Summary** (핵심 요약, 3-5 bullet points)
2. **Market Context** (시장 배경 및 현황)
3. **Key Findings** (주요 발견사항)
   - 각 발견사항마다 근거 데이터 인용
   - 정량적 수치 우선 활용
4. **Company Analysis** (기업별 상세 분석)
   - SWOT 형식
   - 경쟁 포지셔닝
5. **Financial Implications** (재무적 시사점)
   - 매출/마진/밸류에이션 영향
6. **Investment Perspective** (투자 관점)
   - 단기/중기/장기 전망
   - 핵심 촉매 요인
   - 주요 리스크
7. **Conclusion & Recommendations** (결론 및 권고사항)

## 작성 지침

1. **명확성**: 전문 용어는 필요시에만, 설명과 함께
2. **간결성**: 핵심만 전달, 불필요한 수식어 배제
3. **구조화**: 헤딩, 서브헤딩, 리스트 적극 활용
4. **데이터 중심**: 주장마다 근거 명시
5. **실용성**: 실제 투자 결정에 도움되는 정보
6. **균형**: 긍정/부정 모두 객관적 서술
7. **전문성**: 애널리스트 수준의 깊이

출력 길이: {expected_length} (short: 500-1000자, medium: 1000-2000자, long: 2000-5000자)
대상 독자: {target_audience} (전문투자자|개인투자자|경영진)
톤: {tone} (formal|balanced|concise)

바로 보고서를 작성하세요. 추가 설명이나 메타 코멘트 없이 보고서 본문만 출력하세요.
"""

final_report = await llm.invoke(final_report_prompt)
```

**효과**:
- 4초 → 2-3초 (50% 단축)
- **더 일관성 있는 보고서** (한 번에 전체 구조 고려)
- **더 높은 품질** (초안-개선 과정의 정보 손실 없음)

---

## 🎯 최종 워크플로우 (8-10회 → 2-3회)

### New Workflow

```python
async def generate_report_optimized(query: str, contexts: List):
    """최적화된 2-3회 호출 워크플로우"""

    # ========== 호출 1: 통합 초기 분석 (2초) ==========
    initial_analysis = await llm.invoke(unified_analysis_prompt(query))
    # → keywords, complexity, focus_areas, requirements

    # ========== 데이터 수집 (병렬, LLM 없음, 0.5초) ==========
    contexts = await gather_contexts_parallel(query, initial_analysis)

    # ========== 호출 2: 종합 분석 (2-3초) ==========
    comprehensive_analysis = await llm.invoke(
        comprehensive_analysis_prompt(
            query,
            contexts,
            initial_analysis
        )
    )
    # → insights, relationships, company_analysis, outlook

    # ========== 호출 3: 최종 보고서 (2-3초) ==========
    final_report = await llm.invoke(
        final_report_prompt(
            query,
            comprehensive_analysis,
            initial_analysis
        )
    )

    return final_report

# 총 시간: 2 + 0.5 + 2.5 + 2.5 = 7-8초
# vs 현재: 15-20초
# 개선: 50-60% 단축
```

---

## 📊 예상 성능 비교

| 항목 | Before | After | 개선율 |
|-----|--------|-------|-------|
| LLM 호출 횟수 | 8-10회 | 2-3회 | 70-80% 감소 |
| 총 LLM 시간 | 10-20초 | 6-8초 | 50-60% 단축 |
| 전체 시간 | 15-25초 | 7-9초 | 50-60% 단축 |
| 타임아웃율 | 80% | <10% | 매우 개선 |

---

## ✨ 품질 향상 효과

### 1. **더 일관성 있는 분석**
- 여러 번 나눠 호출하면 문맥 단절
- 한 번에 통합 분석하면 일관된 관점 유지

### 2. **더 깊은 인사이트**
- 개별 분석: 각 영역을 독립적으로 분석
- 통합 분석: 영역 간 상호작용과 시너지 파악

### 3. **더 실용적인 결과**
- Task 지향적 프롬프트로 실제 사용 가능한 출력
- JSON 구조화로 후처리 용이

### 4. **더 나은 리스크 관리**
- 종합적 관점에서 상충 요인 파악
- 균형 잡힌 투자 관점

---

## 🚀 구현 우선순위

### Phase 1: Quick Win (2-3시간)
1. ✅ `_analyze_query` 통합 (2회 → 1회)
2. ✅ `_generate_insights` + `_analyze_relationships` 통합 (5-8회 → 1회)

**예상 효과**: 15-20초 → 8-10초

### Phase 2: 완전 최적화 (반나절)
3. ✅ `_synthesize_report` + `_enhance_report` 통합 (2회 → 1회)
4. ✅ 프롬프트 품질 검증 및 튜닝

**예상 효과**: 8-10초 → 6-8초

### Phase 3: 검증 및 개선 (1일)
5. ✅ A/B 테스트 (기존 vs 신규)
6. ✅ 품질 지표 측정
7. ✅ 프롬프트 미세 조정

**최종 목표**:
- 응답 시간: 6-8초
- 품질 점수: 0.9+
- 타임아웃: 0%

---

## 💡 핵심 원칙

### 1. **Context is King**
- 충분한 컨텍스트를 제공하면 LLM이 여러 작업을 한 번에 수행 가능
- 역할 정의, 입력 데이터, 출력 형식을 명확히

### 2. **Structure Over Stream**
- JSON 같은 구조화된 출력으로 후처리 간소화
- 일관성과 파싱 용이성

### 3. **Quality Over Quantity**
- 여러 번 짧게 < 한 번 제대로
- 정교한 프롬프트가 성능과 품질 모두 향상

### 4. **Task-Oriented Design**
- "무엇을 분석하라"가 아니라 "어떤 결과를 만들라"
- 명확한 출력 스펙이 더 나은 결과

---

**다음 단계**: 실제 구현 및 테스트
