#!/usr/bin/env python3
"""
최소한의 FastAPI-MCP 테스트
"""

import sys
sys.path.insert(0, '/home/nuri/.local/lib/python3.10/site-packages')

from fastapi import FastAPI, Body
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel
from typing import Dict, Any

# 최소한의 FastAPI 앱 생성
app = FastAPI(title="MCP Test", version="1.0.0")

# FastAPI-MCP 통합
mcp = FastApiMCP(
    fastapi=app,
    name="test-mcp",
    description="Minimal MCP integration test"
)

# MCP 엔드포인트 마운트 (SSE)
mcp.mount_sse(app, mount_path="/mcp/sse")

# MCP 엔드포인트 마운트 (HTTP)
mcp.mount_http(app, mount_path="/mcp/http")

class ChatRequest(BaseModel):
    query: str

class StockQuery(BaseModel):
    symbol: str
    limit: int = 10

@app.get("/health")
async def health():
    """Health check endpoint - automatically becomes MCP tool"""
    return {"status": "healthy", "service": "mcp-test"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Simple chat endpoint - automatically becomes MCP tool

    Args:
        request: Chat request with query

    Returns:
        Chat response
    """
    return {
        "response": f"You asked: '{request.query}'",
        "timestamp": "2025-09-21",
        "service": "mcp-chat"
    }

@app.get("/stocks/search")
async def search_stocks(query: str, limit: int = 5):
    """
    Stock search endpoint - automatically becomes MCP tool

    Args:
        query: Search term for stocks
        limit: Number of results to return

    Returns:
        List of mock stock data
    """
    mock_stocks = [
        {"name": f"{query} Corp {i}", "symbol": f"{query.upper()}{i:02d}", "price": 100 + i*10}
        for i in range(1, limit + 1)
    ]
    return {
        "success": True,
        "query": query,
        "stocks": mock_stocks
    }

@app.post("/report")
async def generate_report(query: str = Body(..., embed=True)):
    """
    Report generation endpoint - automatically becomes MCP tool

    Args:
        query: Analysis query

    Returns:
        Mock report data
    """
    return {
        "query": query,
        "report": f"Analysis report for: {query}",
        "summary": f"This is a mock analysis of '{query}' topic.",
        "confidence": 85.5,
        "sources_count": 42
    }

if __name__ == "__main__":
    print("🧪 최소한의 FastAPI-MCP 테스트")
    print(f"✓ FastAPI 앱 생성: {app.title}")
    print(f"✓ MCP 통합: {mcp.name}")

    # 라우트 확인
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = getattr(route, 'methods', set())
            if methods:
                routes.append(f"{list(methods)[0]} {route.path}")

    print(f"✓ 등록된 엔드포인트 ({len(routes)}개):")
    for route in routes:
        print(f"  - {route}")

    # MCP 속성 확인
    print(f"\n✓ MCP 객체 정보:")
    print(f"  - name: {getattr(mcp, 'name', 'N/A')}")
    print(f"  - fastapi: {type(getattr(mcp, 'fastapi', None)).__name__}")

    # MCP 메서드 확인
    mcp_methods = [method for method in dir(mcp) if not method.startswith('_')]
    print(f"  - 사용 가능한 메서드: {mcp_methods[:5]}...")

    print(f"\n✓ 테스트 완료! 서버를 시작하려면:")
    print(f"    uvicorn test_mcp_minimal:app --host 127.0.0.1 --port 8001")