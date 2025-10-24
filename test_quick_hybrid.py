"""
하이브리드 라우팅 빠른 테스트 (pytest 없이)
"""

import asyncio
from api.services.chat_service import ChatService
from api.services.langgraph_report_service import LangGraphReportEngine
from api.services.query_router import QueryRouter
from api.services.response_formatter import ResponseFormatter
from api.services.intent_classifier import classify_query_intent


async def test_complexity_calculation():
    """복잡도 계산 로직 테스트"""
    print("\n" + "=" * 60)
    print("📊 복잡도 계산 테스트")
    print("=" * 60)

    chat_service = ChatService()
    langgraph_engine = LangGraphReportEngine()
    router = QueryRouter(chat_service, ResponseFormatter(), langgraph_engine)

    test_cases = [
        ("삼성전자 뉴스", "단순"),
        ("삼성전자와 SK하이닉스 비교 분석", "복잡"),
        ("HBM 시장 전망 보고서 작성해줘", "매우 복잡"),
        ("2차전지", "단순"),
        ("삼성전자 LG전자 SK하이닉스 비교 분석 보고서", "매우 복잡"),
    ]

    for query, expected_level in test_cases:
        intent_result = classify_query_intent(query)
        complexity = router._analyze_query_complexity(query, intent_result)
        requires_deep = router._requires_deep_analysis(query)

        # 라우팅 결정
        will_use_langgraph = complexity >= 0.7 or requires_deep

        print(f"\n📝 질문: {query}")
        print(f"   예상: {expected_level}")
        print(f"   복잡도: {complexity:.2f}")
        print(f"   심층분석 키워드: {requires_deep}")
        print(f"   라우팅: {'🤖 LangGraph Multi-Agent' if will_use_langgraph else '⚡ 빠른 핸들러'}")


async def test_simple_query():
    """단순 질문 테스트"""
    print("\n" + "=" * 60)
    print("⚡ 단순 질문 처리 테스트")
    print("=" * 60)

    chat_service = ChatService()
    langgraph_engine = LangGraphReportEngine()
    router = QueryRouter(chat_service, ResponseFormatter(), langgraph_engine)

    query = "삼성전자 뉴스"
    print(f"\n📝 질문: {query}")
    print("처리 중...")

    result = await router.process_query(query, force_deep_analysis=False)

    print(f"✅ 완료!")
    print(f"   타입: {result.get('type', 'unknown')}")
    print(f"   처리 방식: {result.get('meta', {}).get('processing_method', 'legacy')}")
    print(f"   응답 길이: {len(result.get('markdown', ''))} 자")


async def test_complex_query():
    """복잡한 질문 테스트"""
    print("\n" + "=" * 60)
    print("🤖 복잡한 질문 처리 테스트 (LangGraph)")
    print("=" * 60)

    chat_service = ChatService()
    langgraph_engine = LangGraphReportEngine()
    router = QueryRouter(chat_service, ResponseFormatter(), langgraph_engine)

    query = "삼성전자와 SK하이닉스 HBM 시장 점유율 비교 분석"
    print(f"\n📝 질문: {query}")
    print("처리 중... (Multi-Agent 분석, 시간 소요 가능)")

    result = await router.process_query(query, force_deep_analysis=False)

    print(f"✅ 완료!")
    print(f"   타입: {result.get('type', 'unknown')}")
    print(f"   처리 방식: {result.get('meta', {}).get('processing_method', 'legacy')}")
    print(f"   복잡도: {result.get('meta', {}).get('complexity_score', 0):.2f}")
    print(f"   분석 깊이: {result.get('meta', {}).get('analysis_depth', 'N/A')}")
    print(f"   품질 점수: {result.get('meta', {}).get('quality_score', 0):.2f}")


async def main():
    print("\n" + "=" * 80)
    print("🚀 하이브리드 라우팅 시스템 테스트")
    print("=" * 80)

    # 1. 복잡도 계산 테스트
    await test_complexity_calculation()

    # 2. 단순 질문 테스트
    await test_simple_query()

    # 3. 복잡한 질문 테스트 (선택적)
    run_complex_test = input("\n\n🤔 복잡한 질문 테스트 실행? (시간 소요, y/n): ").lower() == 'y'
    if run_complex_test:
        await test_complex_query()
    else:
        print("⏭️  복잡한 질문 테스트 스킵")

    print("\n" + "=" * 80)
    print("✅ 모든 테스트 완료!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
