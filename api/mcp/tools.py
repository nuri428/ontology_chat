from typing import Any, Dict
from api.logging import setup_logging
logger = setup_logging()
from api.mcp.base import MCPTool
from api.adapters.mcp_opensearch import OpenSearchMCP
from api.adapters.mcp_neo4j import Neo4jMCP
from api.adapters.mcp_stock import StockMCP

class SearchNewsTool:
    name = "search_news"
    description = "뉴스/문서 검색 (OpenSearch). Args: index:str, query:str|dict, limit:int"

    def __init__(self, os_client: OpenSearchMCP | None = None):
        self.os = os_client or OpenSearchMCP()

    async def call(self, **kwargs) -> Dict[str, Any]:
        index = kwargs.get("index", "news_article_bulk")
        query_str = kwargs.get("query", "")
        limit = kwargs.get("limit", 5)
        
        # 문자열 쿼리를 OpenSearch 쿼리로 변환
        if isinstance(query_str, str):
            search_query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query_str,
                                    "fields": ["title^4", "content^2", "text^3", "metadata.title^4", "metadata.content^2"],
                                    "type": "best_fields",
                                    "operator": "or",
                                }
                            },
                            {
                                "query_string": {
                                    "query": query_str,
                                    "fields": ["title^3", "content", "metadata.title^3", "metadata.content", "text"],
                                    "default_operator": "OR",
                                }
                            }
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "sort": [{"created_datetime": {"order": "desc", "missing": "_last"}}]
            }
        else:
            # 이미 딕셔너리인 경우 그대로 사용
            search_query = query_str
            
        logger.info(f"[MCP] search_news index={index} query_str={query_str}")
        res = await self.os.search(index=index, query=search_query, size=limit)
        return {"ok": True, "data": res}

class QueryGraphTool:
    name = "query_graph"
    description = "그래프 질의 (Neo4j). Args: cypher:str, params:dict"

    def __init__(self, neo: Neo4jMCP | None = None):
        self.neo = neo or Neo4jMCP()

    async def call(self, **kwargs) -> Dict[str, Any]:
        cypher = kwargs.get("cypher", "MATCH (n) RETURN n LIMIT 1")
        params = kwargs.get("params", {})
        logger.info(f"[MCP] query_graph cypher={cypher}")
        rows = await self.neo.query(cypher, params)
        logger.info(f"[MCP] query_graph rows={rows}")
        return {"ok": True, "data": rows}
    
class Neo4jDiagTool:
    name = "neo4j_diag"
    description = "Neo4j 연결/DB 상태 진단(현재 DB ping, CURRENT DATABASE, system에서 SHOW DATABASES)"

    def __init__(self, neo: Neo4jMCP | None = None):
        self.neo = neo or Neo4jMCP()

    async def call(self, **kwargs):
        # Neo4jMCP.ping()이 dict로 상세 진단을 반환하게 구현되어 있어야 합니다.
        return await self.neo.ping()


class GetPriceTool:
    name = "get_price"
    description = "주가 현재가(근사) 조회. Args: symbol:str (예: 005930.KS)"

    def __init__(self, st: StockMCP | None = None):
        self.st = st or StockMCP()

    async def call(self, **kwargs):
        symbol = kwargs.get("symbol")
        if not symbol:
            return {"ok": False, "error": "symbol is required"}
        data = await self.st.get_price(symbol)
        return {"ok": True, "data": data}

class GetHistoryTool:
    name = "get_history"
    description = "주가 과거 시세 조회. Args: symbol:str, period:str='1mo', interval:str='1d'"

    def __init__(self, st: StockMCP | None = None):
        self.st = st or StockMCP()

    async def call(self, **kwargs):
        symbol = kwargs.get("symbol")
        period = kwargs.get("period", "1mo")
        interval = kwargs.get("interval", "1d")
        if not symbol:
            return {"ok": False, "error": "symbol is required"}
        data = await self.st.get_history(symbol, period=period, interval=interval)
        return {"ok": True, "data": data}