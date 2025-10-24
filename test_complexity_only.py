"""
복잡도 계산 전용 테스트 (빠른 실행)
실제 질의 처리 없이 복잡도 점수만 계산
"""

from api.services.query_router import QueryRouter
from api.services.chat_service import ChatService
from api.services.langgraph_report_service import LangGraphReportEngine
from api.services.response_formatter import ResponseFormatter
from api.services.intent_classifier import classify_query_intent


# 테스트 케이스
TEST_QUESTIONS = [
    # (질문, 예상 라우팅, 카테고리)
    ("삼성전자 뉴스", "fast", "단순 뉴스"),
    ("2차전지 관련 뉴스", "fast", "단순 뉴스"),
    ("방산주", "fast", "단순 조회"),
    ("SK하이닉스 최근 소식", "fast", "단순 뉴스"),
    ("에코프로", "fast", "단순 조회"),

    ("현대차 전기차 사업 현황은?", "fast", "중간 복잡도"),
    ("AI 반도체 관련 종목 추천", "fast", "중간 복잡도"),
    ("삼성전자 최근 실적 발표 내용", "fast", "중간 복잡도"),

    ("삼성전자와 SK하이닉스 비교 분석", "langgraph", "비교 분석"),
    ("HBM 시장에서 삼성전자와 SK하이닉스의 경쟁력 분석 보고서", "langgraph", "심층 보고서"),
    ("2차전지 산업 투자 전망 보고서 작성해줘", "langgraph", "심층 보고서"),
    ("삼성전자 LG전자 현대차 실적 비교 분석", "langgraph", "다중 비교"),
    ("AI 반도체 시장 트렌드와 주요 기업들의 전략 비교", "langgraph", "트렌드 분석"),
    ("방산 산업 주요 종목들의 최근 6개월 실적 변화 추이 분석", "langgraph", "추이 분석"),

    ("삼성전자 SK하이닉스 마이크론의 HBM 기술 경쟁력과 시장 점유율 종합 비교 분석 보고서를 상세히 작성해줘", "langgraph", "종합 분석"),
    ("전기차 배터리 산업의 밸류체인 분석과 주요 기업별 포지셔닝 전략 보고서", "langgraph", "밸류체인 분석"),
    ("2024년 반도체 시장 회복 전망과 삼성전자 SK하이닉스의 투자 전략 비교", "langgraph", "전망 분석"),

    ("PER이 뭐야?", "fast", "일반 QA"),
    ("배당수익률 높은 종목", "fast", "단순 조회"),
    ("요즘 핫한 종목은?", "fast", "트렌드 조회"),
]


def test_complexity():
    """복잡도 계산 테스트"""

    print("\n" + "=" * 100)
    print("📊 하이브리드 라우팅 복잡도 계산 테스트")
    print("=" * 100)

    # 라우터 초기화 (서비스는 None으로)
    print("\n초기화 중...")
    chat_service = ChatService()
    langgraph_engine = LangGraphReportEngine()
    router = QueryRouter(chat_service, ResponseFormatter(), langgraph_engine)

    results = []
    correct = 0
    total = len(TEST_QUESTIONS)

    print("\n" + "=" * 100)
    print("테스트 실행")
    print("=" * 100)

    for i, (query, expected_route, category) in enumerate(TEST_QUESTIONS, 1):
        # 의도 분류
        intent_result = classify_query_intent(query)

        # 복잡도 계산
        complexity = router._analyze_query_complexity(query, intent_result)
        requires_deep = router._requires_deep_analysis(query)

        # 라우팅 결정
        will_use_langgraph = complexity >= 0.7 or requires_deep
        actual_route = "langgraph" if will_use_langgraph else "fast"

        # 정답 확인
        is_correct = actual_route == expected_route
        if is_correct:
            correct += 1

        # 결과 저장
        results.append({
            "query": query,
            "category": category,
            "expected": expected_route,
            "actual": actual_route,
            "complexity": complexity,
            "requires_deep": requires_deep,
            "is_correct": is_correct,
        })

        # 진행 상황 출력
        status = "✅" if is_correct else "❌"
        route_symbol = "🤖" if actual_route == "langgraph" else "⚡"

        print(f"\n[{i:2d}/{total}] {status} {route_symbol} [{category}]")
        print(f"       질문: {query}")
        print(f"       복잡도: {complexity:.2f} | 심층키워드: {requires_deep}")
        print(f"       예상: {expected_route.upper():10s} | 실제: {actual_route.upper():10s}")

        if not is_correct:
            print(f"       ⚠️  불일치!")

    # 요약 통계
    print("\n\n" + "=" * 100)
    print("📈 테스트 결과 요약")
    print("=" * 100)

    accuracy = (correct / total * 100) if total > 0 else 0
    print(f"\n✅ 전체 정확도: {correct}/{total} ({accuracy:.1f}%)")

    # 카테고리별 정확도
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "correct": 0}
        categories[cat]["total"] += 1
        if r["is_correct"]:
            categories[cat]["correct"] += 1

    print("\n📊 카테고리별 정확도:")
    for cat, stats in sorted(categories.items()):
        cat_acc = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"   {cat:20s}: {stats['correct']:2d}/{stats['total']:2d} ({cat_acc:5.1f}%)")

    # 라우팅별 통계
    fast_count = sum(1 for r in results if r["actual"] == "fast")
    langgraph_count = sum(1 for r in results if r["actual"] == "langgraph")

    print(f"\n⚡ 라우팅 분포:")
    print(f"   빠른 핸들러: {fast_count:2d}건 ({fast_count/total*100:.1f}%)")
    print(f"   LangGraph:   {langgraph_count:2d}건 ({langgraph_count/total*100:.1f}%)")

    # 복잡도 분포
    print("\n📊 복잡도 분포:")
    bins = [
        ("0.0-0.3 (매우 단순)", 0.0, 0.3),
        ("0.3-0.5 (단순)", 0.3, 0.5),
        ("0.5-0.7 (중간)", 0.5, 0.7),
        ("0.7-0.9 (복잡)", 0.7, 0.9),
        ("0.9-1.0 (매우 복잡)", 0.9, 1.0),
    ]

    for bin_name, min_val, max_val in bins:
        count = sum(1 for r in results if min_val <= r["complexity"] < max_val or
                   (max_val == 1.0 and r["complexity"] == 1.0))
        if count > 0:
            print(f"   {bin_name:25s}: {count:2d}건")

    # 실패한 케이스
    failed = [r for r in results if not r["is_correct"]]
    if failed:
        print("\n❌ 실패한 케이스 분석:")
        for r in failed:
            print(f"\n   질문: '{r['query']}'")
            print(f"   예상: {r['expected']:10s} | 실제: {r['actual']:10s}")
            print(f"   복잡도: {r['complexity']:.2f} | 심층키워드: {r['requires_deep']}")

            # 실패 원인 분석
            if r["expected"] == "langgraph" and r["actual"] == "fast":
                print(f"   💡 분석: 복잡도가 너무 낮음 ({r['complexity']:.2f} < 0.7)")
            elif r["expected"] == "fast" and r["actual"] == "langgraph":
                print(f"   💡 분석: 복잡도가 너무 높거나 심층키워드 감지")

    print("\n" + "=" * 100)
    print("✅ 테스트 완료!")
    print("=" * 100)

    return accuracy >= 80.0  # 80% 이상이면 성공


if __name__ == "__main__":
    success = test_complexity()

    if success:
        print("\n🎉 테스트 성공! (정확도 80% 이상)")
        exit(0)
    else:
        print("\n⚠️  테스트 실패 (정확도 80% 미만)")
        exit(1)
