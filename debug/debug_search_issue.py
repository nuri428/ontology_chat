#!/usr/bin/env python3
"""직접 검색 함수 디버깅"""

import asyncio
import sys
sys.path.append('.')

async def debug_search_function():
    """실제 검색 함수 디버깅"""
    print("🔍 실제 검색 함수 디버깅")
    print("=" * 50)

    try:
        from api.services.chat_service import ChatService

        service = ChatService()

        # 단순한 테스트 쿼리들
        test_queries = [
            "삼성전자",
            "반도체",
            "SMR"
        ]

        for query in test_queries:
            print(f"\n🔍 테스트 쿼리: '{query}'")
            print("-" * 30)

            try:
                # _search_news 함수 직접 호출
                hits, search_time, error = await service._search_news(query, size=3)

                print(f"   검색 시간: {search_time:.1f}ms")
                if error:
                    print(f"   ❌ 에러: {error}")
                else:
                    print(f"   ✅ 결과: {len(hits)}건")

                    for i, hit in enumerate(hits[:2], 1):
                        title = hit.get('title', 'No title')[:50]
                        score = hit.get('score', 0)
                        print(f"      {i}. {title}... (점수: {score})")

            except Exception as e:
                print(f"   ❌ 검색 실패: {e}")
                import traceback
                traceback.print_exc()

        # 정리
        await service.neo.close()

    except Exception as e:
        print(f"❌ 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_search_function())