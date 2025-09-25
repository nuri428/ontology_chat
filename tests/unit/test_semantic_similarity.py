#!/usr/bin/env python3
"""의미적 유사도 필터링 시스템 테스트"""
import asyncio
import sys
import time
sys.path.append('.')

async def test_semantic_filtering():
    """의미적 유사도 필터링 테스트"""
    print("🧠 의미적 유사도 필터링 테스트")
    print("=" * 60)

    # 테스트용 문서들 (실제로는 OpenSearch에서 가져옴)
    test_documents = [
        {
            "content": "삼성전자가 새로운 반도체 기술을 개발했다. 메모리 반도체 분야에서 혁신적인 성과를 보였다.",
            "title": "삼성전자 반도체 기술 혁신",
            "score": 0.95
        },
        {
            "content": "SK하이닉스도 메모리 칩 생산 기술을 향상시켰다. 차세대 메모리 기술 개발에 박차를 가하고 있다.",
            "title": "SK하이닉스 메모리 기술 발전",
            "score": 0.88
        },
        {
            "content": "현대자동차가 전기차 신모델을 출시했다. 배터리 기술과 자율주행 기능을 강화했다.",
            "title": "현대차 전기차 신모델 출시",
            "score": 0.82
        },
        {
            "content": "LG에너지솔루션이 배터리 생산을 확대한다. 전기차용 배터리 수요 증가에 대응하고 있다.",
            "title": "LG에너지솔루션 배터리 생산 확대",
            "score": 0.79
        },
        {
            "content": "삼성전자의 메모리 반도체 사업 실적이 호조를 보이고 있다. 글로벌 시장에서 점유율을 높이고 있다.",
            "title": "삼성전자 메모리 사업 호조",
            "score": 0.91
        }
    ]

    # 테스트 쿼리들
    test_queries = [
        "반도체 메모리 기술 발전",
        "전기차 배터리 기술",
        "삼성전자 반도체 실적"
    ]

    try:
        from api.services.semantic_similarity import semantic_filter, filter_similar_content, semantic_rerank

        # 경량 모델로 테스트 (빠른 테스트를 위해)
        print("⚙️  경량 모델로 초기화 중...")
        # 실제 환경에서는 더 강력한 모델 사용

        for i, query in enumerate(test_queries, 1):
            print(f"\n{i}️⃣  테스트 쿼리: '{query}'")
            print("-" * 50)

            # 1. 원본 문서 점수
            print("📄 원본 문서 순위:")
            for j, doc in enumerate(test_documents[:3], 1):
                print(f"   {j}. {doc['title']} (점수: {doc['score']:.2f})")

            # 2. 의미적 재정렬 테스트
            print("\n🔄 의미적 재정렬 중...")
            start_time = time.perf_counter()

            try:
                reranked = await semantic_rerank(query, test_documents.copy())
                elapsed = (time.perf_counter() - start_time) * 1000

                print(f"   ✓ 재정렬 완료 ({elapsed:.1f}ms)")
                print("\n📊 재정렬 결과:")
                for j, doc in enumerate(reranked[:3], 1):
                    semantic_score = doc.get('semantic_score', 0)
                    combined_score = doc.get('combined_score', 0)
                    print(f"   {j}. {doc['title']}")
                    print(f"      의미점수: {semantic_score:.3f}, 통합점수: {combined_score:.3f}")

            except Exception as e:
                print(f"   ❌ 재정렬 실패: {e}")

            # 3. 유사도 필터링 테스트
            print(f"\n🎯 유사도 필터링 (임계값: 0.6)")
            start_time = time.perf_counter()

            try:
                filtered = await filter_similar_content(
                    query,
                    test_documents.copy(),
                    threshold=0.6,
                    top_k=3
                )
                elapsed = (time.perf_counter() - start_time) * 1000

                print(f"   ✓ 필터링 완료 ({elapsed:.1f}ms)")
                print(f"   📉 {len(test_documents)}건 → {len(filtered)}건")

                if filtered:
                    print("\n🏆 최종 선택된 문서:")
                    for j, doc in enumerate(filtered, 1):
                        semantic_score = doc.get('semantic_score', 0)
                        print(f"   {j}. {doc['title']} (의미점수: {semantic_score:.3f})")

            except Exception as e:
                print(f"   ❌ 필터링 실패: {e}")

    except ImportError as e:
        print(f"❌ 의존성 누락: {e}")
        print("💡 다음 명령으로 설치하세요:")
        print("   uv add sentence-transformers scikit-learn torch")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

