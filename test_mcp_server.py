#!/usr/bin/env python3
"""
MCP 서버 테스트 스크립트
"""

import asyncio
import json
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

async def test_mcp_tools():
    """MCP 도구들을 테스트"""

    print("MCP 서버 도구 테스트 시작...\n")

    # MCP 서버 모듈 import
    try:
        from mcp_server import server, call_tool
        from mcp.types import ToolCall
        print("✓ MCP 서버 모듈 import 성공\n")
    except ImportError as e:
        print(f"✗ MCP 서버 모듈 import 실패: {e}")
        print("\nmcp 패키지를 설치해주세요:")
        print("pip install mcp")
        return

    # 사용 가능한 도구 목록 확인
    print("=" * 50)
    print("사용 가능한 도구 목록:")
    print("=" * 50)

    tools = await server.list_tools()
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool.name}")
        print(f"   설명: {tool.description}")
        print()

    # 간단한 테스트 케이스들
    test_cases = [
        {
            "name": "chat",
            "description": "챗봇 대화 테스트",
            "arguments": {"query": "안녕하세요. 테스트입니다."}
        },
        {
            "name": "search_stocks",
            "description": "종목 검색 테스트",
            "arguments": {"query": "삼성", "limit": 3}
        },
        {
            "name": "get_market_themes",
            "description": "시장 테마 조회 테스트",
            "arguments": {}
        }
    ]

    print("=" * 50)
    print("도구 실행 테스트:")
    print("=" * 50)

    for test in test_cases:
        print(f"\n테스트: {test['description']}")
        print(f"도구: {test['name']}")
        print(f"인자: {test['arguments']}")

        try:
            # ToolCall 객체 생성
            tool_call = ToolCall(
                id=f"test_{test['name']}",
                name=test['name'],
                arguments=test['arguments']
            )

            # 도구 실행
            results = await call_tool(tool_call)

            if results:
                result = results[0]
                if hasattr(result, 'content') and result.content:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        # JSON 파싱 시도
                        try:
                            data = json.loads(content.text)
                            print("✓ 실행 성공")
                            print(f"  결과 타입: {type(data).__name__}")

                            # 결과 미리보기 (너무 길면 잘라서 표시)
                            preview = str(data)
                            if len(preview) > 200:
                                preview = preview[:200] + "..."
                            print(f"  결과 미리보기: {preview}")
                        except json.JSONDecodeError:
                            print("✓ 실행 성공 (텍스트 결과)")
                            print(f"  결과: {content.text[:200]}...")
                else:
                    print("✓ 실행 성공 (결과 없음)")
            else:
                print("✗ 실행 실패 (빈 결과)")

        except Exception as e:
            print(f"✗ 실행 실패: {e}")

    print("\n" + "=" * 50)
    print("테스트 완료!")
    print("=" * 50)


async def test_complex_report():
    """복잡한 리포트 생성 테스트"""

    print("\n" + "=" * 50)
    print("복잡한 리포트 생성 테스트:")
    print("=" * 50)

    try:
        from mcp_server import call_tool
        from mcp.types import ToolCall

        # 전망 리포트 생성 테스트
        print("\n전망 리포트 생성 중...")

        tool_call = ToolCall(
            id="test_forecast",
            name="generate_forecast_report",
            arguments={
                "query": "AI 반도체 산업 전망",
                "keywords": ["AI", "반도체", "GPU", "데이터센터"],
                "companies": ["삼성전자", "SK하이닉스", "네이버"],
                "lookback_days": 30,
                "include_news": True,
                "include_ontology": True,
                "report_mode": "테마별 분석"
            }
        )

        results = await call_tool(tool_call)

        if results and results[0].content:
            data = json.loads(results[0].content[0].text)
            print("✓ 전망 리포트 생성 성공")
            print(f"  - 쿼리: {data.get('query', 'N/A')}")
            print(f"  - 모드: {data.get('report_mode', 'N/A')}")
            print(f"  - 키워드: {', '.join(data.get('keywords', []))}")
            print(f"  - 기업: {', '.join(data.get('companies', []))}")

            # 요약 정보 출력
            if 'executive_summary' in data:
                print("\n[경영진 요약]")
                print(data['executive_summary'][:300] + "...")

    except Exception as e:
        print(f"✗ 복잡한 리포트 테스트 실패: {e}")


async def main():
    """메인 테스트 함수"""

    print("🚀 Ontology Chat MCP 서버 테스트\n")

    # 환경 변수 체크
    import os
    env_vars = ["OPENAI_API_KEY", "NEO4J_URI", "OPENSEARCH_HOST"]

    print("환경 변수 체크:")
    for var in env_vars:
        if os.getenv(var):
            print(f"  ✓ {var}: 설정됨")
        else:
            print(f"  ✗ {var}: 설정 안됨")
    print()

    # 기본 도구 테스트
    await test_mcp_tools()

    # 복잡한 리포트 테스트 (선택적)
    response = input("\n복잡한 리포트 생성을 테스트하시겠습니까? (y/n): ")
    if response.lower() == 'y':
        await test_complex_report()

    print("\n테스트 스크립트 종료")


if __name__ == "__main__":
    asyncio.run(main())