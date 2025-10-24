"""Neo4j 인덱스 및 성능 확인"""

from neo4j import GraphDatabase
from api.config import settings

# Neo4j 연결
driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password)
)

def check_indexes():
    """인덱스 확인"""
    print("=" * 80)
    print("Neo4j 인덱스 확인")
    print("=" * 80)

    with driver.session() as session:
        # 인덱스 목록
        result = session.run("SHOW INDEXES")
        indexes = list(result)

        if indexes:
            print(f"\n총 {len(indexes)}개 인덱스:")
            print()
            for idx in indexes:
                print(f"- {idx['name']}")
                print(f"  타입: {idx['type']}")
                print(f"  레이블/타입: {idx.get('labelsOrTypes', 'N/A')}")
                print(f"  속성: {idx.get('properties', 'N/A')}")
                print(f"  상태: {idx.get('state', 'N/A')}")
                print()
        else:
            print("\n⚠️ 인덱스가 없습니다!")
            print()

def check_labels_and_properties():
    """레이블과 속성 확인"""
    print("=" * 80)
    print("노드 레이블 및 속성 확인")
    print("=" * 80)

    with driver.session() as session:
        # 레이블 목록
        result = session.run("CALL db.labels()")
        labels = [record["label"] for record in result]

        print(f"\n총 {len(labels)}개 레이블:")
        for label in labels[:20]:  # 처음 20개만
            print(f"  - {label}")

        if len(labels) > 20:
            print(f"  ... 외 {len(labels) - 20}개")

        print()

        # 각 레이블의 샘플 노드 속성
        print("\n주요 레이블의 속성:")
        important_labels = ["Company", "Article", "News", "Contract", "Person"]

        for label in important_labels:
            if label in labels:
                result = session.run(f"MATCH (n:{label}) RETURN properties(n) as props LIMIT 1")
                record = result.single()
                if record:
                    props = record["props"]
                    print(f"\n{label} 속성:")
                    for key in list(props.keys())[:10]:
                        print(f"    - {key}")

def suggest_indexes():
    """권장 인덱스 제안"""
    print()
    print("=" * 80)
    print("권장 인덱스")
    print("=" * 80)
    print()

    recommendations = [
        ("Company", "name", "회사 이름 검색 최적화"),
        ("Company", "symbol", "종목 코드 검색 최적화"),
        ("Article", "title", "기사 제목 검색 최적화"),
        ("Article", "published_at", "기사 날짜 필터링 최적화"),
        ("News", "published_at", "뉴스 날짜 필터링 최적화"),
        ("News", "title", "뉴스 제목 검색 최적화"),
    ]

    print("CREATE INDEX 명령어:")
    print()
    for label, prop, desc in recommendations:
        print(f"// {desc}")
        print(f"CREATE INDEX {label.lower()}_{prop.lower()} IF NOT EXISTS FOR (n:{label}) ON (n.{prop});")
        print()

def test_query_performance():
    """쿼리 성능 테스트"""
    print("=" * 80)
    print("쿼리 성능 테스트")
    print("=" * 80)
    print()

    test_queries = [
        ("회사 검색", "MATCH (c:Company {name: '삼성전자'}) RETURN c LIMIT 1"),
        ("최근 뉴스", "MATCH (n:News) WHERE n.published_at IS NOT NULL RETURN n ORDER BY n.published_at DESC LIMIT 10"),
        ("회사-뉴스 관계", "MATCH (c:Company)-[r]-(n:News) WHERE c.name CONTAINS '삼성' RETURN c, r, n LIMIT 5"),
    ]

    import time

    with driver.session() as session:
        for name, query in test_queries:
            start = time.time()
            try:
                result = session.run(query)
                records = list(result)
                elapsed = (time.time() - start) * 1000

                print(f"✓ {name}: {elapsed:.1f}ms ({len(records)}건)")
            except Exception as e:
                print(f"✗ {name}: 실패 - {e}")

    print()

if __name__ == "__main__":
    try:
        check_indexes()
        check_labels_and_properties()
        test_query_performance()
        suggest_indexes()
    finally:
        driver.close()
