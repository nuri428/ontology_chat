#!/usr/bin/env python3
"""
LangGraph 간단 테스트
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.services.langgraph_report_service import LangGraphReportEngine, AnalysisDepth

async def test_langgraph_initialization():
    """LangGraph 엔진 초기화 테스트"""
    print("🔧 LangGraph 엔진 초기화 테스트")
    print("="*40)

    try:
        engine = LangGraphReportEngine()
        print("✅ LangGraph 엔진 초기화 성공")

        # BGE-M3 클라이언트 확인
        if hasattr(engine, 'embedding_client') and engine.embedding_client:
            print("✅ BGE-M3 임베딩 클라이언트 초기화됨")
        else:
            print("⚠️ BGE-M3 임베딩 클라이언트 없음 (키워드 검색만 사용)")

        # 워크플로우 확인
        if hasattr(engine, 'workflow') and engine.workflow:
            print("✅ LangGraph 워크플로우 구성됨")
        else:
            print("❌ LangGraph 워크플로우 구성 실패")

        return engine

    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_state_initialization():
    """상태 초기화 테스트"""
    print(f"\n📊 상태 초기화 테스트")
    print("="*40)

    try:
        engine = LangGraphReportEngine()

        # 기본 상태 초기화
        state = engine._initialize_state(
            query="한화 방산",
            domain="방산",
            lookback_days=30,
            analysis_depth="standard"
        )

        print("✅ 상태 초기화 성공")
        print(f"   쿼리: {state['query']}")
        print(f"   도메인: {state.get('domain', 'N/A')}")
        print(f"   분석 깊이: {state['analysis_depth']}")
        print(f"   실행 로그: {len(state['execution_log'])}개")

        # 잘못된 입력 테스트
        try:
            invalid_state = engine._initialize_state(query="")
            print("❌ 빈 쿼리가 허용되어서는 안됨")
        except ValueError:
            print("✅ 빈 쿼리 검증 성공")

        return True

    except Exception as e:
        print(f"❌ 상태 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_hybrid_search():
    """하이브리드 검색 테스트"""
    print(f"\n🔍 하이브리드 검색 테스트")
    print("="*40)

    try:
        engine = LangGraphReportEngine()

        if not engine.embedding_client:
            print("⚠️ BGE-M3 클라이언트가 없어 키워드 검색만 테스트")

        # 간단한 검색 테스트
        results = await engine._langgraph_hybrid_search(
            query="한화",
            lookback_days=30,
            size=5
        )

        print(f"✅ 하이브리드 검색 완료: {len(results)}건")

        if results:
            for i, hit in enumerate(results[:3], 1):
                score = hit.get("_score", 0)
                rrf_score = hit.get("_rrf_score", 0)
                source = hit.get("_source", {})
                title = source.get("title", source.get("text", ""))[:50] + "..."

                print(f"   {i}. (점수: {score:.3f}, RRF: {rrf_score:.3f}) {title}")

        return len(results) > 0

    except Exception as e:
        print(f"❌ 하이브리드 검색 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """메인 테스트 함수"""
    print("🚀 LangGraph 간단 테스트 시작")
    print("="*50)

    # 1. 초기화 테스트
    engine = await test_langgraph_initialization()
    if not engine:
        print("❌ 초기화 실패로 테스트 중단")
        return

    # 2. 상태 초기화 테스트
    state_ok = await test_state_initialization()
    if not state_ok:
        print("⚠️ 상태 초기화 실패, 계속 진행")

    # 3. 하이브리드 검색 테스트
    search_ok = await test_hybrid_search()
    if not search_ok:
        print("⚠️ 하이브리드 검색 실패, 계속 진행")

    print(f"\n🏁 간단 테스트 완료")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())