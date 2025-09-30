#!/usr/bin/env python3
"""Neo4j 쿼리 성능 직접 테스트"""
import asyncio
import sys
import time
sys.path.insert(0, '/app')

async def test_neo4j():
    from api.services.chat_service import ChatService

    service = ChatService()
    query = "삼성전자"

    print(f"Neo4j 쿼리 테스트: {query}")
    print("="*60)

    t0 = time.time()
    try:
        rows, elapsed_ms, error = await service._query_graph(query, limit=5)
        total_time = (time.time() - t0) * 1000

        print(f"결과 수: {len(rows)}개")
        print(f"내부 시간: {elapsed_ms:.2f}ms")
        print(f"전체 시간: {total_time:.2f}ms")
        print(f"에러: {error or 'None'}")

        if total_time > 1500:
            print(f"\n⚠️  타임아웃 초과! ({total_time:.0f}ms > 1500ms)")
        else:
            print(f"\n✓ 타임아웃 이내 완료")

        if rows:
            print(f"\n샘플:")
            for i, row in enumerate(rows[:2], 1):
                print(f"{i}. {row}")

    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_neo4j())