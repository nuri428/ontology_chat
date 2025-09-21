#!/usr/bin/env python3
"""MCP 클라이언트 테스트"""

import asyncio
import json
import httpx

async def test_mcp_tools():
    """MCP 도구 목록 테스트"""
    try:
        # SSE 연결을 통한 MCP 테스트
        timeout = httpx.Timeout(10.0, read=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            # SSE 엔드포인트에 연결하여 세션 ID 받기
            async with client.stream(
                "GET",
                "http://localhost:8003/mcp/sse",
                headers={"Accept": "text/event-stream"}
            ) as response:
                print(f"SSE Response Status: {response.status_code}")

                # 첫 번째 이벤트 읽기
                async for line in response.aiter_lines():
                    print(f"SSE Line: {line}")
                    if line.startswith('data: '):
                        endpoint = line.replace('data: ', '')
                        print(f"Messages endpoint: {endpoint}")
                        break

                # tools/list 요청
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                }

                post_response = await client.post(
                    f"http://localhost:8003{endpoint}",
                    json=tools_request,
                    headers={"Content-Type": "application/json"}
                )

                print(f"Tools list response status: {post_response.status_code}")
                print(f"Tools list response: {post_response.text}")

                # 응답을 받기 위해 SSE 스트림 다시 연결
                print("Listening for MCP response...")
                async with client.stream(
                    "GET",
                    f"http://localhost:8003{endpoint}",
                    headers={"Accept": "text/event-stream"}
                ) as response_stream:
                    line_count = 0
                    async for line in response_stream.aiter_lines():
                        print(f"Response Line: {line}")
                        line_count += 1
                        if line_count > 10:  # 최대 10줄만 읽기
                            break

    except Exception as e:
        import traceback
        print(f"Error testing MCP: {e}")
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
