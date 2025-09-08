from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from api.mcp.base import registry
from api.mcp.tools import Neo4jDiagTool, Neo4jMCP, SearchNewsTool, QueryGraphTool, GetPriceTool, GetHistoryTool
from api.config import settings
from api.services.cypher_builder import build_label_aware_search_cypher


neo = Neo4jMCP()
router = APIRouter(prefix="/mcp", tags=["mcp"])

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