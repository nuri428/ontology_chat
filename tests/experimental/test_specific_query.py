#!/usr/bin/env python3
"""특정 쿼리 테스트"""

import asyncio
import sys
sys.path.append('.')

async def test_specific_query():
    """특정 쿼리 직접 테스트"""
    print("🔍 특정 쿼리 직접 테스트")
    print("=" * 50)

    try:
        from api.services.chat_service import ChatService

        service = ChatService()

        query = "SMR 소형모듈원자로 투자 전망과 관련 업체"
        print(f"쿼리: '{query}'")

        # 온톨로지 검색 직접 테스트
        print("\n1. _search_news_with_ontology 직접 테스트:")
        try:
            result = await service._search_news_with_ontology(query, size=5)
            hits, search_time, error = result
            print(f"   결과: {len(hits)}건, {search_time:.1f}ms")
            if error:
                print(f"   에러: {error}")
        except Exception as e:
            print(f"   예외: {e}")
            import traceback
            traceback.print_exc()

        # 단순 검색 테스트
        print("\n2. _search_news 직접 테스트:")
        try:
            result = await service._search_news(query, size=5)
            hits, search_time, error = result
            print(f"   결과: {len(hits)}건, {search_time:.1f}ms")
            if hits:
                first_title = hits[0].get('title', 'No title')[:50]
                print(f"   첫 번째: {first_title}...")
        except Exception as e:
            print(f"   예외: {e}")

        # 정리
        await service.neo.close()

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_specific_query())