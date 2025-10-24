#!/usr/bin/env python3
"""
Gemma3:4b 품질 테스트 (LangGraph 직접 호출)
타임아웃 없이 완료될 때까지 기다려서 품질 확인
"""

import asyncio
import sys
sys.path.append('/data/dev/git/ontology_chat')

from api.services.langgraph_report_service import LangGraphReportService
from api.services.report_service import ReportService
from api.adapters.mcp_stock import StockAdapter
import time


async def test_gemma_quality():
    """Gemma3:4b 직접 테스트"""

    # 서비스 초기화
    report_service = ReportService()
    stock = StockAdapter()
    langgraph = LangGraphReportService(report_service, stock)

    query = "삼성전자와 SK하이닉스의 HBM 경쟁력 비교 분석"

    print(f"🧪 테스트 쿼리: {query}")
    print(f"🤖 모델: gemma3:4b")
    print(f"⏱️  타임아웃 없음 (완료될 때까지 대기)")
    print()
    print("="*80)

    start_time = time.time()

    try:
        # LangGraph 직접 호출 (타임아웃 없음)
        result = await langgraph.generate_langgraph_report(
            query=query,
            analysis_depth="comprehensive"
        )

        elapsed = time.time() - start_time

        print(f"\n✅ 완료! 총 소요 시간: {elapsed:.2f}초")
        print("="*80)
        print()

        # 결과 출력
        print(f"품질 점수: {result.get('quality_score', 0):.2f}")
        print(f"품질 레벨: {result.get('quality_level', 'unknown')}")
        print(f"컨텍스트: {result.get('contexts_count', 0)}개")
        print(f"인사이트: {result.get('insights_count', 0)}개")
        print(f"관계 분석: {result.get('relationships_count', 0)}개")
        print(f"재시도: {result.get('retry_count', 0)}회")
        print(f"처리 시간: {result.get('processing_time', 0):.2f}초")
        print()

        # 실행 로그
        print("실행 로그:")
        for log in result.get('execution_log', []):
            print(f"  {log}")
        print()

        # 보고서
        markdown = result.get('markdown', '')
        print("="*80)
        print("📝 생성된 보고서")
        print("="*80)
        print(markdown)
        print()
        print(f"보고서 길이: {len(markdown)}자")

        # 품질 분석
        print()
        print("="*80)
        print("📊 품질 분석")
        print("="*80)

        # 한국어 비율
        korean_chars = sum(1 for c in markdown if '가' <= c <= '힣')
        korean_ratio = korean_chars / len(markdown) if len(markdown) > 0 else 0
        print(f"한국어 비율: {korean_ratio*100:.1f}%")

        # 구조화
        has_headers = markdown.count('#')
        has_bullets = markdown.count('-') + markdown.count('*')
        print(f"헤더 수: {has_headers}개")
        print(f"리스트 항목: {has_bullets}개")

        # 금융 용어
        finance_terms = ["투자", "경쟁력", "시장", "성장", "HBM", "반도체", "기업", "전망"]
        term_counts = {term: markdown.count(term) for term in finance_terms}
        print(f"금융 용어 사용:")
        for term, count in term_counts.items():
            if count > 0:
                print(f"  - {term}: {count}회")

        return {
            "success": True,
            "elapsed": elapsed,
            "result": result,
            "quality": {
                "korean_ratio": korean_ratio,
                "headers": has_headers,
                "bullets": has_bullets,
                "terms": term_counts
            }
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ 오류 발생: {e}")
        print(f"소요 시간: {elapsed:.2f}초")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "elapsed": elapsed}


if __name__ == "__main__":
    print("🔥 Gemma3:4b 품질 테스트 시작\n")
    result = asyncio.run(test_gemma_quality())

    if result["success"]:
        print(f"\n✅ 테스트 성공!")
        print(f"   총 시간: {result['elapsed']:.2f}초")
        print(f"   품질 점수: {result['result'].get('quality_score', 0):.2f}")
    else:
        print(f"\n❌ 테스트 실패")
        print(f"   오류: {result['error']}")
