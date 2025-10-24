"""OpenSearch 데이터 및 성능 확인"""

from opensearchpy import OpenSearch
from api.config import settings
import time

# OpenSearch 연결
client = OpenSearch(
    hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
    http_auth=(settings.opensearch_user, settings.opensearch_password),
    use_ssl=False,
    verify_certs=False
)

def check_indices():
    """인덱스 확인"""
    print("=" * 80)
    print("OpenSearch 인덱스 확인")
    print("=" * 80)
    print()

    indices = client.cat.indices(format="json")

    if indices:
        print(f"총 {len(indices)}개 인덱스:")
        print()
        for idx in indices:
            if not idx['index'].startswith('.'):  # 시스템 인덱스 제외
                print(f"- {idx['index']}")
                print(f"  문서 수: {idx.get('docs.count', 'N/A')}")
                print(f"  크기: {idx.get('store.size', 'N/A')}")
                print(f"  상태: {idx.get('health', 'N/A')}")
                print()
    else:
        print("인덱스가 없습니다.")
        print()

def check_sample_data():
    """샘플 데이터 확인"""
    print("=" * 80)
    print("샘플 데이터 확인")
    print("=" * 80)
    print()

    # 주요 인덱스 확인
    test_indices = ["news", "articles", "contracts", "stock-news"]

    for index_name in test_indices:
        try:
            result = client.search(
                index=index_name,
                body={"query": {"match_all": {}}, "size": 1}
            )
            count = result['hits']['total']['value']
            print(f"✓ {index_name}: {count:,}건")

            if count > 0 and result['hits']['hits']:
                sample = result['hits']['hits'][0]['_source']
                print(f"  샘플 필드: {list(sample.keys())[:10]}")
        except Exception as e:
            print(f"✗ {index_name}: 없음 또는 오류")

    print()

def test_search_performance():
    """검색 성능 테스트"""
    print("=" * 80)
    print("검색 성능 테스트")
    print("=" * 80)
    print()

    test_queries = [
        ("단순 키워드", {"query": {"match": {"title": "삼성전자"}}, "size": 10}),
        ("복잡한 쿼리", {"query": {"bool": {"must": [{"match": {"title": "삼성"}}, {"match": {"content": "반도체"}}]}}, "size": 10}),
        ("날짜 범위", {"query": {"range": {"published_at": {"gte": "now-30d"}}}, "size": 10}),
    ]

    # 뉴스 인덱스로 테스트
    index_name = "news"

    for name, query_body in test_queries:
        start = time.time()
        try:
            result = client.search(index=index_name, body=query_body)
            elapsed = (time.time() - start) * 1000
            hits = result['hits']['total']['value']
            print(f"✓ {name}: {elapsed:.1f}ms ({hits}건)")
        except Exception as e:
            print(f"✗ {name}: 실패 - {str(e)[:50]}")

    print()

def suggest_optimizations():
    """최적화 제안"""
    print("=" * 80)
    print("OpenSearch 최적화 제안")
    print("=" * 80)
    print()

    print("1. 인덱스 매핑 최적화:")
    print("   - 자주 검색하는 필드에 keyword 타입 사용")
    print("   - 불필요한 필드는 _source에서 제외")
    print()

    print("2. 쿼리 최적화:")
    print("   - size 파라미터로 결과 제한 (기본 10, 최대 100)")
    print("   - _source 필터로 필요한 필드만 반환")
    print("   - 예:")
    print('   {"query": {...}, "size": 10, "_source": ["title", "summary", "url"]}')
    print()

    print("3. 벡터 검색 최적화:")
    print("   - k-NN 쿼리 사용 시 ef_search 파라미터 조정")
    print("   - 벡터 차원 축소 고려 (768 → 384 차원)")
    print()

if __name__ == "__main__":
    try:
        check_indices()
        check_sample_data()
        test_search_performance()
        suggest_optimizations()
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
