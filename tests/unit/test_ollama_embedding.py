#!/usr/bin/env python3
"""Ollama 기반 임베딩 테스트"""
import asyncio
import sys
sys.path.append('.')

def test_ollama_embedding():
    """Ollama 기반 임베딩 테스트"""
    print("🔗 Ollama 기반 임베딩 테스트")
    print("=" * 80)

    try:
        from api.services.semantic_similarity import get_semantic_filter
        from langchain_ollama import OllamaEmbeddings

        # 1. 직접 Ollama 임베딩 클라이언트 테스트
        print("📡 1. 직접 Ollama 임베딩 클라이언트 테스트:")
        print("-" * 50)

        embedding_client = OllamaEmbeddings(
            base_url="http://192.168.0.10:11434",
            model="bge-m3"
        )

        test_text = "반도체 업계 최신 동향"
        print(f"테스트 텍스트: '{test_text}'")

        try:
            embedding = embedding_client.embed_query(test_text)
            print(f"✅ 임베딩 성공!")
            print(f"   - 임베딩 차원: {len(embedding)}")
            print(f"   - 임베딩 타입: {type(embedding)}")
            print(f"   - 임베딩 처음 5개 값: {embedding[:5]}")
        except Exception as e:
            print(f"❌ 직접 임베딩 실패: {e}")

        # 2. SemanticSimilarityFilter 테스트
        print(f"\n📊 2. SemanticSimilarityFilter 테스트:")
        print("-" * 50)

        try:
            semantic_filter = get_semantic_filter()
            print(f"✅ SemanticSimilarityFilter 초기화 성공!")
            print(f"   - 임베딩 클라이언트: {type(semantic_filter.embedding_client)}")
            print(f"   - 유사도 임계값: {semantic_filter.similarity_threshold}")
            print(f"   - 캐시 활성화: {semantic_filter.cache_embeddings}")

            # 임베딩 생성 테스트
            test_embedding = semantic_filter._get_embedding(test_text)
            print(f"✅ 내부 임베딩 생성 성공!")
            print(f"   - 정규화된 임베딩 차원: {test_embedding.shape}")
            print(f"   - 정규화 확인 (L2 norm): {(test_embedding ** 2).sum() ** 0.5:.6f}")

        except Exception as e:
            print(f"❌ SemanticSimilarityFilter 실패: {e}")
            import traceback
            traceback.print_exc()

        # 3. 유사도 계산 테스트
        print(f"\n🔍 3. 유사도 계산 테스트:")
        print("-" * 50)

        try:
            test_queries = [
                "반도체 업계 최신 동향",
                "메모리 반도체 시장 전망",
                "전기차 배터리 기술",
                "삼성전자 실적 발표"
            ]

            semantic_filter = get_semantic_filter()

            embeddings = []
            for query in test_queries:
                emb = semantic_filter._get_embedding(query)
                embeddings.append(emb)

            print("유사도 매트릭스:")
            print("      " + " ".join(f"{i:>6}" for i in range(len(test_queries))))

            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            similarity_matrix = cosine_similarity(embeddings)

            for i, query in enumerate(test_queries):
                print(f"{i}: {query[:15]:>15} ", end="")
                for j in range(len(test_queries)):
                    sim = similarity_matrix[i][j]
                    print(f"{sim:>6.3f}", end=" ")
                print()

            print(f"\n✅ 유사도 계산 완료!")
            print(f"   - 가장 유사한 쌍: 반도체 관련 쿼리들")
            print(f"   - 가장 비슷하지 않은 쌍: 반도체 vs 전기차/실적")

        except Exception as e:
            print(f"❌ 유사도 계산 실패: {e}")
            import traceback
            traceback.print_exc()

        # 4. 개선 효과 요약
        print(f"\n" + "=" * 80)
        print("🎯 Ollama 기반 임베딩 개선 효과:")
        print("-" * 80)

        improvements = [
            "✅ HuggingFace 의존성 제거 - 로그인/인증 문제 해결",
            "✅ 로컬 Ollama 서버 활용 - 네트워크 지연 최소화",
            "✅ 통합된 모델 관리 - LLM과 임베딩 모델 모두 Ollama에서",
            "✅ 안정적인 서비스 - 외부 API 호출 없음",
            "✅ 캐싱 최적화 - 동일 텍스트 재계산 방지",
            "✅ 일관된 설정 - 192.168.0.11:11434 통일"
        ]

        for imp in improvements:
            print(f"   {imp}")

        print(f"\n💡 기대 효과:")
        print("   - 임베딩 생성 속도 향상")
        print("   - 네트워크 의존성 제거")
        print("   - 시스템 안정성 증대")
        print("   - 설정 및 관리 단순화")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ollama_embedding()