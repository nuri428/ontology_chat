#!/usr/bin/env python3
"""
최종 LangGraph 테스트
"""

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.services.langgraph_report_service import LangGraphReportEngine

async def test_full_pipeline():
    """전체 파이프라인 테스트"""
    print("🚀 LangGraph 전체 파이프라인 테스트")
    print("="*50)

    try:
        engine = LangGraphReportEngine()
        print("✅ LangGraph 엔진 초기화 성공")

        # 간단한 리포트 생성 테스트
        start_time = time.time()

        result = await engine.generate_langgraph_report(
            query="한화",
            domain="방산",
            lookback_days=30,
            analysis_depth="shallow"
        )

        processing_time = time.time() - start_time

        print(f"✅ 리포트 생성 완료!")
        print(f"   처리 시간: {processing_time:.2f}초")
        print(f"   타입: {result.get('type')}")
        print(f"   품질 점수: {result.get('quality_score', 0):.2f}")
        print(f"   품질 레벨: {result.get('quality_level', 'N/A')}")
        print(f"   컨텍스트: {result.get('contexts_count', 0)}개")
        print(f"   인사이트: {result.get('insights_count', 0)}개")
        print(f"   관계 분석: {result.get('relationships_count', 0)}개")
        print(f"   재시도 횟수: {result.get('retry_count', 0)}회")

        # 리포트 길이 확인
        markdown = result.get("markdown", "")
        print(f"   리포트 길이: {len(markdown)} 글자")

        # 실행 로그 확인 (처음 5개)
        execution_log = result.get("execution_log", [])
        if execution_log:
            print(f"   실행 로그 (처음 5개):")
            for i, log in enumerate(execution_log[:5], 1):
                print(f"      {i}. {log}")

        # 오류 확인
        if "error" in result:
            print(f"   ⚠️ 오류: {result['error']}")

        return result.get("quality_score", 0) > 0.3

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_performance():
    """성능 테스트"""
    print(f"\n⚡ 성능 테스트")
    print("="*30)

    try:
        engine = LangGraphReportEngine()

        # 여러 번 실행하여 평균 성능 측정
        times = []
        for i in range(3):
            start_time = time.time()

            result = await engine.generate_langgraph_report(
                query=f"테스트 {i+1}",
                domain="테스트",
                lookback_days=7,
                analysis_depth="shallow"
            )

            processing_time = time.time() - start_time
            times.append(processing_time)

            print(f"   테스트 {i+1}: {processing_time:.2f}초")

        avg_time = sum(times) / len(times)
        print(f"✅ 평균 처리 시간: {avg_time:.2f}초")

        return avg_time < 60  # 60초 이내

    except Exception as e:
        print(f"❌ 성능 테스트 실패: {e}")
        return False

async def main():
    """메인 테스트"""
    print("🧪 LangGraph 최종 테스트 시작")
    print("="*60)

    success_count = 0
    total_tests = 2

    # 1. 전체 파이프라인 테스트
    if await test_full_pipeline():
        success_count += 1
        print("✅ 전체 파이프라인 테스트 성공")
    else:
        print("❌ 전체 파이프라인 테스트 실패")

    # 2. 성능 테스트
    if await test_performance():
        success_count += 1
        print("✅ 성능 테스트 성공")
    else:
        print("❌ 성능 테스트 실패")

    print(f"\n🏁 최종 테스트 완료")
    print(f"   성공: {success_count}/{total_tests}")
    print(f"   성공률: {success_count/total_tests*100:.1f}%")

    if success_count == total_tests:
        print("🎉 모든 테스트 통과!")
    else:
        print("⚠️ 일부 테스트 실패")

if __name__ == "__main__":
    asyncio.run(main())