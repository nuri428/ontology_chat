#!/usr/bin/env python3
"""
숫자 ID 기반 최근 데이터 확인
"""

import asyncio
from opensearchpy import AsyncOpenSearch


async def check_numeric_id_data():
    """숫자 ID로 최근 데이터 확인"""

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
        print("🔍 숫자 ID 기반 최근 데이터 확인")
        print("=" * 100)

        # 1. 숫자 ID로 된 최신 문서 확인
        print("\n1️⃣ 숫자 ID 문서 확인")
        print("-" * 100)

        # quality_score 있는 문서 중 ID가 숫자인 것만 (최신순)
        query_numeric = {
            "query": {
                "bool": {
                    "must": [
                        {"exists": {"field": "quality_score"}},
                        {"regexp": {"_id": "[0-9]+"}}  # 숫자 ID만
                    ]
                }
            },
            "sort": [{"_id": {"order": "desc"}}],
            "size": 10
        }

        try:
            result = await client.search(index=index_name, body=query_numeric)
            hits = result.get("hits", {}).get("hits", [])

            print(f"✅ 숫자 ID + quality_score 있는 문서: {len(hits)}개\n")

            if hits:
                for i, hit in enumerate(hits, 1):
                    src = hit["_source"]
                    doc_id = hit["_id"]
                    title = src.get("title", "N/A")[:60]
                    quality = src.get("quality_score")
                    featured = src.get("is_featured")
                    synced = src.get("neo4j_synced")
                    node_count = src.get("neo4j_node_count")
                    status = src.get("ontology_status")

                    print(f"문서 #{i} (ID: {doc_id})")
                    print(f"  제목: {title}")
                    print(f"  quality_score: {quality}")
                    print(f"  is_featured: {featured}")
                    print(f"  neo4j_synced: {synced}")
                    print(f"  neo4j_node_count: {node_count}")
                    print(f"  ontology_status: {status}")
                    print()
        except Exception as e:
            print(f"❌ 에러: {e}")

        # 2. ID 필드 정보 확인
        print("\n2️⃣ 문서 ID 타입별 분포")
        print("-" * 100)

        # 샘플 문서 가져오기
        sample_query = {
            "query": {"match_all": {}},
            "size": 100
        }

        sample_result = await client.search(index=index_name, body=sample_query)
        sample_hits = sample_result.get("hits", {}).get("hits", [])

        numeric_ids = []
        string_ids = []

        for hit in sample_hits:
            doc_id = hit["_id"]
            if doc_id.isdigit():
                numeric_ids.append(doc_id)
            else:
                string_ids.append(doc_id)

        print(f"샘플 100개 중:")
        print(f"  - 숫자 ID: {len(numeric_ids)}개")
        print(f"  - 문자열 ID: {len(string_ids)}개")

        if numeric_ids:
            print(f"\n숫자 ID 샘플: {', '.join(numeric_ids[:5])}")
        if string_ids:
            print(f"문자열 ID 샘플: {', '.join(string_ids[:5])}")

        # 3. 숫자 ID 범위별 필드 채워짐 확인
        print("\n\n3️⃣ 숫자 ID 문서의 필드 채워짐 상태")
        print("-" * 100)

        # 숫자 ID인 문서만 필터링
        fields = ["quality_score", "is_featured", "neo4j_synced", "neo4j_node_count", "ontology_status"]

        # 숫자 ID 문서 샘플 (큰 ID부터)
        numeric_docs_query = {
            "query": {
                "regexp": {"_id": "[0-9]+"}
            },
            "sort": [{"_id": {"order": "desc"}}],
            "size": 100
        }

        try:
            numeric_result = await client.search(index=index_name, body=numeric_docs_query)
            numeric_hits = numeric_result.get("hits", {}).get("hits", [])

            field_stats = {field: {"exists": 0, "null": 0} for field in fields}

            for hit in numeric_hits:
                src = hit["_source"]
                for field in fields:
                    if src.get(field) is not None:
                        field_stats[field]["exists"] += 1
                    else:
                        field_stats[field]["null"] += 1

            print(f"숫자 ID 문서 최근 100개 분석:\n")
            print(f"{'필드명':25s} | {'존재':>6s} | {'NULL':>6s} | {'채워짐율':>10s}")
            print("-" * 100)

            for field, stats in field_stats.items():
                total = stats["exists"] + stats["null"]
                fill_rate = (stats["exists"] / total * 100) if total > 0 else 0
                status = "✅" if fill_rate > 50 else "⚠️" if fill_rate > 0 else "❌"
                print(f"{field:25s} | {stats['exists']:6d} | {stats['null']:6d} | {status} {fill_rate:6.1f}%")

            # 평균 채워짐율
            avg_fill_rate = sum(s["exists"] for s in field_stats.values()) / (len(fields) * len(numeric_hits)) * 100 if numeric_hits else 0

            print(f"\n평균 채워짐율: {avg_fill_rate:.1f}%")

        except Exception as e:
            print(f"❌ 에러: {e}")

        # 4. 가장 큰 숫자 ID 확인
        print("\n\n4️⃣ 숫자 ID 최대값 확인")
        print("-" * 100)

        # 모든 숫자 ID 문서를 가져와서 최대값 찾기
        all_numeric_query = {
            "query": {"regexp": {"_id": "[0-9]+"}},
            "size": 10000,
            "_source": False
        }

        try:
            all_numeric = await client.search(index=index_name, body=all_numeric_query)
            all_numeric_hits = all_numeric.get("hits", {}).get("hits", [])

            numeric_id_values = [int(hit["_id"]) for hit in all_numeric_hits if hit["_id"].isdigit()]

            if numeric_id_values:
                max_id = max(numeric_id_values)
                min_id = min(numeric_id_values)

                print(f"✅ 숫자 ID 범위:")
                print(f"  - 최소: {min_id:,}")
                print(f"  - 최대: {max_id:,}")
                print(f"  - 개수: {len(numeric_id_values):,}개")

                # 최대 ID 근처 문서 확인
                print(f"\n최대 ID ({max_id}) 근처 문서 10개:")

                nearby_query = {
                    "query": {"ids": {"values": [str(i) for i in range(max_id - 10, max_id + 1)]}},
                    "size": 10
                }

                nearby_result = await client.search(index=index_name, body=nearby_query)
                nearby_hits = nearby_result.get("hits", {}).get("hits", [])

                for hit in nearby_hits:
                    src = hit["_source"]
                    doc_id = hit["_id"]
                    title = src.get("title", "N/A")[:50]
                    quality = src.get("quality_score")
                    status = src.get("ontology_status")

                    print(f"\n  ID {doc_id}:")
                    print(f"    제목: {title}")
                    print(f"    quality_score: {quality}")
                    print(f"    ontology_status: {status}")

        except Exception as e:
            print(f"⚠️ 검색 제한으로 일부만 조회됨: {e}")

        # 5. 결론
        print("\n\n" + "=" * 100)
        print("📊 결론")
        print("=" * 100)

        print(f"\n문서 ID 타입:")
        print(f"  - 숫자 ID: {len(numeric_ids)}개 (샘플 100개 중)")
        print(f"  - 문자열 ID: {len(string_ids)}개 (샘플 100개 중)")

        if len(numeric_ids) > len(string_ids):
            print("\n✅ 대부분의 문서가 숫자 ID를 사용합니다.")
            print("   - 숫자 ID 문서는 이전 시스템에서 생성된 것으로 보입니다.")
            print("   - 이 문서들에는 신규 필드가 채워져 있습니다.")
        else:
            print("\n⚠️ 최근 문서는 문자열 ID를 사용합니다.")
            print("   - 문자열 ID 문서는 최근 수집기에서 생성된 것입니다.")
            print("   - 이 문서들에는 신규 필드가 채워지지 않았습니다.")

        print("\n💡 핵심 발견:")
        print("   1. 숫자 ID 문서 (예: 540699) → 신규 필드 존재 ✅")
        print("   2. 문자열 ID 문서 (예: ztPFqpkBZ86nX0ItKpZm) → 신규 필드 없음 ❌")
        print("   3. 최신 수집기가 문자열 ID를 생성하고 있으며, 신규 필드를 채우지 않음")
        print("\n→ 수집기 업데이트 필요!")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(check_numeric_id_data())
