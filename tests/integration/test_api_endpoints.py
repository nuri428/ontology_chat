#!/usr/bin/env python3
"""
API 엔드포인트 기능 테스트
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_comparative_api():
    """기본 비교 분석 API 테스트"""
    print("📊 기본 비교 분석 API 테스트")

    data = {
        "queries": ["한화시스템", "LIG넥스원"],
        "domain": "방산",
        "lookback_days": 30
    }

    try:
        response = requests.post(
            f"{BASE_URL}/report/comparative",
            json=data,
            timeout=30
        )

        print(f"   응답 코드: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 성공!")
            print(f"   타입: {result.get('type')}")
            print(f"   비교 항목: {result.get('meta', {}).get('comparison_count', 0)}개")
            print(f"   마크다운 길이: {len(result.get('markdown', ''))} 글자")
            return True
        else:
            print(f"   ❌ 실패: {response.text}")
            return False

    except Exception as e:
        print(f"   오류: {e}")
        return False

def test_trend_api():
    """기본 트렌드 분석 API 테스트"""
    print("\n📈 기본 트렌드 분석 API 테스트")

    data = {
        "query": "한화",
        "domain": "방산",
        "periods": [30, 90]
    }

    try:
        response = requests.post(
            f"{BASE_URL}/report/trend",
            json=data,
            timeout=30
        )

        print(f"   응답 코드: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 성공!")
            print(f"   타입: {result.get('type')}")
            print(f"   분석 기간: {result.get('meta', {}).get('analysis_points', 0)}개")
            print(f"   마크다운 길이: {len(result.get('markdown', ''))} 글자")
            return True
        else:
            print(f"   ❌ 실패: {response.text}")
            return False

    except Exception as e:
        print(f"   오류: {e}")
        return False

def test_langgraph_comparative_api():
    """LangGraph 비교 분석 API 테스트"""
    print("\n🤖 LangGraph 비교 분석 API 테스트")

    data = {
        "queries": ["삼성전자", "SK하이닉스"],
        "domain": "반도체",
        "lookback_days": 30,
        "analysis_depth": "shallow"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/report/langgraph/comparative",
            json=data,
            timeout=60
        )

        print(f"   응답 코드: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 성공!")
            print(f"   타입: {result.get('type')}")
            print(f"   비교 항목: {result.get('meta', {}).get('comparison_count', 0)}개")
            print(f"   총 처리 시간: {result.get('meta', {}).get('total_processing_time', 0):.2f}초")
            return True
        else:
            print(f"   ❌ 실패: {response.text}")
            return False

    except Exception as e:
        print(f"   오류: {e}")
        return False

def test_langgraph_trend_api():
    """LangGraph 트렌드 분석 API 테스트"""
    print("\n⏰ LangGraph 트렌드 분석 API 테스트")

    data = {
        "query": "한화",
        "domain": "방산",
        "periods": [30, 60],
        "analysis_depth": "shallow"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/report/langgraph/trend",
            json=data,
            timeout=60
        )

        print(f"   응답 코드: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 성공!")
            print(f"   타입: {result.get('type')}")
            print(f"   분석 기간: {result.get('meta', {}).get('analysis_points', 0)}개")
            print(f"   총 처리 시간: {result.get('meta', {}).get('total_processing_time', 0):.2f}초")
            return True
        else:
            print(f"   ❌ 실패: {response.text}")
            return False

    except Exception as e:
        print(f"   오류: {e}")
        return False

def test_server_health():
    """서버 상태 확인"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """메인 테스트"""
    print("🧪 API 엔드포인트 기능 점검")
    print("=" * 50)

    # 서버 상태 확인
    if not test_server_health():
        print("❌ 서버가 실행 중이지 않습니다. uvicorn api.main:app --host 0.0.0.0 --port 8000을 실행하세요.")
        return

    print("✅ 서버 실행 중")

    tests = [
        ("기본 비교 분석 API", test_comparative_api),
        ("기본 트렌드 분석 API", test_trend_api),
        ("LangGraph 비교 분석 API", test_langgraph_comparative_api),
        ("LangGraph 트렌드 분석 API", test_langgraph_trend_api),
    ]

    success_count = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                success_count += 1
                print(f"✅ {test_name} 통과")
            else:
                print(f"❌ {test_name} 실패")
        except Exception as e:
            print(f"❌ {test_name} 오류: {e}")

    print(f"\n🏁 API 테스트 완료")
    print(f"   성공: {success_count}/{len(tests)}")
    print(f"   성공률: {success_count/len(tests)*100:.1f}%")

if __name__ == "__main__":
    main()