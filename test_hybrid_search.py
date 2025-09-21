#!/usr/bin/env python3
"""
하이브리드 검색 동작 테스트 스크립트
"""

import asyncio
import sys
import os

# 프로젝트 경로를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.services.report_service import ReportService
from api.config import settings
from api.logging import setup_logging

logger = setup_logging()

async def test_hybrid_search():
    """하이브리드 검색 테스트"""
    print("🔍 하이브리드 검색 시스템 테스트 시작")
    print("="*50)

    # 설정 확인
    print(f"✅ BGE_M3_HOST: {settings.bge_m3_host}")
    print(f"✅ BGE_M3_MODEL: {settings.bge_m3_model}")
    print(f"✅ ENABLE_HYBRID_SEARCH: {settings.enable_hybrid_search}")
    print(f"✅ NEWS_EMBEDDING_INDEX: {settings.news_embedding_index}")
    print()

    if not settings.enable_hybrid_search:
        print("❌ 하이브리드 검색이 비활성화되어 있습니다!")
        return

    # ReportService 초기화
    service = ReportService()

    # BGE-M3 연결 테스트
    print("🔗 BGE-M3 Ollama 연결 테스트...")
    if service.embedding:
        try:
            ping_result = await service.embedding.ping()
            if ping_result:
                print("✅ BGE-M3 서버 연결 성공!")
            else:
                print("❌ BGE-M3 서버 연결 실패!")
                return
        except Exception as e:
            print(f"❌ BGE-M3 서버 연결 오류: {e}")
            return
    else:
        print("❌ BGE-M3 임베딩 서비스가 초기화되지 않았습니다!")
        return

    # 임베딩 생성 테스트
    test_query = "한화 방산 계약"
    print(f"🧠 임베딩 생성 테스트: '{test_query}'")
    try:
        embedding = await service.embedding.encode(test_query)
        print(f"✅ 임베딩 생성 성공! 차원: {len(embedding)}")
        print(f"   처음 5개 값: {embedding[:5]}")
    except Exception as e:
        print(f"❌ 임베딩 생성 실패: {e}")
        return

    print()

    # 하이브리드 검색 테스트
    print(f"🔍 하이브리드 검색 테스트: '{test_query}'")
    try:
        # 하이브리드 검색 실행
        results = await service._hybrid_search(test_query, size=5)
        print(f"✅ 하이브리드 검색 성공! 결과: {len(results)}개")

        # 상위 3개 결과 출력
        for i, result in enumerate(results[:3], 1):
            source = result.get("_source", {})
            metadata = source.get("metadata", {})
            title = source.get("text", metadata.get("title", "제목 없음"))[:100]
            score = result.get("_score", 0)
            print(f"   {i}. (점수: {score:.4f}) {title}...")

    except Exception as e:
        print(f"❌ 하이브리드 검색 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    print()

    # 기존 키워드 검색과 비교
    print("📊 기존 키워드 검색과 비교...")
    try:
        keyword_results = await service._keyword_search(settings.news_bulk_index, test_query, size=5)
        print(f"   키워드 검색 (news_bulk): {len(keyword_results)}개")

        embedding_keyword_results = await service._keyword_search(settings.news_embedding_index, test_query, size=5)
        print(f"   키워드 검색 (embedding 인덱스): {len(embedding_keyword_results)}개")

        vector_results = await service._vector_search(settings.news_embedding_index, embedding, size=5)
        print(f"   벡터 검색: {len(vector_results)}개")
        print(f"   하이브리드 검색 (RRF 결합): {len(results)}개")

    except Exception as e:
        print(f"⚠️ 비교 검색 오류: {e}")

    print()
    print("🎉 하이브리드 검색 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(test_hybrid_search())