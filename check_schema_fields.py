#!/usr/bin/env python3
"""
신규 스키마 필드 DB 저장 확인 스크립트
- quality_score
- is_featured
- neo4j_synced
- neo4j_node_count
- ontology_status
- event_chain_id
"""

import asyncio
from opensearchpy import AsyncOpenSearch
from datetime import datetime, timedelta
import json


async def check_opensearch_schema():
    """OpenSearch에 신규 필드가 채워지고 있는지 확인"""

    # OpenSearch 연결
    client = AsyncOpenSearch(
        hosts=["http://localhost:9200"],
        http_auth=("admin", "admin"),
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False
    )

    try:
        index_name = "news_article_bulk"

        print("=" * 80)
        print("📊 OpenSearch 신규 스키마 필드 확인")
        print("=" * 80)

        # 1. 인덱스 매핑 확인
        print("\n1️⃣ 인덱스 매핑 (신규 필드 정의 여부)")
        print("-" * 80)

        mapping = await client.indices.get_mapping(index=index_name)
        properties = mapping[index_name]["mappings"]["properties"]

        new_fields = [
            "quality_score",
            "is_featured",
            "neo4j_synced",
            "neo4j_node_count",
            "ontology_status",
            "event_chain_id"
        ]

        for field in new_fields:
            if field in properties:
                field_type = properties[field].get("type", "unknown")
                print(f"✅ {field:25s} : {field_type}")
            else:
                print(f"❌ {field:25s} : NOT DEFINED")

        # 2. 최근 문서 샘플 확인 (최신 10개)
        print("\n\n2️⃣ 최신 문서 샘플 (10개)")
        print("-" * 80)

        query = {
            "query": {"match_all": {}},
            "sort": [{"_id": {"order": "desc"}}],
            "size": 10
        }

        result = await client.search(index=index_name, body=query)
        hits = result.get("hits", {}).get("hits", [])

        print(f"검색된 문서 수: {len(hits)}개\n")

        if not hits:
            print("⚠️ 데이터가 없습니다.")
        else:
            # 필드별 통계
            field_stats = {field: {"exists": 0, "null": 0, "values": []} for field in new_fields}

            for i, hit in enumerate(hits, 1):
                source = hit["_source"]
                doc_id = hit["_id"]
                title = source.get("title", "N/A")[:50]

                print(f"\n[문서 #{i}] (ID: {doc_id[:20]}...)")
                print(f"  제목: {title}")

                for field in new_fields:
                    value = source.get(field)

                    if value is not None:
                        field_stats[field]["exists"] += 1
                        field_stats[field]["values"].append(value)
                        print(f"  ✅ {field}: {value}")
                    else:
                        field_stats[field]["null"] += 1
                        print(f"  ❌ {field}: NULL")

            # 3. 통계 요약
            print("\n\n3️⃣ 필드별 통계 요약")
            print("-" * 80)
            print(f"{'필드명':25s} | {'존재':>6s} | {'NULL':>6s} | {'채워짐율':>8s} | 샘플 값")
            print("-" * 80)

            for field, stats in field_stats.items():
                total = stats["exists"] + stats["null"]
                fill_rate = (stats["exists"] / total * 100) if total > 0 else 0

                # 샘플 값 (중복 제거)
                unique_values = list(set(stats["values"]))[:3]
                sample = ", ".join(str(v) for v in unique_values) if unique_values else "-"

                print(f"{field:25s} | {stats['exists']:6d} | {stats['null']:6d} | {fill_rate:7.1f}% | {sample}")

        # 4. 전체 통계 (aggregation)
        print("\n\n4️⃣ 전체 통계 (전체 데이터)")
        print("-" * 80)

        agg_query = {
            "query": {"match_all": {}},
            "size": 0,
            "aggs": {
                "total_docs": {"value_count": {"field": "_id"}},
                "quality_score_exists": {
                    "filter": {"exists": {"field": "quality_score"}},
                    "aggs": {
                        "avg_quality": {"avg": {"field": "quality_score"}},
                        "max_quality": {"max": {"field": "quality_score"}},
                        "min_quality": {"min": {"field": "quality_score"}}
                    }
                },
                "is_featured_true": {
                    "filter": {"term": {"is_featured": True}}
                },
                "neo4j_synced_true": {
                    "filter": {"term": {"neo4j_synced": True}}
                },
                "neo4j_node_count_exists": {
                    "filter": {"exists": {"field": "neo4j_node_count"}},
                    "aggs": {
                        "avg_nodes": {"avg": {"field": "neo4j_node_count"}},
                        "max_nodes": {"max": {"field": "neo4j_node_count"}}
                    }
                },
                "ontology_status_breakdown": {
                    "terms": {"field": "ontology_status.keyword", "size": 10}
                }
            }
        }

        try:
            agg_result = await client.search(index=index_name, body=agg_query)
            aggs = agg_result.get("aggregations", {})

            total = agg_result.get("hits", {}).get("total", {}).get("value", 0)
            quality_exists = aggs["quality_score_exists"]["doc_count"]
            featured_count = aggs["is_featured_true"]["doc_count"]
            synced_count = aggs["neo4j_synced_true"]["doc_count"]
            node_count_exists = aggs["neo4j_node_count_exists"]["doc_count"]

            print(f"총 문서 수: {total:,}개\n")

            print(f"quality_score:")
            print(f"  - 존재: {quality_exists:,}개 ({quality_exists/total*100:.1f}%)")
            if quality_exists > 0:
                quality_stats = aggs["quality_score_exists"]
                print(f"  - 평균: {quality_stats['avg_quality']['value']:.3f}")
                print(f"  - 최대: {quality_stats['max_quality']['value']:.3f}")
                print(f"  - 최소: {quality_stats['min_quality']['value']:.3f}")

            print(f"\nis_featured:")
            print(f"  - True: {featured_count:,}개 ({featured_count/total*100:.1f}%)")

            print(f"\nneo4j_synced:")
            print(f"  - True: {synced_count:,}개 ({synced_count/total*100:.1f}%)")

            print(f"\nneo4j_node_count:")
            print(f"  - 존재: {node_count_exists:,}개 ({node_count_exists/total*100:.1f}%)")
            if node_count_exists > 0:
                node_stats = aggs["neo4j_node_count_exists"]
                print(f"  - 평균: {node_stats['avg_nodes']['value']:.1f}개")
                print(f"  - 최대: {node_stats['max_nodes']['value']:.0f}개")

            print(f"\nontology_status:")
            status_buckets = aggs["ontology_status_breakdown"]["buckets"]
            if status_buckets:
                for bucket in status_buckets:
                    print(f"  - {bucket['key']}: {bucket['doc_count']:,}개")
            else:
                print(f"  - 데이터 없음")

        except Exception as e:
            print(f"⚠️ Aggregation 실패: {e}")

        # 5. 결론
        print("\n\n" + "=" * 80)
        print("📋 결론")
        print("=" * 80)

        if len(hits) > 0:
            avg_fill_rate = sum(s["exists"] for s in field_stats.values()) / (len(new_fields) * len(hits)) * 100

            print(f"\n✅ 최신 데이터 존재: {len(hits)}개")
            print(f"✅ 평균 필드 채워짐율: {avg_fill_rate:.1f}%")

            if avg_fill_rate > 80:
                print("\n🎉 상태: 양호 - 대부분의 신규 필드가 채워지고 있습니다!")
            elif avg_fill_rate > 50:
                print("\n⚠️ 상태: 보통 - 일부 필드가 채워지고 있습니다.")
            elif avg_fill_rate > 0:
                print("\n⚠️ 상태: 주의 - 필드가 일부만 채워지고 있습니다.")
            else:
                print("\n❌ 상태: 불량 - 신규 필드가 전혀 채워지지 않고 있습니다.")

                # 신규 필드가 정의는 되어있지만 채워지지 않는 경우
                defined_count = sum(1 for field in new_fields if field in properties)
                if defined_count >= 5:
                    print("\n💡 진단:")
                    print("   - 스키마는 정의되어 있음 (매핑 존재)")
                    print("   - 하지만 실제 데이터는 채워지지 않음")
                    print("   → 수집기 업데이트 필요 (필드 채우는 로직 추가)")
        else:
            print("\n⚠️ 데이터가 없어 판단할 수 없습니다.")
            print("   → 인덱스가 비어있거나 OpenSearch 연결 문제")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(check_opensearch_schema())
