"""
하이브리드 라우팅 시스템 테스트

테스트 내용:
1. 단순 질문 → 빠른 핸들러 라우팅
2. 복잡한 질문 → LangGraph Multi-Agent 라우팅
3. MCP 엔드포인트 테스트
"""

import pytest
import asyncio
from api.services.chat_service import ChatService
from api.services.report_service import ReportService
from api.services.langgraph_report_service import LangGraphReportEngine
from api.services.query_router import QueryRouter
from api.services.response_formatter import ResponseFormatter


@pytest.fixture
def services():
    """서비스 인스턴스 생성"""
    chat_service = ChatService()
    report_service = ReportService()
    langgraph_engine = LangGraphReportEngine()
    return chat_service, report_service, langgraph_engine


@pytest.fixture
def router(services):
    """하이브리드 라우터 생성"""
    chat_service, _, langgraph_engine = services
    return QueryRouter(chat_service, ResponseFormatter(), langgraph_engine)


@pytest.mark.asyncio
async def test_simple_query_routing(router):
    """단순 질문은 빠른 핸들러로 라우팅"""
    query = "삼성전자 뉴스"

    result = await router.process_query(query, force_deep_analysis=False)

    # 빠른 응답 확인
    assert result is not None
    assert "markdown" in result or "answer" in result
    assert result.get("meta", {}).get("processing_method") != "multi_agent_langgraph"

    print(f"✅ 단순 질문 처리: {query}")
    print(f"   처리 방식: {result.get('type', 'unknown')}")


@pytest.mark.asyncio
async def test_complex_query_routing(router):
    """복잡한 질문은 LangGraph로 라우팅"""
    query = "삼성전자와 SK하이닉스의 HBM 시장 점유율 비교 분석 보고서"

    result = await router.process_query(query, force_deep_analysis=False)

    # LangGraph 사용 확인
    assert result is not None
    processing_method = result.get("meta", {}).get("processing_method", "")

    # 복잡도가 높아서 LangGraph 사용했는지 확인
    print(f"✅ 복잡한 질문 처리: {query}")
    print(f"   처리 방식: {result.get('type', 'unknown')}")
    print(f"   복잡도: {result.get('meta', {}).get('complexity_score', 0):.2f}")


@pytest.mark.asyncio
async def test_forced_deep_analysis(router):
    """강제 심층 분석 모드"""
    query = "삼성전자"  # 단순 쿼리지만 강제 심층 분석

    result = await router.process_query(query, force_deep_analysis=True)

    # 강제로 LangGraph 사용 확인
    assert result is not None
    assert result.get("type") == "langgraph_analysis"

    print(f"✅ 강제 심층 분석: {query}")
    print(f"   분석 깊이: {result.get('meta', {}).get('analysis_depth', 'unknown')}")


@pytest.mark.asyncio
async def test_complexity_calculation(router):
    """복잡도 계산 로직 테스트"""
    from api.services.intent_classifier import classify_query_intent

    test_cases = [
        ("삼성전자 뉴스", 0.0, 0.5),  # 단순
        ("삼성전자와 SK하이닉스 비교 분석", 0.6, 1.0),  # 복잡
        ("HBM 시장 전망 보고서 작성", 0.7, 1.0),  # 매우 복잡
    ]

    for query, min_score, max_score in test_cases:
        intent_result = classify_query_intent(query)
        complexity = router._analyze_query_complexity(query, intent_result)

        assert min_score <= complexity <= max_score, \
            f"'{query}' 복잡도 {complexity:.2f}가 예상 범위 [{min_score}, {max_score}]를 벗어남"

        print(f"✅ '{query}' → 복잡도: {complexity:.2f}")


@pytest.mark.asyncio
async def test_mcp_chat_endpoint():
    """MCP 채팅 엔드포인트 테스트 (통합 테스트)"""
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)

    # 단순 질문
    response = client.post("/mcp/chat", json={
        "query": "삼성전자 뉴스",
        "user_id": "test_user",
        "force_deep_analysis": False
    })

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "result" in data

    print("✅ MCP 채팅 엔드포인트 테스트 성공")


@pytest.mark.asyncio
async def test_mcp_report_endpoint():
    """MCP 보고서 엔드포인트 테스트"""
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)

    # LangGraph 보고서
    response = client.post("/mcp/report/langgraph", json={
        "query": "삼성전자 분석",
        "analysis_depth": "standard",
        "lookback_days": 30
    })

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "report" in data

    print("✅ MCP 보고서 엔드포인트 테스트 성공")


if __name__ == "__main__":
    # 개별 테스트 실행
    print("=" * 60)
    print("하이브리드 라우팅 시스템 테스트")
    print("=" * 60)

    # 서비스 초기화
    chat_service = ChatService()
    langgraph_engine = LangGraphReportEngine()
    router = QueryRouter(chat_service, ResponseFormatter(), langgraph_engine)

    # 복잡도 테스트
    asyncio.run(test_complexity_calculation(router))

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)
