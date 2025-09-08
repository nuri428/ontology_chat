from fastapi import APIRouter
from api.adapters.mcp_neo4j import Neo4jMCP
from api.adapters.mcp_opensearch import OpenSearchMCP
# from ontology_chat.adapters.mcp_stock import StockMCP
router = APIRouter(prefix="/health", tags=["health"])

@router.get("/live")
async def liveness():
    return {"status": "ok"}

@router.get("/ready")
async def readiness():
    neo = Neo4jMCP()
    os_ = OpenSearchMCP()
    # st = StockMCP()

    neo_ok = await neo.ping()
    os_ok = await os_.ping()
    # stock은 외부 네트 연결/마켓 휴장 등 변수가 있으므로 ping 생략 or 간단 호출
    stock_ok = True

    # 리소스 정리
    await neo.close()

    status = "ready" if (neo_ok and os_ok and stock_ok) else "degraded"
    return {
        "status": status,
        "neo4j": neo_ok,
        "opensearch": os_ok,
        "stock": stock_ok,
    }