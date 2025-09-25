#!/usr/bin/env python3
"""OpenSearch 연결 및 검색 테스트"""

import asyncio
import sys
sys.path.append('.')

async def test_opensearch_connection():
    """OpenSearch 연결 테스트"""
    print("🔍 OpenSearch 연결 테스트")
    print("=" * 50)

    try:
        from api.adapters.mcp_opensearch import OpenSearchMCP
        from api.config import settings

        os_client = OpenSearchMCP()

        # 인덱스 목록 확인
        print("📋 사용 가능한 인덱스 확인...")
        try:
            indices_result = await os_client.list_indices()
            print(f"   인덱스 목록: {indices_result}")
        except Exception as e:
            print(f"   ❌ 인덱스 목록 조회 실패: {e}")

        # 설정된 뉴스 인덱스 확인
        news_index = settings.news_embedding_index
        print(f"   설정된 뉴스 인덱스: '{news_index}'")

        # 단순한 테스트 쿼리
        test_queries = [
            "삼성전자",
            "반도체",
            "*",  # 전체 검색
        ]

        for query in test_queries:
            print(f"\n🔍 테스트 쿼리: '{query}'")
            try:
                # 가장 단순한 검색 구조
                body = {
                    "query": {
                        "match_all": {} if query == "*" else {
                            "multi_match": {
                                "query": query,
                                "fields": ["title", "content", "text"],
                                "operator": "or"
                            }
                        }
                    },
                    "size": 3,
                    "_source": ["title", "url", "media"]
                }

                result = await os_client.search(
                    index=news_index,
                    query=body,
                    size=3
                )

                if result and "hits" in result:
                    total_hits = result["hits"].get("total", {})
                    if isinstance(total_hits, dict):
                        total_count = total_hits.get("value", 0)
                    else:
                        total_count = total_hits

                    hits = result["hits"].get("hits", [])
                    print(f"   ✅ 검색 성공: 총 {total_count}건, 반환 {len(hits)}건")

                    for i, hit in enumerate(hits[:2], 1):
                        source = hit.get("_source", {})
                        title = source.get("title", "No title")[:50]
                        score = hit.get("_score", 0)
                        print(f"      {i}. {title}... (점수: {score:.3f})")
                else:
                    print(f"   ❌ 검색 결과 없음")

            except Exception as e:
                print(f"   ❌ 검색 실패: {e}")
                import traceback
                traceback.print_exc()

        # 인덱스 매핑 확인
        print(f"\n📊 인덱스 '{news_index}' 매핑 확인...")
        try:
            mapping_result = await os_client.get_mapping(news_index)
            if mapping_result:
                print("   ✅ 매핑 조회 성공")
                # 주요 필드 확인
                mappings = mapping_result.get(news_index, {}).get("mappings", {})
                properties = mappings.get("properties", {})
                field_names = list(properties.keys())[:10]  # 상위 10개 필드만
                print(f"   📝 주요 필드들: {field_names}")
            else:
                print("   ❌ 매핑 조회 결과 없음")
        except Exception as e:
            print(f"   ❌ 매핑 조회 실패: {e}")

    except Exception as e:
        print(f"❌ OpenSearch 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_opensearch_connection())