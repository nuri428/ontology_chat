from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import json
import asyncio
from api.mcp.base import registry
from api.mcp.tools import (
    Neo4jDiagTool, Neo4jMCP, SearchNewsTool, QueryGraphTool, GetPriceTool, GetHistoryTool,
    GetStocksByThemeTool, GetAllThemesTool, GetThemeStocksTool, GetStockBySymbolTool,
    SearchStocksTool, GetTopPerformingStocksTool, InitializeStockDbTool
)
from api.config import settings
from api.services.cypher_builder import build_label_aware_search_cypher
from api.logging import setup_logging

logger = setup_logging()


neo = Neo4jMCP()
router = APIRouter(prefix="/mcp", tags=["mcp"])

# 서비스 인스턴스 (전역, main.py에서 주입 가능)
_chat_service = None
_report_service = None
_langgraph_engine = None

def set_services(chat_service, report_service, langgraph_engine):
    """서비스 인스턴스 주입 (main.py에서 호출)"""
    global _chat_service, _report_service, _langgraph_engine
    _chat_service = chat_service
    _report_service = report_service
    _langgraph_engine = langgraph_engine

class GraphParams(BaseModel):
    q: str
    domain: str | None = None
    lookback_days: int = 180
    limit: int = 30
    
# 초기 등록 (필요시 의존성 주입/지연등록으로 바꿔도 됨)
registry.register(SearchNewsTool())
registry.register(QueryGraphTool())
registry.register(GetPriceTool())
registry.register(GetHistoryTool())
registry.register(Neo4jDiagTool())

# RDB MCP 도구들 등록
registry.register(GetStocksByThemeTool())
registry.register(GetAllThemesTool())
registry.register(GetThemeStocksTool())
registry.register(GetStockBySymbolTool())
registry.register(SearchStocksTool())
registry.register(GetTopPerformingStocksTool())
registry.register(InitializeStockDbTool())

class CallRequest(BaseModel):
    tool: str = Field(..., description="Tool name")
    args: dict = Field(default_factory=dict)

@router.get("/describe")
async def describe_tools():
    return {"tools": registry.list_tools()}

@router.post("/call")
async def call_tool(req: CallRequest):
    try:
        tool = registry.get(req.tool)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    result = await tool.call(**req.args)
    return result

@router.post("/query_graph_default")
async def query_graph_default(p: GraphParams):
    cypher = settings.resolve_search_cypher()
    if not cypher:
        keys_map = settings.get_graph_search_keys()
        cypher = build_label_aware_search_cypher(keys_map)
    if not cypher or not cypher.strip():
        raise HTTPException(status_code=500, detail="No default cypher configured.")

    try:
        rows = await neo.query(
            cypher,
            {
                "q": p.q,
                "domain": p.domain,
                "lookback_days": p.lookback_days,
                "limit": p.limit,
            },
        )
        return {"ok": True, "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== MCP Chat Service 엔드포인트 ==========

class MCPChatRequest(BaseModel):
    """MCP용 채팅 요청"""
    query: str = Field(..., description="사용자 질문")
    user_id: str = Field(default="mcp_client", description="사용자 ID")
    session_id: Optional[str] = Field(default=None, description="세션 ID")
    force_deep_analysis: bool = Field(default=False, description="강제 심층 분석 (LangGraph)")


@router.post("/chat")
async def mcp_chat(req: MCPChatRequest):
    """
    MCP 채팅 엔드포인트 (하이브리드 라우팅)

    - 단순 질문: 빠른 응답 (1.5초)
    - 복잡한 질문: Multi-Agent LangGraph (5초+)
    """
    if not _chat_service or not _langgraph_engine:
        raise HTTPException(
            status_code=503,
            detail="Chat service not initialized. Call set_services() first."
        )

    try:
        from api.services.query_router import QueryRouter
        from api.services.response_formatter import ResponseFormatter
        import numpy as np

        # 하이브리드 라우터 사용
        router_instance = QueryRouter(_chat_service, ResponseFormatter(), _langgraph_engine)
        result = await router_instance.process_query(
            req.query,
            req.user_id,
            req.session_id,
            req.force_deep_analysis
        )

        # numpy 타입 변환
        def convert_numpy(obj):
            if isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        return {"ok": True, "result": convert_numpy(result)}

    except Exception as e:
        logger.error(f"[MCP Chat] 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def mcp_chat_stream(req: MCPChatRequest):
    """
    MCP 채팅 스트리밍 엔드포인트 (실시간 진행 상황 전송)

    - Server-Sent Events (SSE) 사용
    - 각 LangGraph 단계별 진행 상황 전송
    - 고품질 분석에 적합 (60-120초)

    Returns:
        StreamingResponse: text/event-stream
    """
    if not _chat_service or not _langgraph_engine:
        raise HTTPException(
            status_code=503,
            detail="Chat service not initialized."
        )

    async def event_generator():
        """SSE 이벤트 생성기"""
        try:
            logger.info(f"[Stream] 시작: query={req.query}, user={req.user_id}")

            # force_deep_analysis가 True이거나 복잡한 쿼리만 스트리밍
            if req.force_deep_analysis:
                # LangGraph 스트리밍 직접 실행
                async for event in _langgraph_engine.stream_report(
                    query=req.query,
                    analysis_depth="comprehensive" if req.force_deep_analysis else "standard"
                ):
                    # SSE 형식으로 전송
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                    # 백프레셔 방지
                    await asyncio.sleep(0)

            else:
                # 단순 쿼리는 기존 라우터 사용 (1회 전송)
                from api.services.query_router import QueryRouter
                from api.services.response_formatter import ResponseFormatter

                yield f"data: {json.dumps({'type': 'start', 'data': {'query': req.query}}, ensure_ascii=False)}\n\n"

                router_instance = QueryRouter(_chat_service, ResponseFormatter(), _langgraph_engine)
                result = await router_instance.process_query(
                    req.query,
                    req.user_id,
                    req.session_id,
                    False  # force_deep_analysis=False
                )

                # 최종 결과 전송
                yield f"data: {json.dumps({'type': 'final', 'data': result}, ensure_ascii=False)}\n\n"

            # Done 이벤트
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"[Stream] 오류: {e}")
            error_event = {
                "type": "error",
                "data": {"error": str(e)}
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginx buffering 비활성화
        }
    )


