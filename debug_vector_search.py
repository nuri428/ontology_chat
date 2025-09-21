#!/usr/bin/env python3
"""
벡터 검색 디버깅 스크립트
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.adapters.mcp_opensearch import OpenSearchMCP
from api.adapters.ollama_embedding import OllamaEmbeddingMCP
from api.config import settings

async def debug_vector_search():
    print("🔍 벡터 검색 디버깅 시작")
    print("="*50)

    # OpenSearch와 BGE-M3 초기화
    os_client = OpenSearchMCP()
    embedding_client = OllamaEmbeddingMCP()

    # 테스트 쿼리
    test_query = "한화 방산"
    print(f"테스트 쿼리: {test_query}")

    # 1. 임베딩 생성
    print("\n1. 임베딩 생성...")
    embedding = await embedding_client.encode(test_query)
    print(f"임베딩 차원: {len(embedding)}")

    # 2. 벡터 검색 쿼리 테스트
    print("\n2. 벡터 검색 쿼리 테스트...")

    # OpenSearch 2.x 방식으로 직접 테스트
    vector_query = {
        "size": 3,
        "query": {
            "knn": {
                "vector_field": {
                    "vector": embedding,
                    "k": 3
                }
            }
        },
        "_source": ["text", "metadata.title"]
    }

    try:
        result = await os_client.search(
            index="news_article_embedding",
            query=vector_query,
            size=3
        )

        hits = result.get("hits", {}).get("hits", [])
        print(f"✅ 벡터 검색 성공! 결과: {len(hits)}개")

        for i, hit in enumerate(hits, 1):
            source = hit.get("_source", {})
            score = hit.get("_score", 0)
            text = source.get("text", "")[:100] + "..."
            print(f"   {i}. (점수: {score:.4f}) {text}")

    except Exception as e:
        print(f"❌ 벡터 검색 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_vector_search())