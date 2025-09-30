#!/usr/bin/env python3
"""간단한 채팅 API 테스트"""
import asyncio
import aiohttp
import json

async def test_chat(query: str):
    """단일 채팅 테스트"""
    print(f"\n질문: {query}")
    print("="*80)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/chat",
            json={"query": query},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            print(f"Status: {response.status}")
            result = await response.json()

            print(f"\n응답:")
            print(f"  - 답변 길이: {len(result.get('answer', ''))} chars")
            print(f"  - 출처 개수: {len(result.get('sources', []))}")
            print(f"  - 그래프 샘플: {len(result.get('graph_samples', []))}")
            print(f"  - 메타데이터: {json.dumps(result.get('meta', {}), indent=2)}")

            answer = result.get('answer', '')
            if answer:
                print(f"\n답변 내용 (처음 500자):")
                print(answer[:500])
            else:
                print("\n⚠️ 빈 응답!")

            # 출처 샘플
            sources = result.get('sources', [])
            if sources:
                print(f"\n출처 샘플 (최대 3개):")
                for i, source in enumerate(sources[:3], 1):
                    print(f"  {i}. {source.get('title', 'No title')}")
                    print(f"     Date: {source.get('date', 'N/A')}")

            return result

async def main():
    # 간단한 질문부터 시작
    queries = [
        "삼성전자 최근 뉴스",
        "반도체 시장 동향",
        "2차전지 관련 주요 기업"
    ]

    for query in queries:
        await test_chat(query)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())