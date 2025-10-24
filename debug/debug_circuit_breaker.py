#!/usr/bin/env python3
"""서킷 브레이커 상태 디버깅"""
import asyncio
import sys
sys.path.insert(0, '/app')

async def check_circuit_breaker():
    """서킷 브레이커 상태 및 Neo4j 쿼리 실행 확인"""
    from api.services.chat_service import ChatService

    print("="*80)
    print("Neo4j 서킷 브레이커 상태 확인")
    print("="*80)

    service = ChatService()
    cb = service.neo4j_circuit_breaker

    print(f"\n[서킷 브레이커 상태]")
    print(f"  - 현재 상태: {cb.state}")
    print(f"  - 실패 횟수: {cb.failure_count}/{cb.failure_threshold}")
    print(f"  - is_open(): {cb.is_open()}")
    print(f"  - 마지막 실패 시각: {cb.last_failure_time}")

    if cb.is_open():
        print("\n⚠️  서킷 브레이커가 OPEN 상태입니다!")
        print("   → Neo4j 쿼리가 실행되지 않습니다.")
        print("\n[해결 방법]")
        print("   1. 서킷 브레이커 리셋 (30초 대기)")
        print("   2. Neo4j 연결 확인")
        print("   3. 타임아웃 조정 (0.3s → 1.0s)")
    else:
        print("\n✓ 서킷 브레이커 정상 (CLOSED/HALF_OPEN)")

    # Neo4j 직접 쿼리 테스트
    print("\n" + "="*80)
    print("Neo4j 직접 쿼리 테스트")
    print("="*80)

    test_query = "삼성전자"
    print(f"\n질의: {test_query}")

    try:
        rows, elapsed_ms, error = await service._query_graph(test_query, limit=3)

        print(f"\n[쿼리 결과]")
        print(f"  - 결과 수: {len(rows)}개")
        print(f"  - 실행 시간: {elapsed_ms:.2f}ms")
        print(f"  - 에러: {error or 'None'}")

        if rows:
            print(f"\n[샘플 결과]")
            for i, row in enumerate(rows[:2], 1):
                print(f"  {i}. {row}")
        else:
            print("\n⚠️  결과가 비어있습니다!")

        # 서킷 브레이커 상태 재확인
        print(f"\n[쿼리 후 서킷 브레이커]")
        print(f"  - 상태: {cb.state}")
        print(f"  - 실패 횟수: {cb.failure_count}/{cb.failure_threshold}")

    except Exception as e:
        print(f"\n✗ 쿼리 실패: {e}")
        import traceback
        traceback.print_exc()

    # search_parallel에서의 타임아웃 테스트
    print("\n" + "="*80)
    print("search_parallel 흐름에서 Neo4j 호출 시뮬레이션")
    print("="*80)

    print(f"\n현재 타임아웃: 0.3초 (300ms)")
    print(f"위 쿼리 실행 시간: {elapsed_ms:.2f}ms")

    if elapsed_ms > 300:
        print(f"\n⚠️  타임아웃 초과! ({elapsed_ms:.2f}ms > 300ms)")
        print(f"   → 이것이 Neo4j가 사용되지 않는 주요 원인입니다.")
        print(f"\n[권장 수정]")
        print(f"   chat_service.py:491")
        print(f"   timeout=0.3 → timeout=1.0 (또는 1.5)")
    else:
        print(f"\n✓ 타임아웃 이내 실행 완료")

    print("\n" + "="*80)
    print("디버깅 완료")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(check_circuit_breaker())