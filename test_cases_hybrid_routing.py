"""
하이브리드 라우팅 실제 테스트 케이스
다양한 난이도의 질문으로 라우팅 정확도 검증
"""

import asyncio
import time
from typing import List, Dict, Any
from dataclasses import dataclass
from api.services.chat_service import ChatService
from api.services.langgraph_report_service import LangGraphReportEngine
from api.services.query_router import QueryRouter
from api.services.response_formatter import ResponseFormatter


@dataclass
class TestCase:
    """테스트 케이스"""
    query: str
    expected_route: str  # "fast" or "langgraph"
    category: str  # 카테고리
    description: str  # 설명


# 테스트 케이스 정의
TEST_CASES = [
    # ========== 레벨 1: 단순 질문 (빠른 핸들러) ==========
    TestCase(
        query="삼성전자 뉴스",
        expected_route="fast",
        category="단순 뉴스 조회",
        description="단일 회사 뉴스"
    ),
    TestCase(
        query="2차전지 관련 뉴스",
        expected_route="fast",
        category="단순 뉴스 조회",
        description="산업 키워드 뉴스"
    ),
    TestCase(
        query="방산주",
        expected_route="fast",
        category="단순 주식 조회",
        description="테마 조회"
    ),
    TestCase(
        query="SK하이닉스 최근 소식",
        expected_route="fast",
        category="단순 뉴스 조회",
        description="단일 회사 최근 뉴스"
    ),
    TestCase(
        query="에코프로",
        expected_route="fast",
        category="단순 주식 조회",
        description="단일 종목"
    ),

    # ========== 레벨 2: 중간 복잡도 ==========
    TestCase(
        query="현대차 전기차 사업 현황은?",
        expected_route="fast",
        category="중간 복잡도",
        description="특정 사업 현황 질문"
    ),
    TestCase(
        query="AI 반도체 관련 종목 추천",
        expected_route="fast",
        category="중간 복잡도",
        description="테마 종목 추천"
    ),
    TestCase(
        query="삼성전자 최근 실적 발표 내용",
        expected_route="fast",
        category="중간 복잡도",
        description="실적 정보"
    ),

    # ========== 레벨 3: 복잡한 질문 (LangGraph) ==========
    TestCase(
        query="삼성전자와 SK하이닉스 비교 분석",
        expected_route="langgraph",
        category="비교 분석",
        description="2개 회사 비교"
    ),
    TestCase(
        query="HBM 시장에서 삼성전자와 SK하이닉스의 경쟁력 분석 보고서",
        expected_route="langgraph",
        category="심층 보고서",
        description="시장 경쟁력 분석"
    ),
    TestCase(
        query="2차전지 산업 투자 전망 보고서 작성해줘",
        expected_route="langgraph",
        category="심층 보고서",
        description="산업 전망 보고서"
    ),
    TestCase(
        query="삼성전자 LG전자 현대차 실적 비교 분석",
        expected_route="langgraph",
        category="다중 비교",
        description="3개 회사 비교"
    ),
    TestCase(
        query="AI 반도체 시장 트렌드와 주요 기업들의 전략 비교",
        expected_route="langgraph",
        category="트렌드 분석",
        description="시장 트렌드 및 전략 비교"
    ),
    TestCase(
        query="방산 산업 주요 종목들의 최근 6개월 실적 변화 추이 분석",
        expected_route="langgraph",
        category="추이 분석",
        description="시계열 실적 분석"
    ),

    # ========== 레벨 4: 매우 복잡한 질문 ==========
    TestCase(
        query="삼성전자 SK하이닉스 마이크론의 HBM 기술 경쟁력과 시장 점유율 종합 비교 분석 보고서를 상세히 작성해줘",
        expected_route="langgraph",
        category="종합 분석",
        description="3개 글로벌 기업 종합 비교"
    ),
    TestCase(
        query="전기차 배터리 산업의 밸류체인 분석과 주요 기업별 포지셔닝 전략 보고서",
        expected_route="langgraph",
        category="밸류체인 분석",
        description="산업 구조 분석"
    ),
    TestCase(
        query="2024년 반도체 시장 회복 전망과 삼성전자 SK하이닉스의 투자 전략 비교",
        expected_route="langgraph",
        category="전망 및 전략",
        description="시장 전망 + 전략 비교"
    ),

    # ========== 엣지 케이스 ==========
    TestCase(
        query="PER이 뭐야?",
        expected_route="fast",
        category="일반 QA",
        description="금융 용어 질문"
    ),
    TestCase(
        query="배당수익률 높은 종목",
        expected_route="fast",
        category="단순 조회",
        description="조건 기반 종목 조회"
    ),
    TestCase(
        query="요즘 핫한 종목은?",
        expected_route="fast",
        category="단순 조회",
        description="트렌드 종목"
    ),
]


