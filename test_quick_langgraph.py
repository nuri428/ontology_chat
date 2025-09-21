#!/usr/bin/env python3
"""
빠른 LangGraph API 테스트
"""

import requests
import json

def quick_test():
    """빠른 테스트"""
    print("🔥 빠른 LangGraph API 테스트")

    data = {
        "req": {
            "query": "한화",
            "domain": "방산",
            "lookback_days": 30,
            "news_size": 5,
            "graph_limit": 10
        },
        "analysis_depth": "shallow"
    }

    try:
        response = requests.post(
            "http://localhost:8000/report/langgraph",
            json=data,
            timeout=60
        )

        print(f"응답 코드: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 성공!")
            print(f"   타입: {result.get('type')}")
            print(f"   품질점수: {result.get('quality_score')}")
            print(f"   컨텍스트: {result.get('contexts_count')}개")
            print(f"   처리시간: {result.get('processing_time'):.2f}초")
        else:
            print(f"❌ 실패: {response.text}")

    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    quick_test()