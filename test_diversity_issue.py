#!/usr/bin/env python3
"""다양성 문제 디버깅"""

import asyncio
import sys
sys.path.append('.')

async def test_diversity_issue():
    """반도체 쿼리 다양성 문제 분석"""
    print("🔍 반도체 쿼리 다양성 문제 분석")
    print("=" * 50)

    try:
        from api.services.chat_service import ChatService

        service = ChatService()

        query = "반도체 메모리 시장 전망과 삼성전자 경쟁우위"
        print(f"쿼리: '{query}'")

        # 검색 결과 확인
        news_hits, search_time, error = await service._search_news(query, size=10)  # 더 많이 가져오기

        print(f"\n📊 원본 검색 결과: {len(news_hits)}건")
        for i, hit in enumerate(news_hits[:10], 1):
            title = hit.get('title', 'No title')
            url = hit.get('url', 'No URL')
            score = hit.get('score', 0)
            print(f"   {i}. {title[:60]}... (점수: {score:.3f})")
            print(f"      URL: {url}")

        # 다양성 분석
        print(f"\n🔍 다양성 분석:")
        titles = [hit.get('title', '') for hit in news_hits]
        unique_titles = set(titles)
        print(f"   총 결과: {len(titles)}건")
        print(f"   고유 제목: {len(unique_titles)}건")
        print(f"   중복률: {(len(titles) - len(unique_titles)) / len(titles) * 100:.1f}%")

        # 중복 제목 찾기
        from collections import Counter
        title_counts = Counter(titles)
        duplicates = {title: count for title, count in title_counts.items() if count > 1}

        if duplicates:
            print(f"\n⚠️  중복된 제목들:")
            for title, count in duplicates.items():
                print(f"   • '{title[:50]}...' ({count}번)")

        # 정리
        await service.neo.close()

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_diversity_issue())