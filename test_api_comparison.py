#!/usr/bin/env python3
"""
실제 API 호출하여 하이브리드 검색 차이점 확인
"""

import requests
import json
import sys

def test_report_api():
    """리포트 API 호출 테스트"""
    print("🚀 리포트 API 호출 테스트")
    print("="*50)

    base_url = "http://localhost:8000"

    # 테스트 요청 데이터
    test_requests = [
        {
            "name": "한화 방산 관련 검색",
            "data": {
                "query": "한화 방산 계약",
                "domain": "방산 무기체계",
                "lookback_days": 90,
                "news_size": 10,
                "graph_limit": 20
            }
        },
        {
            "name": "KAI 항공우주 검색",
            "data": {
                "query": "KAI 항공우주산업",
                "domain": "항공 우주",
                "lookback_days": 60,
                "news_size": 8,
                "graph_limit": 15
            }
        }
    ]

    for test in test_requests:
        print(f"\n📋 테스트: {test['name']}")
        print(f"   쿼리: {test['data']['query']}")

        try:
            # API 호출
            response = requests.post(
                f"{base_url}/report",
                json=test["data"],
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()

                # 기본 정보
                print(f"✅ 응답 성공 ({response.status_code})")
                print(f"   응답 크기: {len(response.content)} bytes")

                # 메타데이터 확인
                meta = result.get("meta", {})
                print(f"   하이브리드 검색: {meta.get('hybrid_search_enabled', 'N/A')}")
                print(f"   BGE-M3 서버: {meta.get('bge_m3_host', 'N/A')}")
                print(f"   뉴스 결과 수: {meta.get('news_size', 0)}")

                # 뉴스 소스 정보
                sources = result.get("sources", [])
                print(f"   수집된 소스: {len(sources)}개")
                if sources:
                    print("   상위 3개 뉴스:")
                    for i, source in enumerate(sources[:3], 1):
                        title = source.get("title", "제목 없음")[:60] + "..."
                        score = source.get("score", 0)
                        print(f"      {i}. (점수: {score:.4f}) {title}")

                # 리포트 품질 확인
                markdown = result.get("markdown", "")
                print(f"   리포트 길이: {len(markdown)} 글자")

                # 메트릭스 정보
                metrics = result.get("metrics", {})
                news_metrics = metrics.get("news", {})
                graph_metrics = metrics.get("graph", {})

                print(f"   뉴스 메트릭스: {news_metrics.get('count', 0)}건")
                print(f"   그래프 엔터티: {len(graph_metrics.get('label_distribution', []))}개 라벨")

            else:
                print(f"❌ 응답 실패 ({response.status_code})")
                print(f"   오류: {response.text}")

        except requests.RequestException as e:
            print(f"❌ 요청 오류: {e}")
        except Exception as e:
            print(f"❌ 기타 오류: {e}")

    print(f"\n🏁 API 테스트 완료")

def compare_indices():
    """news_article_bulk vs news_article_embedding 직접 비교"""
    print(f"\n🔍 인덱스 직접 비교")
    print("="*30)

    opensearch_url = "http://admin:Manhae428!@192.168.0.10:9200"
    test_query = "한화"

    indices = ["news_article_bulk", "news_article_embedding"]

    for index in indices:
        try:
            search_query = {
                "query": {
                    "multi_match": {
                        "query": test_query,
                        "fields": ["title^2", "text", "content"],
                        "type": "best_fields"
                    }
                },
                "size": 3,
                "_source": ["title", "text", "metadata.title"]
            }

            response = requests.post(
                f"{opensearch_url}/{index}/_search",
                json=search_query,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                hits = result.get("hits", {}).get("hits", [])
                total = result.get("hits", {}).get("total", {})
                total_value = total.get("value", 0) if isinstance(total, dict) else total

                print(f"📊 {index}:")
                print(f"   총 결과: {total_value}건")
                print(f"   상위 3개:")

                for i, hit in enumerate(hits, 1):
                    source = hit.get("_source", {})
                    score = hit.get("_score", 0)

                    # 제목 추출 (여러 필드에서)
                    title = (
                        source.get("title") or
                        source.get("text", "")[:50] or
                        source.get("metadata", {}).get("title") or
                        "제목 없음"
                    )

                    print(f"      {i}. (점수: {score:.4f}) {title[:50]}...")
            else:
                print(f"❌ {index} 검색 실패: {response.status_code}")

        except Exception as e:
            print(f"❌ {index} 검색 오류: {e}")

if __name__ == "__main__":
    # 서버가 실행 중인지 확인
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ 서버 연결 확인됨")
            test_report_api()
            compare_indices()
        else:
            print(f"❌ 서버 응답 오류: {response.status_code}")
    except requests.RequestException:
        print("❌ 서버가 실행되지 않았거나 연결할 수 없습니다.")
        print("   서버를 먼저 실행해주세요: python -m uvicorn api.main:app --reload")
        sys.exit(1)