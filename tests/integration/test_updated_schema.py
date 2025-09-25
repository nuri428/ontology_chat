#!/usr/bin/env python3
"""
업데이트된 스키마 기반 분석 테스트
"""

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.services.report_service import ReportService

async def test_updated_schema_analysis():
    """업데이트된 스키마 기반 분석 테스트"""
    print("🆕 업데이트된 스키마 분석 테스트")
    print("=" * 50)

    try:
        service = ReportService()

        # 상장사 중심 쿼리 테스트
        test_queries = [
            {"query": "삼성전자", "description": "대표 상장사"},
            {"query": "현대차", "description": "제조업 상장사"},
            {"query": "SK하이닉스", "description": "반도체 상장사"},
            {"query": "한화시스템", "description": "방산 상장사"},
        ]

        for test_case in test_queries:
            print(f"\n📊 {test_case['description']} 테스트: {test_case['query']}")
            print("-" * 40)

            start_time = time.time()

            # 컨텍스트 수집
            ctx = await service.fetch_context(
                query=test_case["query"],
                lookback_days=30,
                news_size=10,
                graph_limit=20
            )

            # 새로운 메트릭 계산
            graph_metrics = service.compute_graph_metrics(ctx.graph_rows)

            processing_time = time.time() - start_time

            print(f"✅ 처리 완료 ({processing_time:.2f}초)")
            print(f"   🔍 그래프 노드: {len(ctx.graph_rows)}개")
            print(f"   📰 뉴스: {len(ctx.news_hits)}개")

            # 새로운 메트릭 확인
            print(f"   📈 상장사: {len(graph_metrics.get('listed_companies', []))}개")
            print(f"   💰 총 매출: {graph_metrics['financial_summary']['total_revenue']:,.0f}")
            print(f"   💼 총 투자: {graph_metrics['investment_summary']['total_amount']:,.0f}")

            # 라벨 분포 확인
            if graph_metrics["label_distribution"]:
                top_labels = graph_metrics["label_distribution"][:3]
                labels_str = ", ".join([f"{label}({count})" for label, count in top_labels])
                print(f"   🏷️ 주요 라벨: {labels_str}")

            # 상장사 정보 출력
            if graph_metrics["listed_companies"]:
                print(f"   🏢 주요 상장사:")
                for company in graph_metrics["listed_companies"][:2]:
                    name = company["name"]
                    ticker = f"({company['ticker']})" if company.get("ticker") else ""
                    market_cap = f" 시총: {company['market_cap']:,.0f}억" if company.get("market_cap") else ""
                    print(f"      - {name} {ticker}{market_cap}")

        return True

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_markdown_generation():
    """마크다운 생성 테스트"""
    print(f"\n📝 마크다운 생성 테스트")
    print("=" * 40)

    try:
        service = ReportService()

        # 샘플 쿼리로 리포트 생성
        result = await service.generate_report(
            query="삼성전자",
            lookback_days=30,
            news_size=5,
            graph_limit=10
        )

        markdown = result["markdown"]
        metrics = result["metrics"]

        print(f"✅ 마크다운 생성 완료")
        print(f"   📄 마크다운 길이: {len(markdown)} 글자")
        print(f"   📊 그래프 메트릭: {len(metrics['graph'])}개 항목")

        # 새로운 메트릭 확인
        graph_metrics = metrics["graph"]
        if "financial_summary" in graph_metrics:
            print(f"   💰 재무 요약 포함됨")
        if "investment_summary" in graph_metrics:
            print(f"   💼 투자 요약 포함됨")
        if "listed_companies" in graph_metrics:
            print(f"   📈 상장사 정보 포함됨")

        # 마크다운 첫 부분 출력
        print(f"\n📄 마크다운 미리보기:")
        print("-" * 30)
        print(markdown[:300] + "..." if len(markdown) > 300 else markdown)

        return True

    except Exception as e:
        print(f"❌ 마크다운 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """메인 테스트"""
    print("🧪 업데이트된 스키마 테스트 시작")
    print("=" * 60)

    tests = [
        ("스키마 분석", test_updated_schema_analysis),
        ("마크다운 생성", test_markdown_generation),
    ]

    success_count = 0

    for test_name, test_func in tests:
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

    if success_count == len(tests):
        print("🎉 모든 테스트 통과! 새 스키마 적용 완료")
    else:
        print("⚠️ 일부 테스트 실패")

if __name__ == "__main__":
    asyncio.run(main())