#!/usr/bin/env python3
"""성능 분석 및 병목 지점 찾기"""

import asyncio
import time
import sys
sys.path.append('.')

async def analyze_performance():
    """성능 병목 지점 분석"""
    print("⏱️ 성능 분석 및 병목 지점 찾기")
    print("=" * 50)

    try:
        from api.services.chat_service import ChatService

        service = ChatService()

        test_queries = [
            "SMR 소형모듈원자로 투자 전망과 관련 업체",
            "반도체 메모리 시장 전망과 삼성전자 경쟁우위",
        ]

        for query in test_queries:
            print(f"\n🔍 쿼리: '{query[:30]}...'")
            print("-" * 40)

            # 전체 시간 측정
            total_start = time.perf_counter()

            # 1. 키워드 추출 시간
            keyword_start = time.perf_counter()
            keywords = await service._get_context_keywords(query)
            keyword_time = (time.perf_counter() - keyword_start) * 1000
            print(f"   🔤 키워드 추출: {keyword_time:.1f}ms")

            # 2. 뉴스 검색 시간 (세부 분석)
            news_start = time.perf_counter()
            news_hits, search_time, error = await service._search_news(query, size=5)
            news_total_time = (time.perf_counter() - news_start) * 1000
            print(f"   📰 뉴스 검색 (총): {news_total_time:.1f}ms")
            print(f"   📰 뉴스 검색 (OpenSearch): {search_time:.1f}ms")
            print(f"   📰 후처리 시간: {news_total_time - search_time:.1f}ms")

            # 3. 그래프 검색 시간
            graph_start = time.perf_counter()
            graph_rows, graph_time, graph_error = await service._query_graph(query, limit=3)
            graph_total_time = (time.perf_counter() - graph_start) * 1000
            print(f"   🔗 그래프 검색: {graph_total_time:.1f}ms")

            # 4. 병렬 처리 시간 (비교용)
            parallel_start = time.perf_counter()
            (news_hits_p, graph_rows_p, keywords_p,
             keyword_time_p, news_time_p, total_time_p) = await service.search_parallel(query, size=5)
            parallel_total = (time.perf_counter() - parallel_start) * 1000
            print(f"   🚀 병렬 처리 (총): {parallel_total:.1f}ms")

            total_time = (time.perf_counter() - total_start) * 1000
            print(f"   📊 개별 합계: {keyword_time + news_total_time + graph_total_time:.1f}ms")
            print(f"   📊 병렬 효과: {((keyword_time + news_total_time + graph_total_time) - parallel_total):.1f}ms 단축")

        # 정리
        await service.neo.close()

    except Exception as e:
        print(f"❌ 성능 분석 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(analyze_performance())