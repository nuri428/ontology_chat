"""실제 Neo4j 인덱스 및 데이터 확인 (192.168.0.10:7687/news-def-topology)"""

from neo4j import GraphDatabase
from api.config import settings

# 실제 사용 중인 Neo4j 연결
NEO4J_URI = "neo4j://192.168.0.10:7687"
NEO4J_DATABASE = "news-def-topology"

print("=" * 80)
print("실제 Neo4j 연결 정보")
print("=" * 80)
print(f"URI: {NEO4J_URI}")
print(f"Database: {NEO4J_DATABASE}")
print(f"User: {settings.neo4j_user}")
print()

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(settings.neo4j_user, settings.neo4j_password)
)

def check_database_info():
    """데이터베이스 기본 정보"""
    print("=" * 80)
    print("데이터베이스 기본 정보")
    print("=" * 80)
    print()

    with driver.session(database=NEO4J_DATABASE) as session:
        # 노드 수
        result = session.run("MATCH (n) RETURN count(n) as count")
        node_count = result.single()["count"]

        # 관계 수
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result.single()["count"]

        # 레이블 수
        result = session.run("CALL db.labels()")
        labels = [record["label"] for record in result]

        print(f"📊 총 노드: {node_count:,}개")
        print(f"📊 총 관계: {rel_count:,}개")
        print(f"📊 총 레이블: {len(labels)}개")
        print()

        if node_count > 0:
            print("✅ 데이터가 존재합니다!")
        else:
            print("⚠️ 데이터가 없습니다.")

        print()
        return labels

def check_labels_detail(labels):
    """레이블별 상세 정보"""
    print("=" * 80)
    print("레이블별 노드 수")
    print("=" * 80)
    print()

    with driver.session(database=NEO4J_DATABASE) as session:
        for label in labels[:20]:  # 처음 20개만
            result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
            count = result.single()["count"]
            print(f"  {label}: {count:,}개")

        if len(labels) > 20:
            print(f"  ... 외 {len(labels) - 20}개 레이블")

    print()

def check_indexes():
    """인덱스 확인"""
    print("=" * 80)
    print("인덱스 목록")
    print("=" * 80)
    print()

    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run("SHOW INDEXES")
        indexes = list(result)

        if indexes:
            print(f"총 {len(indexes)}개 인덱스:")
            print()

            # 인덱스 타입별로 그룹화
            lookup_indexes = [idx for idx in indexes if idx['type'] == 'LOOKUP']
            other_indexes = [idx for idx in indexes if idx['type'] != 'LOOKUP']

            if lookup_indexes:
                print(f"LOOKUP 인덱스 ({len(lookup_indexes)}개):")
                for idx in lookup_indexes:
                    print(f"  - {idx['name']}")

            if other_indexes:
                print()
                print(f"기타 인덱스 ({len(other_indexes)}개):")
                for idx in other_indexes:
                    print(f"  - {idx['name']}")
                    print(f"    타입: {idx['type']}")
                    print(f"    레이블: {idx.get('labelsOrTypes', 'N/A')}")
                    print(f"    속성: {idx.get('properties', 'N/A')}")
                    print()
        else:
            print("인덱스가 없습니다.")

    print()

def test_sample_queries():
    """샘플 쿼리 성능 테스트"""
    print("=" * 80)
    print("샘플 쿼리 성능 테스트")
    print("=" * 80)
    print()

    import time

    test_queries = [
        ("전체 노드 샘플", "MATCH (n) RETURN n LIMIT 5"),
        ("전체 관계 샘플", "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 5"),
    ]

    with driver.session(database=NEO4J_DATABASE) as session:
        for name, query in test_queries:
            start = time.time()
            try:
                result = session.run(query)
                records = list(result)
                elapsed = (time.time() - start) * 1000

                print(f"✓ {name}: {elapsed:.1f}ms ({len(records)}건)")

                # 첫 번째 레코드의 노드 정보 출력
                if records:
                    first_record = records[0]
                    if 'n' in first_record:
                        node = first_record['n']
                        print(f"  샘플 노드 레이블: {list(node.labels)}")
                        print(f"  샘플 노드 속성: {list(node.keys())[:5]}")

            except Exception as e:
                print(f"✗ {name}: 실패 - {e}")

        print()

def suggest_useful_indexes(labels):
    """유용한 인덱스 제안"""
    print("=" * 80)
    print("권장 인덱스 (주요 레이블 기준)")
    print("=" * 80)
    print()

    # 주요 레이블 확인
    important_labels = []
    with driver.session(database=NEO4J_DATABASE) as session:
        for label in labels[:10]:
            result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
            count = result.single()["count"]
            if count > 100:  # 100개 이상인 레이블만
                important_labels.append((label, count))

    if important_labels:
        print("노드가 많은 레이블 (100개 이상):")
        for label, count in important_labels:
            print(f"\n{label} ({count:,}개):")

            # 샘플 노드에서 자주 사용될 만한 속성 확인
            with driver.session(database=NEO4J_DATABASE) as session:
                result = session.run(f"MATCH (n:{label}) RETURN properties(n) as props LIMIT 1")
                record = result.single()
                if record:
                    props = record["props"]

                    # 검색에 유용한 속성 우선순위
                    useful_props = []
                    for key in props.keys():
                        if any(keyword in key.lower() for keyword in ['name', 'title', 'id', 'date', 'time', 'code', 'symbol']):
                            useful_props.append(key)

                    if useful_props:
                        print(f"  권장 인덱스 속성: {useful_props}")
                        for prop in useful_props[:3]:  # 상위 3개만
                            print(f"  CREATE INDEX {label.lower()}_{prop.lower()} IF NOT EXISTS FOR (n:{label}) ON (n.{prop});")

    print()

if __name__ == "__main__":
    try:
        labels = check_database_info()

        if labels:
            check_labels_detail(labels)
            check_indexes()
            test_sample_queries()
            suggest_useful_indexes(labels)
        else:
            print("⚠️ 데이터베이스가 비어있습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()
