#!/usr/bin/env python3
"""
개선된 LangGraph 기반 리포트 API 테스트
"""

import requests
import json
import time

def test_langgraph_report():
    """LangGraph 리포트 API 테스트"""
    print("🚀 LangGraph 리포트 API 테스트")
    print("="*50)

    base_url = "http://localhost:8000"

    # 테스트 요청
    test_data = {
        "query": "한화 방산 계약",
        "domain": "방산 무기체계",
        "lookback_days": 90,
        "analysis_depth": "standard"
    }

    print(f"📋 테스트 쿼리: {test_data['query']}")
    print(f"   분석 깊이: {test_data['analysis_depth']}")

    try:
        start_time = time.time()

        # LangGraph 리포트 API 호출
        response = requests.post(
            f"{base_url}/report/langgraph",
            json=test_data,
            timeout=120
        )

        request_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            print(f"✅ 응답 성공 ({response.status_code})")
            print(f"   요청 시간: {request_time:.2f}초")

            # 기본 정보
            print(f"   품질 점수: {result.get('quality_score', 0):.2f}")
            print(f"   품질 레벨: {result.get('quality_level', 'N/A')}")
            print(f"   처리 시간: {result.get('processing_time', 0):.2f}초")

            # 컨텍스트 정보
            print(f"   수집된 컨텍스트: {result.get('contexts_count', 0)}개")
            print(f"   생성된 인사이트: {result.get('insights_count', 0)}개")
            print(f"   분석된 관계: {result.get('relationships_count', 0)}개")

            # 메타 정보
            meta = result.get("meta", {})
            print(f"   신뢰도: {meta.get('confidence', 0):.1f}%")
            print(f"   완성도: {meta.get('coverage', 0):.1f}%")

            # 실행 로그 (처음 3개)
            execution_log = result.get("execution_log", [])
            if execution_log:
                print(f"   실행 로그 (첫 3개):")
                for i, log in enumerate(execution_log[:3], 1):
                    print(f"      {i}. {log}")

            # 리포트 길이
            markdown = result.get("markdown", "")
            print(f"   리포트 길이: {len(markdown)} 글자")

            # 하이브리드 검색 확인
            if "하이브리드" in str(execution_log):
                print("   🔍 하이브리드 검색이 활성화되었습니다!")
            elif "BGE-M3" in str(execution_log):
                print("   🔍 BGE-M3 임베딩이 사용되었습니다!")

            # 오류가 있으면 표시
            if "error" in result:
                print(f"   ⚠️ 오류: {result['error']}")

        else:
            print(f"❌ 응답 실패 ({response.status_code})")
            print(f"   오류: {response.text}")

    except requests.RequestException as e:
        print(f"❌ 요청 오류: {e}")
    except Exception as e:
        print(f"❌ 기타 오류: {e}")

def test_langgraph_comparative():
    """LangGraph 비교 분석 API 테스트"""
    print(f"\n🔄 LangGraph 비교 분석 API 테스트")
    print("="*50)

    base_url = "http://localhost:8000"

    # 비교 분석 요청
    test_data = {
        "queries": ["한화 방산", "KAI 항공우주"],
        "domain": "방산",
        "lookback_days": 60,
        "analysis_depth": "standard"
    }

    print(f"📋 비교 대상: {', '.join(test_data['queries'])}")

    try:
        start_time = time.time()

        response = requests.post(
            f"{base_url}/report/langgraph/comparative",
            json=test_data,
            timeout=180
        )

        request_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            print(f"✅ 비교 분석 성공 ({response.status_code})")
            print(f"   요청 시간: {request_time:.2f}초")

            # 개별 결과 정보
            individual_results = result.get("individual_results", [])
            print(f"   개별 분석 결과: {len(individual_results)}개")

            for i, item in enumerate(individual_results, 1):
                query = item.get("query", "N/A")
                quality = item.get("result", {}).get("quality_score", 0)
                print(f"      {i}. {query}: 품질 {quality:.2f}")

            # 메타 정보
            meta = result.get("meta", {})
            print(f"   총 처리 시간: {meta.get('total_processing_time', 0):.2f}초")

            # 리포트 길이
            markdown = result.get("markdown", "")
            print(f"   비교 리포트 길이: {len(markdown)} 글자")

        else:
            print(f"❌ 비교 분석 실패 ({response.status_code})")
            print(f"   오류: {response.text}")

    except requests.RequestException as e:
        print(f"❌ 요청 오류: {e}")
    except Exception as e:
        print(f"❌ 기타 오류: {e}")

if __name__ == "__main__":
    # 서버 연결 확인
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ 서버 연결 확인됨")

            # 기본 LangGraph 리포트 테스트
            test_langgraph_report()

            # 비교 분석 테스트
            test_langgraph_comparative()

            print(f"\n🏁 LangGraph API 테스트 완료")
        else:
            print(f"❌ 서버 응답 오류: {response.status_code}")
    except requests.RequestException:
        print("❌ 서버가 실행되지 않았거나 연결할 수 없습니다.")
        print("   서버를 먼저 실행해주세요: python -m uvicorn api.main:app --reload")