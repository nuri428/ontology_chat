#!/usr/bin/env python3
"""
FastAPI-MCP 통합 테스트
"""

import sys
sys.path.insert(0, '/home/nuri/.local/lib/python3.10/site-packages')

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel

# 간단한 FastAPI 앱 생성
app = FastAPI(title="MCP Test", version="1.0.0")

# FastAPI-MCP 통합
mcp = FastApiMCP(
    fastapi=app,
    name="test-mcp",
    description="Test MCP integration"
)

class ChatRequest(BaseModel):
    query: str

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Simple chat endpoint for MCP testing.

    This endpoint will be automatically converted to an MCP tool.
    """
    return {"response": f"You said: {request.query}"}

@app.get("/health")
async def health():
    """
    Health check endpoint.

    This endpoint will be automatically converted to an MCP tool.
    """
    return {"status": "healthy", "service": "mcp-test"}

if __name__ == "__main__":
    print("FastAPI-MCP 테스트 성공!")
    print(f"MCP 이름: {mcp.name}")
    print(f"FastAPI 앱: {app.title}")

    # MCP 도구 목록 확인 (가능한 경우)
    try:
        tools = getattr(mcp, 'tools', [])
        print(f"등록된 MCP 도구 수: {len(tools)}")
        for tool in tools:
            print(f"  - {tool}")
    except Exception as e:
        print(f"MCP 도구 조회 실패: {e}")

    print("테스트 완료!")