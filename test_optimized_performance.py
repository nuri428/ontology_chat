#!/usr/bin/env python3
"""
최적화된 LangGraph 성능 테스트

Phase 1 (완료): _analyze_query 통합 (2회 → 1회)
Phase 2 (완료): _comprehensive_analysis_and_report 통합 (5-9회 → 1회)

예상 성능: 15-20초 → 6-8초 (50-60% 개선)
"""

import asyncio
import time
import json
import httpx
from datetime import datetime


async def test_optimized_langgraph():
    """최적화된 LangGraph 성능 테스트"""

    test_queries = [
        # 복잡한 질문 (LangGraph 사용)
        "삼성전자와 SK하이닉스의 HBM 경쟁력 비교",
        "AI 반도체 시장에서 HBM 기술 경쟁력을 가진 기업은?",
        "현대차 전기차 사업 현황은?",
    ]

    results = {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "optimization_info": {
            "phase_1": "query analysis unified (2 → 1 LLM calls)",
            "phase_2": "comprehensive analysis unified (5-9 → 1 LLM calls)",
            "expected_improvement": "15-20s → 6-8s (50-60% faster)"
        },
        "tests": []
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for query in test_queries:
            print(f"\n{'='*80}")
            print(f"테스트 쿼리: {query}")
            print(f"{'='*80}")

            start_time = time.time()

            try:
                # MCP 엔드포인트 호출 (하이브리드 라우팅)
                response = await client.post(
                    "http://localhost:8000/mcp/chat",
                    json={
                        "query": query,
                        "user_id": "performance_test",
                        "force_deep_analysis": True  # LangGraph 강제 사용
                    }
                )

                elapsed = time.time() - start_time

                if response.status_code == 200:
                    data = response.json()
                    result_data = data.get("result", {})

                    # 응답 구조 확인
                    report = result_data.get("report", {})

                    test_result = {
                        "query": query,
                        "status": "success",
                        "response_time": f"{elapsed:.2f}s",
                        "quality_score": report.get("quality_score", 0.0),
                        "quality_level": report.get("quality_level", "unknown"),
                        "contexts_count": report.get("contexts_count", 0),
                        "insights_count": report.get("insights_count", 0),
                        "relationships_count": report.get("relationships_count", 0),
                        "retry_count": report.get("retry_count", 0),
                        "processing_time": report.get("processing_time", 0.0),
                        "execution_log": report.get("execution_log", [])
                    }

                    print(f"✅ 성공")
                    print(f"   응답 시간: {elapsed:.2f}초")
                    print(f"   품질 점수: {test_result['quality_score']:.2f} ({test_result['quality_level']})")
                    print(f"   처리 시간: {test_result['processing_time']:.2f}초")
                    print(f"   컨텍스트: {test_result['contexts_count']}개")
                    print(f"   인사이트: {test_result['insights_count']}개")
                    print(f"   관계 분석: {test_result['relationships_count']}개")
                    print(f"   재시도: {test_result['retry_count']}회")

                    # 실행 로그 출력
                    print(f"\n   실행 로그:")
                    for log_entry in test_result['execution_log']:
                        print(f"     {log_entry}")

                    # 보고서 샘플 출력 (처음 500자)
                    markdown = report.get("markdown", "")
                    print(f"\n   보고서 샘플 ({len(markdown)}자):")
                    print(f"   {markdown[:500]}...")

                else:
                    test_result = {
                        "query": query,
                        "status": "error",
                        "response_time": f"{elapsed:.2f}s",
                        "error": f"HTTP {response.status_code}: {response.text[:200]}"
                    }
                    print(f"❌ 실패: {test_result['error']}")

            except Exception as e:
                elapsed = time.time() - start_time
                test_result = {
                    "query": query,
                    "status": "exception",
                    "response_time": f"{elapsed:.2f}s",
                    "error": str(e)
                }
                print(f"❌ 예외 발생: {e}")

            results["tests"].append(test_result)

            # 다음 테스트 전 잠시 대기
            await asyncio.sleep(2)

    # 결과 요약
    print(f"\n{'='*80}")
    print("성능 테스트 결과 요약")
    print(f"{'='*80}")

    success_tests = [t for t in results["tests"] if t["status"] == "success"]

    if success_tests:
        avg_response_time = sum(float(t["response_time"].replace("s", "")) for t in success_tests) / len(success_tests)
        avg_quality = sum(t["quality_score"] for t in success_tests) / len(success_tests)
        avg_processing = sum(t["processing_time"] for t in success_tests) / len(success_tests)

        print(f"\n성공한 테스트: {len(success_tests)}/{len(results['tests'])}")
        print(f"평균 응답 시간: {avg_response_time:.2f}초")
        print(f"평균 처리 시간: {avg_processing:.2f}초")
        print(f"평균 품질 점수: {avg_quality:.2f}")

        results["summary"] = {
            "success_rate": f"{len(success_tests)}/{len(results['tests'])}",
            "avg_response_time": f"{avg_response_time:.2f}s",
            "avg_processing_time": f"{avg_processing:.2f}s",
            "avg_quality_score": avg_quality,
            "improvement_achieved": avg_response_time < 10.0,
            "target_met": avg_response_time <= 8.0
        }

        print(f"\n🎯 목표 달성 여부:")
        print(f"   10초 이내: {'✅ YES' if avg_response_time < 10.0 else '❌ NO'}")
        print(f"   8초 이내: {'✅ YES' if avg_response_time <= 8.0 else '❌ NO'}")
        print(f"   15-20초 대비 개선률: {(1 - avg_response_time / 17.5) * 100:.1f}%")

    # 결과 저장
    output_file = f"optimized_performance_results_{results['timestamp']}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {output_file}")

    return results


if __name__ == "__main__":
    print("🚀 최적화된 LangGraph 성능 테스트 시작\n")
    print("Phase 1: Query Analysis Unified (2 → 1 LLM calls)")
    print("Phase 2: Comprehensive Analysis Unified (5-9 → 1 LLM calls)")
    print("예상 개선: 15-20초 → 6-8초 (50-60% 개선)\n")

    results = asyncio.run(test_optimized_langgraph())
