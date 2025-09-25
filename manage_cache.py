#!/usr/bin/env python3
"""캐시 관리 CLI 도구"""
import asyncio
import sys
import argparse
from typing import Optional

sys.path.append('.')

async def clear_cache():
    """전체 캐시 초기화"""
    from api.services.context_cache import context_cache

    print("🗑️ 캐시 초기화 중...")
    await context_cache.clear()
    print("✅ 캐시가 완전히 초기화되었습니다.")

async def show_stats():
    """캐시 통계 표시"""
    from api.services.context_cache import context_cache

    stats = context_cache.get_stats()
    print("\n📊 캐시 통계")
    print("=" * 50)
    print(f"총 요청: {stats['total_requests']}회")
    print(f"캐시 히트: {stats['hits']}회")
    print(f"캐시 미스: {stats['misses']}회")
    print(f"히트율: {stats['hit_rate']*100:.1f}%")
    print(f"현재 크기: {stats['cache_size']}/{stats['max_size']}")
    print(f"제거된 항목: {stats['evictions']}개")

    # 인기 쿼리
    hot_queries = context_cache.get_hot_queries(5)
    if hot_queries:
        print("\n🔥 인기 쿼리 TOP 5:")
        for i, hq in enumerate(hot_queries, 1):
            print(f"{i}. {hq['query'][:50]}... (히트: {hq['hit_count']}회)")

async def invalidate_pattern(pattern: str):
    """패턴 기반 캐시 무효화"""
    from api.services.context_cache import context_cache

    print(f"🔍 패턴 '{pattern}'과 일치하는 캐시 무효화 중...")
    count = await context_cache.invalidate(pattern=pattern)
    print(f"✅ {count}개 항목이 무효화되었습니다.")

async def cleanup_expired():
    """만료된 캐시 정리"""
    from api.services.context_cache import context_cache

    print("🧹 만료된 캐시 정리 중...")
    count = await context_cache.cleanup_expired()
    print(f"✅ {count}개의 만료된 항목이 제거되었습니다.")

async def test_cache():
    """캐시 동작 테스트"""
    from api.services.context_cache import context_cache
    import time

    print("\n🧪 캐시 테스트")
    print("=" * 50)

    # 테스트 데이터 추가
    test_query = "test query for cache"
    test_context = [{"content": "test data", "score": 0.9}]

    print(f"1️⃣ 테스트 데이터 추가: '{test_query}'")
    await context_cache.set(test_query, test_context, {"test": True})

    # 캐시 히트 테스트
    print("2️⃣ 캐시 히트 테스트...")
    start = time.perf_counter()
    result = await context_cache.get(test_query)
    elapsed = (time.perf_counter() - start) * 1000

    if result:
        print(f"   ✅ 캐시 히트! ({elapsed:.2f}ms)")
    else:
        print(f"   ❌ 캐시 미스")

    # 통계 확인
    stats = context_cache.get_stats()
    print(f"3️⃣ 현재 캐시 크기: {stats['cache_size']}")

    # 정리
    await context_cache.clear()
    print("4️⃣ 테스트 완료 - 캐시 초기화됨")

def main():
    parser = argparse.ArgumentParser(description="Ontology Chat 캐시 관리 도구")
    parser.add_argument("command", choices=["clear", "stats", "test", "cleanup"],
                       help="실행할 명령")
    parser.add_argument("--pattern", "-p", type=str,
                       help="무효화할 패턴 (invalidate 명령용)")

    args = parser.parse_args()

    if args.command == "clear":
        asyncio.run(clear_cache())
    elif args.command == "stats":
        asyncio.run(show_stats())
    elif args.command == "test":
        asyncio.run(test_cache())
    elif args.command == "cleanup":
        asyncio.run(cleanup_expired())
    elif args.command == "invalidate" and args.pattern:
        asyncio.run(invalidate_pattern(args.pattern))
    else:
        print("❌ 잘못된 명령입니다.")
        parser.print_help()

if __name__ == "__main__":
    main()