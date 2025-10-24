"""
복잡도 점수 계산 디버깅
"""

import re

def analyze_query_complexity(query: str) -> float:
    """복잡도 분석 (query_router와 동일한 로직)"""
    score = 0.0
    details = []

    # 1. 길이 기반 (max 0.3)
    if len(query) > 80:
        score += 0.3
        details.append(f"길이 {len(query)} > 80: +0.3")
    elif len(query) > 50:
        score += 0.2
        details.append(f"길이 {len(query)} > 50: +0.2")
    elif len(query) > 30:
        score += 0.1
        details.append(f"길이 {len(query)} > 30: +0.1")

    # 2. 복잡한 키워드 (max 0.5)
    complex_keywords = [
        "비교", "분석", "전망", "트렌드", "보고서",
        "평가", "비교분석", "동향", "예측", "전략"
    ]

    matched_keywords = [kw for kw in complex_keywords if kw in query]
    keyword_count = len(matched_keywords)

    if keyword_count >= 3:
        score += 0.5
        details.append(f"복잡 키워드 {keyword_count}개: +0.5")
    elif keyword_count >= 2:
        score += 0.4
        details.append(f"복잡 키워드 {keyword_count}개: +0.4")
    elif keyword_count == 1:
        score += 0.2
        details.append(f"복잡 키워드 {keyword_count}개: +0.2")

    # 3. 다중 엔티티 (max 0.4)
    # 간단한 패턴: "A와 B", "A, B", "A vs B" 등
    multi_entity_patterns = [
        r'.+와\s*.+',
        r'.+,\s*.+',
        r'.+vs\s*.+',
        r'.+대\s*.+',
    ]

    if any(re.search(pattern, query) for pattern in multi_entity_patterns):
        score += 0.4
        details.append("다중 엔티티 감지: +0.4")

    # 4. 시간 관련 키워드 (max 0.15)
    temporal_keywords = ["최근", "올해", "작년", "향후", "미래", "과거"]
    if any(kw in query for kw in temporal_keywords):
        score += 0.15
        details.append("시간 키워드 감지: +0.15")

    return min(1.0, score), details, matched_keywords


def requires_deep_analysis(query: str) -> bool:
    """심층 분석 필요 여부 판단"""
    # 다중 키워드 조합 감지
    trend_keywords = ["트렌드", "추이", "변화", "동향"]
    analysis_keywords = ["분석", "비교", "전략", "평가"]

    has_trend = any(kw in query for kw in trend_keywords)
    has_analysis = any(kw in query for kw in analysis_keywords)

    if has_trend and has_analysis:
        return True

    # 심층 분석이 필요한 키워드
    deep_keywords = [
        "전략적", "종합적", "상세한", "심층", "세부",
        "포트폴리오", "리스크", "시나리오", "예측 모델"
    ]

    return any(kw in query for kw in deep_keywords)


# 테스트 질의들
test_queries = [
    "삼성전자 뉴스",
    "현대차 주가",
    "AI 반도체 시장 트렌드",
    "삼성전자 SK하이닉스",
    "삼성전자와 SK하이닉스",
    "삼성전자와 SK하이닉스 비교",
    "삼성전자와 SK하이닉스 HBM 경쟁력 비교",
    "AI 반도체 시장 트렌드 분석",
]

print("=" * 100)
print("복잡도 점수 분석")
print("=" * 100)
print("")

for query in test_queries:
    score, details, matched_kw = analyze_query_complexity(query)
    deep = requires_deep_analysis(query)

    print(f"질의: {query}")
    print(f"  복잡도 점수: {score:.2f}")
    print(f"  심층 분석 필요: {deep}")

    if details:
        print(f"  상세:")
        for detail in details:
            print(f"    - {detail}")

    if matched_kw:
        print(f"  매칭된 키워드: {matched_kw}")

    # 라우팅 결정
    threshold = 0.85
    if deep or score >= threshold:
        route = f"🔴 LangGraph (심층 분석: {deep}, 복잡도: {score:.2f} >= {threshold})"
    else:
        route = f"🔵 빠른 핸들러 (심층 분석: {deep}, 복잡도: {score:.2f} < {threshold})"

    print(f"  라우팅: {route}")
    print("")

print("=" * 100)
print("임계값 분석")
print("=" * 100)
print("")
print("현재 임계값: 0.85")
print("")
print("권장 사항:")
print("1. 복잡도 0.7-0.84: 빠른 핸들러 사용 (대부분 처리 가능)")
print("2. 복잡도 0.85-0.89: LangGraph 시도 → 타임아웃 시 폴백")
print("3. 복잡도 0.90+: LangGraph 필수 (시간 오래 걸려도 품질 우선)")
print("")
