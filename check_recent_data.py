#!/usr/bin/env python3
"""
최근 데이터 처리 상태 확인
- 신규 필드가 최근 데이터에 채워지고 있는지
- 시간대별 처리 상태
"""

import asyncio
from opensearchpy import AsyncOpenSearch
from datetime import datetime, timedelta
from collections import defaultdict


async def check_recent_data():
    """최근 데이터의 신규 필드 채워짐 상태 확인"""

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
        print("📅 최근 데이터 처리 상태 확인")
        print("=" * 100)

        # 1. 전체 문서 중 최신/최고 ID 확인
        print("\n1️⃣ 데이터 ID 범위 확인")
        print("-" * 100)

        # ID로 정렬해서 최신 10개
        latest_query = {
            "query": {"match_all": {}},
            "sort": [{"_id": {"order": "desc"}}],
            "size": 10
        }

        latest_result = await client.search(index=index_name, body=latest_query)
        latest_hits = latest_result.get("hits", {}).get("hits", [])

        if latest_hits:
            latest_id = latest_hits[0]["_id"]
            oldest_in_latest = latest_hits[-1]["_id"]
            print(f"✅ 최신 문서 ID: {latest_id}")
            print(f"✅ 최근 10개 중 가장 오래된 ID: {oldest_in_latest}")
        else:
            print("❌ 문서가 없습니다.")
            return

        # 2. 최신 100개 문서의 필드 채워짐 상태
        print("\n\n2️⃣ 최신 100개 문서 필드 채워짐 상태")
        print("-" * 100)

        recent_100_query = {
            "query": {"match_all": {}},
            "sort": [{"_id": {"order": "desc"}}],
            "size": 100
        }

        recent_result = await client.search(index=index_name, body=recent_100_query)
        recent_hits = recent_result.get("hits", {}).get("hits", [])

        fields = ["quality_score", "is_featured", "neo4j_synced", "neo4j_node_count", "ontology_status"]
        field_stats = {field: {"exists": 0, "null": 0} for field in fields}

        for hit in recent_hits:
            src = hit["_source"]
            for field in fields:
                if src.get(field) is not None:
                    field_stats[field]["exists"] += 1
                else:
                    field_stats[field]["null"] += 1

        print(f"{'필드명':25s} | {'존재':>6s} | {'NULL':>6s} | {'채워짐율':>10s}")
        print("-" * 100)

        for field, stats in field_stats.items():
            total = stats["exists"] + stats["null"]
            fill_rate = (stats["exists"] / total * 100) if total > 0 else 0
            status = "✅" if fill_rate > 50 else "⚠️" if fill_rate > 0 else "❌"
            print(f"{field:25s} | {stats['exists']:6d} | {stats['null']:6d} | {status} {fill_rate:6.1f}%")

        # 3. ID 범위별 채워짐 상태 (10만개씩 샘플링)
        print("\n\n3️⃣ ID 범위별 필드 채워짐 상태 (샘플링)")
        print("-" * 100)

        # 총 문서 수
        count_result = await client.count(index=index_name, body={"query": {"match_all": {}}})
        total_docs = count_result.get("count", 0)

        print(f"총 문서 수: {total_docs:,}개\n")

        # ID 범위별 샘플링 (최근 -> 과거 순서)
        ranges = [
            (500000, 600000, "최신"),
            (400000, 500000, "최근"),
            (300000, 400000, "중간"),
            (200000, 300000, "과거"),
            (100000, 200000, "오래됨"),
            (0, 100000, "매우 오래됨"),
        ]

        print(f"{'ID 범위':20s} | {'구분':10s} | {'문서수':>8s} | {'quality_score':>15s} | {'ontology_status':>18s}")
        print("-" * 100)

        for start, end, label in ranges:
            # 해당 범위의 문서 수
            range_count_query = {
                "query": {
                    "range": {
                        "_id": {
                            "gte": str(start),
                            "lt": str(end)
                        }
                    }
                }
            }

            try:
                range_count = await client.count(index=index_name, body=range_count_query)
                doc_count = range_count.get("count", 0)

                if doc_count == 0:
                    continue

                # quality_score 존재 여부
                quality_count_query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"range": {"_id": {"gte": str(start), "lt": str(end)}}},
                                {"exists": {"field": "quality_score"}}
                            ]
                        }
                    }
                }

                quality_count = await client.count(index=index_name, body=quality_count_query)
                quality_exists = quality_count.get("count", 0)
                quality_ratio = (quality_exists / doc_count * 100) if doc_count > 0 else 0

                # ontology_status 존재 여부
                ontology_count_query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"range": {"_id": {"gte": str(start), "lt": str(end)}}},
                                {"exists": {"field": "ontology_status"}}
                            ]
                        }
                    }
                }

                ontology_count = await client.count(index=index_name, body=ontology_count_query)
                ontology_exists = ontology_count.get("count", 0)
                ontology_ratio = (ontology_exists / doc_count * 100) if doc_count > 0 else 0

                status_quality = "✅" if quality_ratio > 50 else "⚠️" if quality_ratio > 0 else "❌"
                status_ontology = "✅" if ontology_ratio > 50 else "⚠️" if ontology_ratio > 0 else "❌"

                print(f"{start:,} ~ {end:,} | {label:10s} | {doc_count:8,}개 | {status_quality} {quality_ratio:6.1f}% | {status_ontology} {ontology_ratio:6.1f}%")

            except Exception as e:
                print(f"{start:,} ~ {end:,} | {label:10s} | ERROR: {e}")

        # 4. quality_score가 있는 문서 중 최신/최고 확인
        print("\n\n4️⃣ quality_score 존재하는 문서 중 최신/최고")
        print("-" * 100)

        quality_latest_query = {
            "query": {
                "exists": {"field": "quality_score"}
            },
            "sort": [{"_id": {"order": "desc"}}],
            "size": 5
        }

        quality_latest = await client.search(index=index_name, body=quality_latest_query)
        quality_hits = quality_latest.get("hits", {}).get("hits", [])

        if quality_hits:
            print("✅ quality_score 존재하는 최신 5개 문서:")
            for i, hit in enumerate(quality_hits, 1):
                src = hit["_source"]
                doc_id = hit["_id"]
                title = src.get("title", "N/A")[:50]
                quality = src.get("quality_score")
                status = src.get("ontology_status")

                print(f"\n  #{i} ID: {doc_id}")
                print(f"      제목: {title}")
                print(f"      quality_score: {quality}")
                print(f"      ontology_status: {status}")
        else:
            print("❌ quality_score가 존재하는 문서가 없습니다.")

        # 5. 오늘 업데이트된 문서 확인 (updated_at 필드가 있다면)
        print("\n\n5️⃣ 최근 수정된 문서 확인")
        print("-" * 100)

        # updated_at 필드가 있는지 확인
        mapping = await client.indices.get_mapping(index=index_name)
        properties = mapping[index_name]["mappings"]["properties"]

        update_field = None
        for field in ["updated_at", "modified_at", "last_modified", "timestamp"]:
            if field in properties:
                update_field = field
                break

        if update_field:
            print(f"✅ 수정 시간 필드 발견: {update_field}")

            # 최근 수정된 문서 조회
            recent_update_query = {
                "query": {"exists": {"field": update_field}},
                "sort": [{update_field: {"order": "desc"}}],
                "size": 5
            }

            recent_updated = await client.search(index=index_name, body=recent_update_query)
            update_hits = recent_updated.get("hits", {}).get("hits", [])

            if update_hits:
                print(f"\n최근 수정된 5개 문서:")
                for i, hit in enumerate(update_hits, 1):
                    src = hit["_source"]
                    doc_id = hit["_id"]
                    title = src.get("title", "N/A")[:50]
                    updated = src.get(update_field)
                    quality = src.get("quality_score")

                    print(f"\n  #{i} ID: {doc_id}")
                    print(f"      제목: {title}")
                    print(f"      수정일: {updated}")
                    print(f"      quality_score: {quality}")
        else:
            print("⚠️ 수정 시간 필드가 없습니다.")

        # 6. 결론
        print("\n\n" + "=" * 100)
        print("📊 결론")
        print("=" * 100)

        # 최신 100개 평균 채워짐율
        avg_fill_rate = sum(s["exists"] for s in field_stats.values()) / (len(fields) * len(recent_hits)) * 100

        print(f"\n최신 100개 문서:")
        print(f"  - 평균 필드 채워짐율: {avg_fill_rate:.1f}%")

        if avg_fill_rate > 80:
            print("\n✅ 상태: 양호")
            print("   - 최근 데이터는 신규 필드가 잘 채워지고 있습니다.")
            print("   - 수집기가 정상 작동 중입니다.")
        elif avg_fill_rate > 50:
            print("\n⚠️ 상태: 보통")
            print("   - 최근 데이터 일부만 신규 필드가 채워지고 있습니다.")
            print("   - 수집기 업데이트가 부분적으로 작동 중일 수 있습니다.")
        elif avg_fill_rate > 0:
            print("\n⚠️ 상태: 주의")
            print("   - 최근 데이터도 신규 필드가 거의 채워지지 않고 있습니다.")
            print("   - 수집기가 업데이트되지 않았거나 오류가 있을 수 있습니다.")
        else:
            print("\n❌ 상태: 불량")
            print("   - 최근 데이터도 신규 필드가 전혀 채워지지 않고 있습니다.")
            print("   - 수집기 업데이트가 필요합니다.")

        print("\n💡 권장 사항:")
        if avg_fill_rate < 50:
            print("   1. 수집기 코드 확인 (신규 필드 채우는 로직 있는지)")
            print("   2. 수집기 재시작 필요 여부 확인")
            print("   3. OpenSearch 인덱스 매핑과 수집기 코드 일치 여부 확인")
        else:
            print("   1. 기존 데이터 재처리 (backfill) 고려")
            print("   2. 하이브리드 전략으로 당분간 운영 가능")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(check_recent_data())
