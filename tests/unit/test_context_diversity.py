#!/usr/bin/env python3
"""컨텍스트 다양성 최적화 테스트"""
import asyncio
import sys
import time
from datetime import datetime, timedelta
sys.path.append('.')

async def test_diversity_optimization():
    """다양성 최적화 테스트"""
    print("🌈 컨텍스트 다양성 최적화 테스트")
    print("=" * 60)

    # 다양성 테스트를 위한 문서 세트
    test_documents = [
        # 반도체 관련 (같은 주제)
        {
            "content": "삼성전자가 새로운 메모리 반도체 기술을 개발했습니다.",
            "title": "삼성 메모리 기술 혁신",
            "source": "tech_news",
            "score": 0.95,
            "timestamp": "2024-01-15T10:00:00Z"
        },
        {
            "content": "SK하이닉스도 차세대 메모리 칩 양산에 성공했습니다.",
            "title": "SK하이닉스 메모리 양산",
            "source": "business_daily",
            "score": 0.88,
            "timestamp": "2024-01-16T14:30:00Z"
        },
        {
            "content": "삼성전자 메모리 사업부 실적이 크게 개선되었습니다.",
            "title": "삼성 메모리 실적 호조",
            "source": "tech_news",  # 같은 소스
            "score": 0.91,
            "timestamp": "2024-01-17T09:15:00Z"
        },
        # 자동차 관련 (다른 주제)
        {
            "content": "현대자동차가 전기차 신모델을 공개했습니다.",
            "title": "현대차 전기차 공개",
            "source": "auto_news",
            "score": 0.82,
            "timestamp": "2024-02-01T16:20:00Z"
        },
        {
            "content": "기아차도 전기차 라인업을 확대한다고 발표했습니다.",
            "title": "기아차 전기차 확대",
            "source": "auto_news",  # 같은 소스
            "score": 0.79,
            "timestamp": "2024-02-02T11:45:00Z"
        },
        # 에너지 관련 (또 다른 주제)
        {
            "content": "한국이 SMR 원자로 기술 개발에 투자를 늘린다.",
            "title": "SMR 기술 투자 확대",
            "source": "energy_today",
            "score": 0.86,
            "timestamp": "2024-03-01T08:30:00Z"
        },
        # 바이오 관련
        {
            "content": "삼성바이오로직스가 새로운 의약품 생산 계약을 체결했습니다.",
            "title": "삼성바이오 계약 체결",
            "source": "bio_weekly",
            "score": 0.84,
            "timestamp": "2024-03-15T13:10:00Z"
        },
        # 중복도가 높은 문서들
        {
            "content": "삼성전자 메모리 반도체 기술이 한층 발전했습니다.",
            "title": "삼성 메모리 기술 발전",
            "source": "tech_news",
            "score": 0.89,
            "timestamp": "2024-01-15T11:00:00Z"  # 비슷한 시간
        }
    ]

    try:
        from api.services.context_diversity import diversity_optimizer, optimize_context_diversity, calculate_diversity_score

        print(f"📊 초기 문서 수: {len(test_documents)}개")

        # 1. 원본 다양성 측정
        print("\n1️⃣ 원본 문서 집합 다양성 분석")
        print("-" * 50)

        original_metrics = diversity_optimizer.calculate_diversity_metrics(test_documents)
        print(f"📈 주제 다양성: {original_metrics.topic_diversity:.3f}")
        print(f"📰 소스 다양성: {original_metrics.source_diversity:.3f}")
        print(f"⏰ 시간적 다양성: {original_metrics.temporal_diversity:.3f}")
        print(f"🔍 컨텐츠 독창성: {original_metrics.content_uniqueness:.3f}")
        print(f"🏆 전체 다양성 점수: {original_metrics.overall_score:.3f}")

        # 2. 균형잡힌 다양성 최적화
        target_sizes = [3, 5, 7]
        strategies = ["balanced", "topic_first", "temporal_first"]

        for target_size in target_sizes:
            if target_size >= len(test_documents):
                continue

            print(f"\n2️⃣ 목표 크기: {target_size}개 문서")
            print("-" * 50)

            for strategy in strategies:
                print(f"\n🎯 {strategy} 전략:")

                start_time = time.perf_counter()
                optimized = optimize_context_diversity(
                    test_documents.copy(),
                    target_size,
                    strategy
                )
                elapsed = (time.perf_counter() - start_time) * 1000

                print(f"   ⏱️  실행 시간: {elapsed:.1f}ms")
                print(f"   📄 선택된 문서: {len(optimized)}개")

                # 선택된 문서들의 다양성 분석
                metrics = diversity_optimizer.calculate_diversity_metrics(optimized)
                print(f"   📊 다양성 점수: {metrics.overall_score:.3f}")

                print("   📋 선택된 문서:")
                for i, doc in enumerate(optimized, 1):
                    source = doc.get('source', 'N/A')[:15]
                    title = doc.get('title', 'N/A')[:40]
                    print(f"      {i}. {title} ({source})")

        # 3. 중복 제거 효과 테스트
        print(f"\n3️⃣ 중복 제거 효과")
        print("-" * 50)

        print("원본 문서 해시:")
        for i, doc in enumerate(test_documents[:5], 1):
            content = doc.get("content", "")
            content_hash = diversity_optimizer._calculate_content_hash(content)
            print(f"   {i}. {content_hash} - {doc.get('title', 'N/A')}")

        # 중복 제거 전후 비교
        unique_docs = diversity_optimizer._remove_duplicates(test_documents)
        print(f"\n🔄 중복 제거: {len(test_documents)}개 → {len(unique_docs)}개")
        print(f"📉 중복 비율: {(1 - len(unique_docs)/len(test_documents))*100:.1f}%")

        # 4. 주제별 그룹화 테스트
        print(f"\n4️⃣ 주제별 그룹화")
        print("-" * 50)

        topic_groups = diversity_optimizer._group_by_topics(test_documents)
        for topic, docs in topic_groups.items():
            print(f"📂 {topic}: {len(docs)}개 문서")
            for doc in docs[:2]:  # 각 주제별 최대 2개만 표시
                title = doc.get('title', 'N/A')[:30]
                print(f"   - {title}")

        # 5. 성능 벤치마크
        print(f"\n5️⃣ 성능 벤치마크")
        print("-" * 50)

        # 큰 데이터셋으로 성능 테스트
        large_dataset = test_documents * 10  # 80개 문서
        print(f"📊 테스트 조건: {len(large_dataset)}개 문서")

        start_time = time.perf_counter()
        optimized_large = optimize_context_diversity(large_dataset, 10, "balanced")
        elapsed = (time.perf_counter() - start_time) * 1000

        print(f"⚡ 대용량 최적화: {elapsed:.1f}ms")
        print(f"📈 처리 속도: {len(large_dataset)/elapsed*1000:.1f} docs/sec")

        final_diversity = calculate_diversity_score(optimized_large)
        print(f"🎯 최종 다양성 점수: {final_diversity:.3f}")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n" + "=" * 60)
    print("🧪 엣지 케이스 테스트")
    print("=" * 60)

    from api.services.context_diversity import optimize_context_diversity

    # 빈 리스트
    print("1️⃣ 빈 문서 리스트:")
    result = optimize_context_diversity([], 5)
    print(f"   결과: {len(result)}개")

    # 목표보다 적은 문서
    print("\n2️⃣ 목표보다 적은 문서:")
    small_docs = [
        {"content": "테스트 1", "title": "문서 1", "source": "test"},
        {"content": "테스트 2", "title": "문서 2", "source": "test"}
    ]
    result = optimize_context_diversity(small_docs, 5)
    print(f"   입력: {len(small_docs)}개, 목표: 5개, 결과: {len(result)}개")

    # 모든 문서가 동일한 주제
    print("\n3️⃣ 단일 주제 문서들:")
    single_topic_docs = [
        {"content": f"반도체 관련 뉴스 {i}", "title": f"반도체 {i}", "source": f"source_{i%2}"}
        for i in range(8)
    ]
    result = optimize_context_diversity(single_topic_docs, 4)
    print(f"   결과: {len(result)}개 (소스별로 분산되어야 함)")

    print("\n✅ 엣지 케이스 테스트 완료")

if __name__ == "__main__":
    asyncio.run(test_diversity_optimization())
    asyncio.run(test_edge_cases())