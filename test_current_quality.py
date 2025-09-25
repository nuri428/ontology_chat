#!/usr/bin/env python3
"""현재 적용된 모든 기능의 종합 품질 테스트"""
import asyncio
import sys
import time
from datetime import datetime
sys.path.append('.')

async def test_integrated_pipeline():
    """통합 파이프라인 품질 테스트"""
    print("🔬 통합 컨텍스트 엔지니어링 품질 테스트")
    print("=" * 70)

    try:
        from api.services.chat_service import ChatService

        service = ChatService()

        # 다양한 복잡도의 테스트 쿼리
        test_queries = [
            {
                "query": "SMR 관련 유망 투자 종목 분석",
                "complexity": "중간",
                "expected_features": ["에너지", "원자력", "투자", "상장사"]
            },
            {
                "query": "반도체 메모리 시장 전망과 삼성전자 경쟁력",
                "complexity": "높음",
                "expected_features": ["반도체", "메모리", "삼성전자", "시장분석"]
            },
            {
                "query": "전기차 배터리 공급망 이슈",
                "complexity": "중간",
                "expected_features": ["전기차", "배터리", "공급망"]
            }
        ]

        print(f"📋 테스트 대상 기능:")
        print(f"   ✅ Ollama LLM (llama3.1:8b)")
        print(f"   ✅ 컨텍스트 캐싱")
        print(f"   ✅ 동적 프루닝")
        print(f"   ✅ 의미적 유사도 필터링")
        print(f"   ✅ 다양성 최적화")
        print(f"   ✅ Neo4j 온톨로지 확장")

        total_metrics = {
            "total_queries": 0,
            "avg_response_time": 0,
            "cache_hits": 0,
            "semantic_improvements": 0,
            "diversity_scores": [],
            "quality_ratings": []
        }

        for i, test_case in enumerate(test_queries, 1):
            query = test_case["query"]
            complexity = test_case["complexity"]

            print(f"\n{i}️⃣  쿼리: '{query}'")
            print(f"   복잡도: {complexity}")
            print("-" * 60)

            # 전체 파이프라인 실행
            start_time = time.perf_counter()

            try:
                # 1. 키워드 추출 (Ollama LLM)
                print("🔍 1단계: Ollama LLM 키워드 추출")
                keyword_start = time.perf_counter()
                keywords = await service._get_context_keywords(query)
                keyword_time = (time.perf_counter() - keyword_start) * 1000

                print(f"   ⏱️  키워드 추출: {keyword_time:.1f}ms")
                print(f"   📝 추출 키워드: '{keywords}'")

                # 2. 뉴스 검색 (온톨로지 강화 + 모든 필터 적용)
                print(f"\n🔍 2단계: 통합 뉴스 검색")
                search_start = time.perf_counter()

                news_hits, search_time, search_error = await service._search_news_with_ontology(query, size=5)
                search_elapsed = (time.perf_counter() - search_start) * 1000

                print(f"   ⏱️  검색 시간: {search_elapsed:.1f}ms")
                print(f"   📊 검색 결과: {len(news_hits)}건")

                if news_hits:
                    print(f"   📄 결과 미리보기:")
                    for j, hit in enumerate(news_hits[:3], 1):
                        title = hit.get('title', 'N/A')[:50]
                        semantic_score = hit.get('semantic_score', 0)
                        combined_score = hit.get('combined_score', 0)
                        print(f"      {j}. {title}...")
                        print(f"         의미점수: {semantic_score:.3f}, 통합점수: {combined_score:.3f}")

                # 3. 그래프 검색
                print(f"\n🔗 3단계: Neo4j 그래프 검색")
                graph_start = time.perf_counter()

                graph_rows, graph_time, graph_error = await service._query_graph(query, limit=5)
                graph_elapsed = (time.perf_counter() - graph_start) * 1000

                print(f"   ⏱️  그래프 검색: {graph_elapsed:.1f}ms")
                print(f"   🔗 그래프 결과: {len(graph_rows)}개 노드")

                if graph_rows:
                    print(f"   📊 그래프 노드:")
                    for j, row in enumerate(graph_rows[:3], 1):
                        node = row.get('n', {})
                        name = node.get('name', node.get('title', 'N/A'))[:30]
                        print(f"      {j}. {name}")

                # 4. 전체 파이프라인 시간
                total_time = (time.perf_counter() - start_time) * 1000
                print(f"\n⏱️  전체 파이프라인: {total_time:.1f}ms")

                # 5. 품질 분석
                print(f"\n📈 품질 분석:")

                # 다양성 점수 계산
                diversity_score = 0.0
                if news_hits:
                    from api.services.context_diversity import calculate_diversity_score
                    diversity_score = calculate_diversity_score(news_hits)
                    print(f"   🌈 다양성 점수: {diversity_score:.3f}")
                    total_metrics["diversity_scores"].append(diversity_score)

                # 캐시 효과 확인
                from api.services.context_cache import context_cache
                cache_stats = context_cache.get_stats()
                cache_hit_rate = cache_stats.get('hit_rate', 0) * 100
                print(f"   🎯 캐시 히트율: {cache_hit_rate:.1f}%")

                # 검색 품질 평가 - 의미적 점수 활용
                relevance_score = 0
                if news_hits:
                    # 의미적 점수가 있으면 우선 사용, 없으면 키워드 매칭
                    semantic_scores = [hit.get('semantic_score', 0) for hit in news_hits]

                    if any(score > 0 for score in semantic_scores):
                        # 의미적 점수 사용 (더 정확한 관련성 측정)
                        relevance_score = sum(semantic_scores) / len(semantic_scores)
                    else:
                        # 폴백: 제목에서 쿼리 키워드 매칭도 계산
                        query_words = set(query.lower().split())
                        for hit in news_hits:
                            title = hit.get('title', '').lower()
                            title_words = set(title.split())
                            overlap = len(query_words & title_words)
                            relevance_score += overlap / len(query_words) if query_words else 0
                        relevance_score /= len(news_hits)

                print(f"   🎯 관련성 점수: {relevance_score:.3f}")

                # 응답 완성도 평가
                completeness = 0
                if news_hits: completeness += 0.4
                if graph_rows: completeness += 0.3
                if keywords: completeness += 0.3

                print(f"   ✅ 완성도 점수: {completeness:.3f}")

                # 전체 품질 점수
                quality_score = (diversity_score + relevance_score + completeness) / 3
                print(f"   🏆 종합 품질: {quality_score:.3f}")

                # 메트릭 누적
                total_metrics["total_queries"] += 1
                total_metrics["avg_response_time"] += total_time
                total_metrics["quality_ratings"].append(quality_score)

                if cache_hit_rate > 0:
                    total_metrics["cache_hits"] += 1

                if news_hits and any(hit.get('semantic_score', 0) > 0.7 for hit in news_hits):
                    total_metrics["semantic_improvements"] += 1

            except Exception as e:
                print(f"   ❌ 파이프라인 실패: {e}")
                import traceback
                traceback.print_exc()

        # 종합 분석
        print(f"\n" + "=" * 70)
        print("📊 종합 성능 분석")
        print("=" * 70)

        if total_metrics["total_queries"] > 0:
            avg_time = total_metrics["avg_response_time"] / total_metrics["total_queries"]
            avg_quality = sum(total_metrics["quality_ratings"]) / len(total_metrics["quality_ratings"]) if total_metrics["quality_ratings"] else 0
            avg_diversity = sum(total_metrics["diversity_scores"]) / len(total_metrics["diversity_scores"]) if total_metrics["diversity_scores"] else 0

            print(f"🎯 핵심 지표:")
            print(f"   • 평균 응답 시간: {avg_time:.1f}ms")
            print(f"   • 평균 품질 점수: {avg_quality:.3f}")
            print(f"   • 평균 다양성: {avg_diversity:.3f}")
            print(f"   • 캐시 활용률: {total_metrics['cache_hits']}/{total_metrics['total_queries']}")
            print(f"   • 의미적 개선: {total_metrics['semantic_improvements']}/{total_metrics['total_queries']}")

            # 성능 등급 평가
            print(f"\n🏅 성능 등급:")
            if avg_time < 2000: print(f"   ⚡ 응답 속도: A급 (2초 미만)")
            elif avg_time < 5000: print(f"   🔶 응답 속도: B급 (5초 미만)")
            else: print(f"   🔴 응답 속도: C급 (5초 이상)")

            if avg_quality > 0.8: print(f"   🏆 답변 품질: A급 (0.8 이상)")
            elif avg_quality > 0.6: print(f"   🥈 답변 품질: B급 (0.6 이상)")
            else: print(f"   🥉 답변 품질: C급 (0.6 미만)")

            if avg_diversity > 0.7: print(f"   🌈 정보 다양성: A급 (0.7 이상)")
            elif avg_diversity > 0.5: print(f"   🎨 정보 다양성: B급 (0.5 이상)")
            else: print(f"   📝 정보 다양성: C급 (0.5 미만)")

        # 개선 제안
        print(f"\n💡 개선 제안:")
        if avg_time > 3000:
            print(f"   ⚡ 응답 속도 개선 필요 - 캐싱 강화 권장")
        if avg_diversity < 0.6:
            print(f"   🌈 다양성 필터링 강화 필요")
        if total_metrics['cache_hits'] < total_metrics['total_queries'] * 0.3:
            print(f"   🎯 캐시 히트율 개선 - TTL 조정 권장")

        # 리소스 사용량
        cache_stats = context_cache.get_stats()
        print(f"\n📈 리소스 현황:")
        print(f"   • 캐시 사용량: {cache_stats.get('cache_size', 0)}/{cache_stats.get('max_size', 100)}")
        print(f"   • 총 캐시 요청: {cache_stats.get('total_requests', 0)}회")
        print(f"   • 캐시 제거: {cache_stats.get('evictions', 0)}회")

        # 정리
        await service.neo.close()

    except Exception as e:
        print(f"❌ 품질 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def benchmark_vs_baseline():
    """기준선 대비 성능 벤치마크"""
    print(f"\n" + "=" * 70)
    print("⚖️  기준선 대비 성능 벤치마크")
    print("=" * 70)

    # 간단한 키워드 vs LLM 키워드 비교
    test_query = "SMR 소형모듈원자로 투자 전망"

    print(f"📋 벤치마크 쿼리: '{test_query}'")

    try:
        from api.services.chat_service import ChatService
        service = ChatService()

        # 1. 기존 방식 (폴백)
        print(f"\n1️⃣ 기존 방식 (폴백 키워드):")
        start = time.perf_counter()
        fallback_keywords = service._fallback_keyword_extraction(test_query)
        fallback_time = (time.perf_counter() - start) * 1000
        print(f"   ⏱️  처리 시간: {fallback_time:.1f}ms")
        print(f"   📝 키워드: '{fallback_keywords}'")

        # 2. LLM 방식
        print(f"\n2️⃣ Ollama LLM 방식:")
        start = time.perf_counter()
        llm_keywords = await service._get_context_keywords(test_query)
        llm_time = (time.perf_counter() - start) * 1000
        print(f"   ⏱️  처리 시간: {llm_time:.1f}ms")
        print(f"   📝 키워드: '{llm_keywords}'")

        # 비교 분석
        print(f"\n📊 비교 분석:")
        speedup = fallback_time / llm_time if llm_time > 0 else 0
        if speedup < 1:
            print(f"   ⚡ LLM이 {1/speedup:.1f}배 빠름 (예상 밖)")
        else:
            print(f"   🐌 LLM이 {speedup:.1f}배 느림 (정상 - 품질 향상 대가)")

        # 키워드 품질 비교
        fallback_words = set(fallback_keywords.split())
        llm_words = set(llm_keywords.split()) if llm_keywords else set()

        overlap = len(fallback_words & llm_words)
        llm_unique = len(llm_words - fallback_words)

        print(f"   🔄 공통 키워드: {overlap}개")
        print(f"   ✨ LLM 추가 키워드: {llm_unique}개")
        print(f"   📈 키워드 확장률: {llm_unique/len(fallback_words)*100:.1f}%" if fallback_words else "N/A")

        await service.neo.close()

    except Exception as e:
        print(f"   ❌ 벤치마크 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_integrated_pipeline())
    asyncio.run(benchmark_vs_baseline())