# ========== MCP Report Service 엔드포인트 ==========

class MCPReportRequest(BaseModel):
    """MCP용 보고서 요청"""
    query: str = Field(..., description="보고서 주제")
    domain: Optional[str] = Field(default=None, description="도메인 (자동 추론)")
    lookback_days: int = Field(default=30, description="조회 기간 (일)")
    analysis_depth: str = Field(default="standard", description="분석 깊이: shallow/standard/deep/comprehensive")
    symbol: Optional[str] = Field(default=None, description="종목 코드 (선택)")


@router.post("/report/langgraph")
async def mcp_report_langgraph(req: MCPReportRequest):
    """
    MCP LangGraph 보고서 생성 엔드포인트 (Multi-Agent)

    고품질 심층 분석 보고서 생성
    """
    if not _langgraph_engine:
        raise HTTPException(
            status_code=503,
            detail="LangGraph engine not initialized. Call set_services() first."
        )

    # 분석 깊이 검증
    valid_depths = ["shallow", "standard", "deep", "comprehensive"]
    if req.analysis_depth not in valid_depths:
        raise HTTPException(
            status_code=400,
            detail=f"analysis_depth must be one of {valid_depths}"
        )

    try:
        result = await _langgraph_engine.generate_langgraph_report(
            query=req.query,
            domain=req.domain,
            lookback_days=req.lookback_days,
            analysis_depth=req.analysis_depth,
            symbol=req.symbol
        )

        return {"ok": True, "report": result}

    except Exception as e:
        logger.error(f"[MCP Report] 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report/langgraph/stream")
async def mcp_report_langgraph_stream(req: MCPReportRequest):
    """
    MCP LangGraph 보고서 스트리밍 엔드포인트

    실시간 진행 상황과 함께 고품질 보고서 생성
    - Server-Sent Events (SSE)
    - 10단계 워크플로우 진행 상황 전송
    - 각 단계별 부분 결과 제공
    """
    if not _langgraph_engine:
        raise HTTPException(
            status_code=503,
            detail="LangGraph engine not initialized."
        )

    # 분석 깊이 검증
    valid_depths = ["shallow", "standard", "deep", "comprehensive"]
    if req.analysis_depth not in valid_depths:
        raise HTTPException(
            status_code=400,
            detail=f"analysis_depth must be one of {valid_depths}"
        )

    async def event_generator():
        """보고서 생성 SSE 이벤트 생성기"""
        try:
            logger.info(f"[Report Stream] 시작: query={req.query}, depth={req.analysis_depth}")

            # LangGraph 스트리밍 실행
            async for event in _langgraph_engine.stream_report(
                query=req.query,
                domain=req.domain,
                lookback_days=req.lookback_days,
                analysis_depth=req.analysis_depth,
                symbol=req.symbol
            ):
                # SSE 형식으로 전송
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                # 백프레셔 방지
                await asyncio.sleep(0)

            # Done 이벤트
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"[Report Stream] 오류: {e}")
            error_event = {
                "type": "error",
                "data": {"error": str(e)}
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/report/simple")
async def mcp_report_simple(req: MCPReportRequest):
    """
    MCP 간단한 보고서 생성 엔드포인트 (템플릿 기반)

    빠른 응답이 필요한 경우 사용
    """
    if not _report_service:
        raise HTTPException(
            status_code=503,
            detail="Report service not initialized. Call set_services() first."
        )

    try:
        result = await _report_service.generate_report(
            query=req.query,
            domain=req.domain,
            lookback_days=req.lookback_days,
            symbol=req.symbol
        )

        return {"ok": True, "report": result}

    except Exception as e:
        logger.error(f"[MCP Report Simple] 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))