async def run_test_case(router: QueryRouter, test_case: TestCase) -> Dict[str, Any]:
    """단일 테스트 케이스 실행"""

    start_time = time.time()

    try:
        result = await router.process_query(
            test_case.query,
            user_id="test_user",
            force_deep_analysis=False
        )

        processing_time = (time.time() - start_time) * 1000

        # 실제 라우팅 경로 판단
        processing_method = result.get("meta", {}).get("processing_method", "legacy")
        actual_route = "langgraph" if processing_method == "multi_agent_langgraph" else "fast"

        # 복잡도 점수
        complexity_score = result.get("meta", {}).get("complexity_score", 0)

        # 성공 여부
        is_correct = actual_route == test_case.expected_route

        return {
            "query": test_case.query,
            "category": test_case.category,
            "expected": test_case.expected_route,
            "actual": actual_route,
            "complexity": complexity_score,
            "processing_time_ms": processing_time,
            "is_correct": is_correct,
            "response_length": len(result.get("markdown", "")),
            "quality_score": result.get("meta", {}).get("quality_score", 0),
        }

    except Exception as e:
        return {
            "query": test_case.query,
            "category": test_case.category,
            "expected": test_case.expected_route,
            "actual": "error",
            "complexity": 0,
            "processing_time_ms": 0,
            "is_correct": False,
            "error": str(e),
        }


async def run_all_tests():
    """모든 테스트 실행"""

    print("\n" + "=" * 100)
    print("🚀 하이브리드 라우팅 테스트 케이스 실행")
    print("=" * 100)

    # 서비스 초기화
    print("\n초기화 중...")
    chat_service = ChatService()
    langgraph_engine = LangGraphReportEngine()
    router = QueryRouter(chat_service, ResponseFormatter(), langgraph_engine)

    # 결과 저장
    results = []

    # 카테고리별 그룹화
    categories = {}
    for test_case in TEST_CASES:
        if test_case.category not in categories:
            categories[test_case.category] = []
        categories[test_case.category].append(test_case)

    # 카테고리별 실행
    for category_name, test_cases in categories.items():
        print(f"\n\n{'=' * 100}")
        print(f"📂 카테고리: {category_name} ({len(test_cases)}개 테스트)")
        print("=" * 100)

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] 테스트 중: {test_case.query}")
            print(f"   설명: {test_case.description}")
            print(f"   예상 라우팅: {test_case.expected_route.upper()}")

            result = await run_test_case(router, test_case)
            results.append(result)

            # 결과 출력
            status = "✅ 성공" if result["is_correct"] else "❌ 실패"
            print(f"   실제 라우팅: {result['actual'].upper()} - {status}")
            print(f"   복잡도: {result['complexity']:.2f}")
            print(f"   처리 시간: {result['processing_time_ms']:.0f}ms")

            if not result["is_correct"]:
                print(f"   ⚠️  예상({test_case.expected_route}) != 실제({result['actual']})")

    # 전체 결과 요약
    print("\n\n" + "=" * 100)
    print("📊 테스트 결과 요약")
    print("=" * 100)

    total = len(results)
    correct = sum(1 for r in results if r["is_correct"])
    accuracy = (correct / total * 100) if total > 0 else 0

    print(f"\n✅ 정확도: {correct}/{total} ({accuracy:.1f}%)")

    # 카테고리별 정확도
    print("\n📈 카테고리별 정확도:")
    for category_name in categories.keys():
        category_results = [r for r in results if r["category"] == category_name]
        cat_total = len(category_results)
        cat_correct = sum(1 for r in category_results if r["is_correct"])
        cat_accuracy = (cat_correct / cat_total * 100) if cat_total > 0 else 0
        print(f"   {category_name}: {cat_correct}/{cat_total} ({cat_accuracy:.1f}%)")

    # 라우팅별 통계
    print("\n⚡ 라우팅별 통계:")
    fast_results = [r for r in results if r["actual"] == "fast"]
    langgraph_results = [r for r in results if r["actual"] == "langgraph"]

    if fast_results:
        avg_fast_time = sum(r["processing_time_ms"] for r in fast_results) / len(fast_results)
        print(f"   빠른 핸들러: {len(fast_results)}건 (평균 {avg_fast_time:.0f}ms)")

    if langgraph_results:
        avg_lg_time = sum(r["processing_time_ms"] for r in langgraph_results) / len(langgraph_results)
        avg_quality = sum(r.get("quality_score", 0) for r in langgraph_results) / len(langgraph_results)
        print(f"   LangGraph: {len(langgraph_results)}건 (평균 {avg_lg_time:.0f}ms, 품질 {avg_quality:.2f})")

    # 실패한 케이스 상세
    failed = [r for r in results if not r["is_correct"]]
    if failed:
        print("\n❌ 실패한 케이스:")
        for r in failed:
            print(f"   - '{r['query']}'")
            print(f"     예상: {r['expected']}, 실제: {r['actual']}, 복잡도: {r['complexity']:.2f}")

    # 복잡도 분포
    print("\n📊 복잡도 분포:")
    complexity_bins = {
        "0.0-0.3 (매우 단순)": [r for r in results if 0 <= r["complexity"] < 0.3],
        "0.3-0.5 (단순)": [r for r in results if 0.3 <= r["complexity"] < 0.5],
        "0.5-0.7 (중간)": [r for r in results if 0.5 <= r["complexity"] < 0.7],
        "0.7-0.9 (복잡)": [r for r in results if 0.7 <= r["complexity"] < 0.9],
        "0.9-1.0 (매우 복잡)": [r for r in results if 0.9 <= r["complexity"] <= 1.0],
    }

    for bin_name, bin_results in complexity_bins.items():
        if bin_results:
            print(f"   {bin_name}: {len(bin_results)}건")

    print("\n" + "=" * 100)
    print("✅ 테스트 완료!")
    print("=" * 100)

    return results


