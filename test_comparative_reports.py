#!/usr/bin/env python3
"""
비교 보고서 및 트렌드 보고서 기능 테스트
"""

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.services.report_service import ReportService
from api.services.langgraph_report_service import LangGraphReportEngine

async def test_basic_comparative_report():
    """기본 비교 분석 리포트 테스트"""
    print("📊 기본 비교 분석 리포트 테스트")
    print("=" * 40)

    try:
        service = ReportService()

        # 한화시스템과 LIG넥스원 비교
        queries = ["한화시스템", "LIG넥스원"]

        start_time = time.time()
        result = await service.generate_comparative_report(
            queries=queries,
            domain="방산",
            lookback_days=90
        )
        processing_time = time.time() - start_time

        print(f"✅ 기본 비교 분석 완료!")
        print(f"   처리 시간: {processing_time:.2f}초")
        print(f"   비교 대상: {len(queries)}개")
        print(f"   마크다운 길이: {len(result.get('markdown', ''))} 글자")
        print(f"   비교 데이터: {len(result.get('comparisons', []))}개")

        # 각 비교 항목의 메트릭 확인
        for i, comp in enumerate(result.get('comparisons', []), 1):
            ctx = comp.get('context', {})
            print(f"   {i}. {comp.get('query')}: 뉴스 {len(getattr(ctx, 'news_hits', []))}개, 그래프 {len(getattr(ctx, 'graph_rows', []))}개")

        return True

    except Exception as e:
        print(f"❌ 기본 비교 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_basic_trend_analysis():
    """기본 트렌드 분석 리포트 테스트"""
    print("\n📈 기본 트렌드 분석 리포트 테스트")
    print("=" * 40)

    try:
        service = ReportService()

        start_time = time.time()
        result = await service.generate_trend_analysis(
            query="한화",
            domain="방산",
            periods=[30, 90, 180]
        )
        processing_time = time.time() - start_time

        print(f"✅ 기본 트렌드 분석 완료!")
        print(f"   처리 시간: {processing_time:.2f}초")
        print(f"   분석 기간: {len(result.get('trend_data', []))}개")
        print(f"   마크다운 길이: {len(result.get('markdown', ''))} 글자")

        # 각 기간별 데이터 확인
        for trend in result.get('trend_data', []):
            period = trend.get('period')
            metrics = trend.get('metrics', {})
            print(f"   {period}일: 뉴스 {metrics.get('news_count', 0)}개, 계약 {metrics.get('contract_count', 0)}개")

        return True

    except Exception as e:
        print(f"❌ 기본 트렌드 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_langgraph_comparative():
    """LangGraph 비교 분석 테스트"""
    print("\n🤖 LangGraph 비교 분석 테스트")
    print("=" * 40)

    try:
        engine = LangGraphReportEngine()

        # 간단한 2개 항목 비교
        queries = ["삼성전자", "SK하이닉스"]

        # 각 쿼리별 분석 수행 (실제 API 로직 모방)
        results = []
        for query in queries:
            result = await engine.generate_langgraph_report(
                query=query,
                domain="반도체",
                lookback_days=30,
                analysis_depth="shallow"
            )
            results.append({
                "query": query,
                "result": result
            })
            print(f"   {query} 분석 완료: 품질 {result.get('quality_score', 0):.2f}")

        print(f"✅ LangGraph 비교 분석 완료!")
        print(f"   비교 항목: {len(results)}개")

        for r in results:
            result = r["result"]
            print(f"   {r['query']}: 품질 {result.get('quality_score', 0):.2f}, 컨텍스트 {result.get('contexts_count', 0)}개")

        return True

    except Exception as e:
        print(f"❌ LangGraph 비교 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """메인 테스트"""
    print("🧪 비교 및 트렌드 보고서 기능 테스트")
    print("=" * 60)

    tests = [
        ("기본 비교 분석", test_basic_comparative_report),
        ("기본 트렌드 분석", test_basic_trend_analysis),
        ("LangGraph 비교 분석", test_langgraph_comparative),
    ]

    success_count = 0

    for test_name, test_func in tests:
        print(f"\n🚀 {test_name} 시작...")
        try:
            if await test_func():
                success_count += 1
                print(f"✅ {test_name} 성공")
            else:
                print(f"❌ {test_name} 실패")
        except Exception as e:
            print(f"❌ {test_name} 오류: {e}")

    print(f"\n🏁 테스트 완료")
    print(f"   성공: {success_count}/{len(tests)}")
    print(f"   성공률: {success_count/len(tests)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())