async def test_semantic_diversity():
    """의미적 다양성 테스트"""
    print("\n" + "=" * 60)
    print("🌈 의미적 다양성 테스트")
    print("=" * 60)

    # 중복성이 높은 문서들
    similar_docs = [
        {"content": "삼성전자 메모리 반도체 성과", "title": "삼성 메모리 1"},
        {"content": "삼성 반도체 메모리 기술 발전", "title": "삼성 메모리 2"},
        {"content": "현대차 전기차 기술 혁신", "title": "현대차 전기차"},
        {"content": "LG배터리 생산 확대 계획", "title": "LG 배터리"}
    ]

    try:
        from api.services.semantic_similarity import semantic_filter

        # 다양성 점수 계산
        diversity_score = semantic_filter.calculate_semantic_diversity(similar_docs)
        print(f"📊 문서 집합의 다양성 점수: {diversity_score:.3f}")

        if diversity_score < 0.3:
            print("   ⚠️  낮은 다양성 - 중복 컨텐츠가 많음")
        elif diversity_score < 0.6:
            print("   🔶 보통 다양성")
        else:
            print("   ✅ 높은 다양성 - 다양한 주제 포함")

        # 클러스터링 테스트
        print(f"\n🗂️  의미적 클러스터링 (2개 클러스터):")
        clusters = semantic_filter.find_semantic_clusters(similar_docs, n_clusters=2)

        for i, cluster in enumerate(clusters, 1):
            print(f"   클러스터 {i}: {len(cluster)}개 문서")
            for doc in cluster:
                print(f"      - {doc['title']}")

    except Exception as e:
        print(f"❌ 다양성 테스트 실패: {e}")

async def performance_test():
    """성능 벤치마크 테스트"""
    print("\n" + "=" * 60)
    print("⚡ 성능 벤치마크 테스트")
    print("=" * 60)

    # 더 많은 문서로 성능 테스트
    large_doc_set = [
        {"content": f"테스트 문서 {i} - 반도체 관련 내용입니다", "title": f"문서 {i}"}
        for i in range(20)
    ]

    query = "반도체 기술 발전"

    try:
        from api.services.semantic_similarity import semantic_rerank, filter_similar_content

        print(f"📊 테스트 조건: {len(large_doc_set)}개 문서")

        # 재정렬 성능 테스트
        print("\n1️⃣ 의미적 재정렬 성능:")
        start = time.perf_counter()
        reranked = await semantic_rerank(query, large_doc_set.copy())
        elapsed = (time.perf_counter() - start) * 1000
        print(f"   ⏱️  실행 시간: {elapsed:.1f}ms")
        print(f"   📈 처리 속도: {len(large_doc_set)/elapsed*1000:.1f} docs/sec")

        # 필터링 성능 테스트
        print("\n2️⃣ 유사도 필터링 성능:")
        start = time.perf_counter()
        filtered = await filter_similar_content(query, large_doc_set.copy(), top_k=5)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"   ⏱️  실행 시간: {elapsed:.1f}ms")
        print(f"   📉 필터링 비율: {len(filtered)/len(large_doc_set)*100:.1f}%")

    except Exception as e:
        print(f"❌ 성능 테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_semantic_filtering())
    asyncio.run(test_semantic_diversity())
    asyncio.run(performance_test())