async def run_quick_sampling():
    """빠른 샘플링 테스트 (5개만)"""

    print("\n" + "=" * 100)
    print("🚀 빠른 샘플링 테스트 (5개 질문)")
    print("=" * 100)

    # 서비스 초기화
    chat_service = ChatService()
    langgraph_engine = LangGraphReportEngine()
    router = QueryRouter(chat_service, ResponseFormatter(), langgraph_engine)

    # 샘플 케이스 선택 (각 레벨에서 1개씩)
    sample_cases = [
        TEST_CASES[0],   # 단순 뉴스
        TEST_CASES[6],   # 중간 복잡도
        TEST_CASES[8],   # 비교 분석
        TEST_CASES[14],  # 종합 분석
        TEST_CASES[17],  # 일반 QA
    ]

    results = []

    for i, test_case in enumerate(sample_cases, 1):
        print(f"\n[{i}/{len(sample_cases)}] 📝 {test_case.query}")
        print(f"   카테고리: {test_case.category}")
        print(f"   예상: {test_case.expected_route.upper()}")

        result = await run_test_case(router, test_case)
        results.append(result)

        status = "✅" if result["is_correct"] else "❌"
        print(f"   결과: {result['actual'].upper()} {status}")
        print(f"   복잡도: {result['complexity']:.2f}, 시간: {result['processing_time_ms']:.0f}ms")

    # 간단한 요약
    correct = sum(1 for r in results if r["is_correct"])
    print(f"\n✅ 샘플 정확도: {correct}/{len(results)} ({correct/len(results)*100:.1f}%)")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        # 빠른 샘플링
        asyncio.run(run_quick_sampling())
    else:
        # 전체 테스트
        print("\n💡 팁: 빠른 샘플링 테스트는 'python test_cases_hybrid_routing.py quick'")

        # 사용자 확인
        response = input("\n전체 테스트를 실행하시겠습니까? (복잡한 질문 포함, 시간 소요) [y/N]: ")
        if response.lower() != 'y':
            print("❌ 테스트 취소")
            print("💡 빠른 테스트: python test_cases_hybrid_routing.py quick")
            sys.exit(0)

        asyncio.run(run_all_tests())
