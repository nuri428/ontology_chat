#!/usr/bin/env python3
"""
신규 필드 데이터 분포 상세 분석
"""

import asyncio
from opensearchpy import AsyncOpenSearch
import json


async def analyze_field_coverage():
    """필드 채워짐 상태를 시간대별/문서별로 상세 분석"""

    client = AsyncOpenSearch(
        hosts=["http://localhost:9200"],
        http_auth=("admin", "admin"),
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False
    )

    try:
        index_name = "news_article_bulk"

        print("=" * 100)
        print("🔍 신규 필드 채워짐 상세 분석")
        print("=" * 100)

        # 1. 필드별 존재 여부 샘플링 (랜덤 100개)
        print("\n1️⃣ 랜덤 샘플 100개 분석")
        print("-" * 100)

        # quality_score가 존재하는 문서 조회
        query_with_quality = {
            "query": {
                "exists": {"field": "quality_score"}
            },
            "size": 50
        }

        result_with = await client.search(index=index_name, body=query_with_quality)
        hits_with = result_with.get("hits", {}).get("hits", [])

        # quality_score가 없는 문서 조회
        query_without_quality = {
            "query": {
                "bool": {
                    "must_not": [
                        {"exists": {"field": "quality_score"}}
                    ]
                }
            },
            "size": 50
        }

        result_without = await client.search(index=index_name, body=query_without_quality)
        hits_without = result_without.get("hits", {}).get("hits", [])

        print(f"✅ quality_score 존재하는 문서: {len(hits_with)}개")
        print(f"❌ quality_score 없는 문서: {len(hits_without)}개")

        # 샘플 출력 (각 5개씩)
        if hits_with:
            print("\n[quality_score 존재하는 문서 샘플 5개]")
            for i, hit in enumerate(hits_with[:5], 1):
                src = hit["_source"]
                print(f"\n  문서 #{i}:")
                print(f"    ID: {hit['_id']}")
                print(f"    제목: {src.get('title', 'N/A')[:60]}")
                print(f"    quality_score: {src.get('quality_score')}")
                print(f"    is_featured: {src.get('is_featured')}")
                print(f"    neo4j_synced: {src.get('neo4j_synced')}")
                print(f"    neo4j_node_count: {src.get('neo4j_node_count')}")
                print(f"    ontology_status: {src.get('ontology_status')}")

        if hits_without:
            print("\n[quality_score 없는 문서 샘플 5개]")
            for i, hit in enumerate(hits_without[:5], 1):
                src = hit["_source"]
                print(f"\n  문서 #{i}:")
                print(f"    ID: {hit['_id']}")
                print(f"    제목: {src.get('title', 'N/A')[:60]}")
                print(f"    quality_score: {src.get('quality_score')}")
                print(f"    is_featured: {src.get('is_featured')}")
                print(f"    neo4j_synced: {src.get('neo4j_synced')}")

        # 2. 전체 통계 재확인 (정확한 수치)
        print("\n\n2️⃣ 전체 통계 재확인")
        print("-" * 100)

        # 총 문서 수
        count_all = await client.count(index=index_name, body={"query": {"match_all": {}}})
        total_docs = count_all.get("count", 0)

        # 각 필드별 존재 개수
        fields = [
            "quality_score",
            "is_featured",
            "neo4j_synced",
            "neo4j_node_count",
            "ontology_status"
        ]

        print(f"총 문서 수: {total_docs:,}개\n")
        print(f"{'필드명':25s} | {'존재':>10s} | {'비율':>8s}")
        print("-" * 100)

        for field in fields:
            count_result = await client.count(
                index=index_name,
                body={
                    "query": {
                        "exists": {"field": field}
                    }
                }
            )
            exists_count = count_result.get("count", 0)
            ratio = (exists_count / total_docs * 100) if total_docs > 0 else 0

            print(f"{field:25s} | {exists_count:10,}개 | {ratio:7.1f}%")

        # 3. 필드 값 분포 (quality_score 히스토그램)
        print("\n\n3️⃣ quality_score 값 분포")
        print("-" * 100)

        histogram_query = {
            "query": {
                "exists": {"field": "quality_score"}
            },
            "size": 0,
            "aggs": {
                "quality_distribution": {
                    "histogram": {
                        "field": "quality_score",
                        "interval": 0.1
                    }
                },
                "quality_stats": {
                    "stats": {"field": "quality_score"}
                }
            }
        }

        hist_result = await client.search(index=index_name, body=histogram_query)
        aggs = hist_result.get("aggregations", {})

        stats = aggs.get("quality_stats", {})
        print(f"평균: {stats.get('avg', 0):.3f}")
        print(f"최소: {stats.get('min', 0):.3f}")
        print(f"최대: {stats.get('max', 0):.3f}")
        print(f"합계: {stats.get('sum', 0):,.0f}")
        print(f"개수: {stats.get('count', 0):,}개")

        print("\n분포:")
        buckets = aggs.get("quality_distribution", {}).get("buckets", [])
        for bucket in buckets:
            if bucket["doc_count"] > 0:
                key = bucket["key"]
                count = bucket["doc_count"]
                bar = "█" * min(int(count / 1000), 50)
                print(f"  {key:.1f} ~ {key+0.1:.1f}: {count:6,}개 {bar}")

        # 4. neo4j_synced True/False 분포
        print("\n\n4️⃣ neo4j_synced 분포")
        print("-" * 100)

        synced_true = await client.count(
            index=index_name,
            body={"query": {"term": {"neo4j_synced": True}}}
        )

        synced_false = await client.count(
            index=index_name,
            body={"query": {"term": {"neo4j_synced": False}}}
        )

        synced_null = total_docs - synced_true.get("count", 0) - synced_false.get("count", 0)

        print(f"True:  {synced_true.get('count', 0):10,}개 ({synced_true.get('count', 0)/total_docs*100:5.1f}%)")
        print(f"False: {synced_false.get('count', 0):10,}개 ({synced_false.get('count', 0)/total_docs*100:5.1f}%)")
        print(f"NULL:  {synced_null:10,}개 ({synced_null/total_docs*100:5.1f}%)")

        # 5. ontology_status 분포
        print("\n\n5️⃣ ontology_status 분포")
        print("-" * 100)

        status_query = {
            "size": 0,
            "aggs": {
                "status_breakdown": {
                    "terms": {
                        "field": "ontology_status.keyword",
                        "size": 20
                    }
                }
            }
        }

        status_result = await client.search(index=index_name, body=status_query)
        status_buckets = status_result.get("aggregations", {}).get("status_breakdown", {}).get("buckets", [])

        for bucket in status_buckets:
            status = bucket["key"]
            count = bucket["doc_count"]
            ratio = (count / total_docs * 100) if total_docs > 0 else 0
            print(f"{status:20s}: {count:10,}개 ({ratio:5.1f}%)")

        # 6. 결론
        print("\n\n" + "=" * 100)
        print("📊 결론")
        print("=" * 100)

        quality_count = await client.count(
            index=index_name,
            body={"query": {"exists": {"field": "quality_score"}}}
        )
        quality_ratio = (quality_count.get("count", 0) / total_docs * 100) if total_docs > 0 else 0

        print(f"\n총 문서 수: {total_docs:,}개")
        print(f"quality_score 존재: {quality_count.get('count', 0):,}개 ({quality_ratio:.1f}%)")

        if quality_ratio > 80:
            print("\n✅ 상태: 양호")
            print("   - 대부분의 문서에 신규 필드가 채워져 있습니다.")
            print("   - 하이브리드 전략이 제대로 작동할 것으로 예상됩니다.")
            print("\n💡 다음 단계:")
            print("   - API 서버에서 실제 질의 테스트")
            print("   - 품질 점수 개선 효과 확인")
        elif quality_ratio > 50:
            print("\n⚠️ 상태: 보통")
            print("   - 절반 정도의 문서에 신규 필드가 채워져 있습니다.")
            print("   - 하이브리드 전략의 fallback 로직이 중요합니다.")
        else:
            print("\n❌ 상태: 주의")
            print("   - 신규 필드가 충분히 채워지지 않았습니다.")
            print("   - 수집기 업데이트가 필요할 수 있습니다.")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(analyze_field_coverage())
