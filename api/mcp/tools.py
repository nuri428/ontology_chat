from typing import Any, Dict

from api.logging import setup_logging
from api.config import settings

from api.adapters.mcp_neo4j import Neo4jMCP
from api.adapters.mcp_opensearch import OpenSearchMCP
from api.adapters.mcp_rdb import RdbMCP
from api.adapters.mcp_stock import StockMCP
from api.mcp.base import MCPTool
from langchain_community.embeddings import OllamaEmbeddings
import numpy as np 
logger = setup_logging()


def normalize_vector(vector):
    vector_array = np.array(vector, dtype=np.float32)
    norm = np.linalg.norm(vector_array)
    if norm == 0:
        return vector_array.tolist()
    return (vector_array / norm).tolist()

class SearchNewsTool:
    name = "search_news"
    description = "뉴스/문서 검색 (OpenSearch). Args: index:str, query:str|dict, limit:int"

    def __init__(self, os_client: OpenSearchMCP | None = None):
        self.os = os_client or OpenSearchMCP()
        # self.embedding_client = OllamaEmbeddings(base_url=settings.get_ollama_base_url(), model=settings.bge_m3_model)
        self.embedding_client = OllamaEmbeddings(base_url="http://192.168.0.10:11434", model="bge-m3")        

    def embedded_query(self, query: str) -> list[float]:
        return normalize_vector(self.embedding_client.embed_query(query))
    
    async def call(self, **kwargs) -> Dict[str, Any]:
        # index = kwargs.get("index", "news_article_embedding")
        index = "news_article_embedding"  # 고정
        query_str = kwargs.get("query", "")
        limit = kwargs.get("limit", 5)
        embedded_query = self.embedding_client.embed_query(query_str)
        # 문자열 쿼리를 OpenSearch 쿼리로 변환
        if isinstance(query_str, str):
            search_query = {
                "query": {
                    "hybrid": {
                        "queries": [
                            {                    
                                "multi_match": {
                                    "query": query_str,
                                    "fields": ["title^4", "content^2", "text^3", "metadata.title^4", "metadata.content^2"],
                                    "type": "best_fields",
                                    "operator": "or",
                                }
                            },
                            {
                                "knn": {
                                    "vector_field": {
                                        "vector": embedded_query,
                                        "k": limit,
                                    }
                                }
                            }
                        ]
                    }
                }
                # "sort": [
                #     {
                #         "meta_data.created_datetime": {
                #             "order": "desc",
                #             "missing": "_last"
                #             }
                #     }
                #     ]                 
            }            
        else:
            # 이미 딕셔너리인 경우 그대로 사용
            search_query = query_str
        # 단순 knn 쿼리부터 테스트
        normalized_query = normalize_vector(embedded_query)
        search_query = {
            "size": limit,
            "query": {
                "hybrid": {
                    "queries": [
                        {
                            "multi_match": {
                                "query": query_str,
                                "fields": ["title^4", "content^2", "text^3", "metadata.title^4"],
                                "type": "best_fields",
                                "operator": "or"
                            }
                        },
                        {
                            "knn": {
                                "vector_field": {
                                    "vector": normalized_query,
                                    "k": limit
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [
                {
                    "metadata.created_date": {
                        "order": "desc",
                        "missing": "_last"
                    }
                }
            ]
        }

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

# RDB MCP Tools
class GetStocksByThemeTool:
    name = "get_stocks_by_theme"
    description = "테마별 관련 종목 조회 (RDB). Args: theme_keyword:str, limit:int=20"

    def __init__(self, rdb: RdbMCP | None = None):
        self.rdb = rdb or RdbMCP()

    async def call(self, **kwargs):
        theme_keyword = kwargs.get("theme_keyword")
        limit = kwargs.get("limit", 20)

        if not theme_keyword:
            return {"ok": False, "error": "theme_keyword is required"}

        try:
            stocks = await self.rdb.get_stocks_by_theme(theme_keyword, limit)
            # StockData 객체를 딕셔너리로 변환
            data = [
                {
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "sector": stock.sector,
                    "industry": stock.industry,
                    "market_cap": stock.market_cap,
                    "price": stock.price,
                    "change_percent": stock.change_percent,
                    "volume": stock.volume,
                    "last_updated": stock.last_updated.isoformat() if stock.last_updated else None
                }
                for stock in stocks
            ]
            return {"ok": True, "data": data}
        except Exception as e:
            logger.error(f"테마별 종목 조회 실패: {e}")
            return {"ok": False, "error": str(e)}

class GetAllThemesTool:
    name = "get_all_themes"
    description = "모든 테마 목록 조회 (RDB). Args: none"

    def __init__(self, rdb: RdbMCP | None = None):
        self.rdb = rdb or RdbMCP()

    async def call(self, **kwargs):
        try:
            themes = await self.rdb.get_all_themes()
            data = [
                {
                    "theme_id": theme.theme_id,
                    "theme_name": theme.theme_name,
                    "description": theme.description,
                    "sector": theme.sector
                }
                for theme in themes
            ]
            return {"ok": True, "data": data}
        except Exception as e:
            logger.error(f"테마 목록 조회 실패: {e}")
            return {"ok": False, "error": str(e)}

class GetThemeStocksTool:
    name = "get_theme_stocks"
    description = "특정 테마의 종목들 조회 (RDB). Args: theme_id:str"

    def __init__(self, rdb: RdbMCP | None = None):
        self.rdb = rdb or RdbMCP()

    async def call(self, **kwargs):
        theme_id = kwargs.get("theme_id")

        if not theme_id:
            return {"ok": False, "error": "theme_id is required"}

        try:
            stocks = await self.rdb.get_theme_stocks(theme_id)
            data = [
                {
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "sector": stock.sector,
                    "industry": stock.industry,
                    "market_cap": stock.market_cap,
                    "price": stock.price,
                    "change_percent": stock.change_percent,
                    "volume": stock.volume,
                    "last_updated": stock.last_updated.isoformat() if stock.last_updated else None
                }
                for stock in stocks
            ]
            return {"ok": True, "data": data}
        except Exception as e:
            logger.error(f"테마 종목 조회 실패: {e}")
            return {"ok": False, "error": str(e)}

class GetStockBySymbolTool:
    name = "get_stock_by_symbol"
    description = "종목 코드로 개별 종목 조회 (RDB). Args: symbol:str"

    def __init__(self, rdb: RdbMCP | None = None):
        self.rdb = rdb or RdbMCP()

    async def call(self, **kwargs):
        symbol = kwargs.get("symbol")

        if not symbol:
            return {"ok": False, "error": "symbol is required"}

        try:
            stock = await self.rdb.get_stock_by_symbol(symbol)
            if not stock:
                return {"ok": False, "error": f"Stock not found: {symbol}"}

            data = {
                "symbol": stock.symbol,
                "name": stock.name,
                "sector": stock.sector,
                "industry": stock.industry,
                "market_cap": stock.market_cap,
                "price": stock.price,
                "change_percent": stock.change_percent,
                "volume": stock.volume,
                "last_updated": stock.last_updated.isoformat() if stock.last_updated else None
            }
            return {"ok": True, "data": data}
        except Exception as e:
            logger.error(f"종목 조회 실패: {e}")
            return {"ok": False, "error": str(e)}

class SearchStocksTool:
    name = "search_stocks"
    description = "종목 이름/코드로 검색 (RDB). Args: query:str, limit:int=10"

    def __init__(self, rdb: RdbMCP | None = None):
        self.rdb = rdb or RdbMCP()

    async def call(self, **kwargs):
        query = kwargs.get("query")
        limit = kwargs.get("limit", 10)

        if not query:
            return {"ok": False, "error": "query is required"}

        try:
            stocks = await self.rdb.search_stocks(query, limit)
            data = [
                {
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "sector": stock.sector,
                    "industry": stock.industry,
                    "market_cap": stock.market_cap,
                    "price": stock.price,
                    "change_percent": stock.change_percent,
                    "volume": stock.volume,
                    "last_updated": stock.last_updated.isoformat() if stock.last_updated else None
                }
                for stock in stocks
            ]
            return {"ok": True, "data": data}
        except Exception as e:
            logger.error(f"종목 검색 실패: {e}")
            return {"ok": False, "error": str(e)}

class GetTopPerformingStocksTool:
    name = "get_top_performing_stocks"
    description = "상승률 기준 상위 종목 조회 (RDB). Args: sector:str=None, limit:int=20"

    def __init__(self, rdb: RdbMCP | None = None):
        self.rdb = rdb or RdbMCP()

    async def call(self, **kwargs):
        sector = kwargs.get("sector")
        limit = kwargs.get("limit", 20)

        try:
            stocks = await self.rdb.get_top_performing_stocks(sector, limit)
            data = [
                {
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "sector": stock.sector,
                    "industry": stock.industry,
                    "market_cap": stock.market_cap,
                    "price": stock.price,
                    "change_percent": stock.change_percent,
                    "volume": stock.volume,
                    "last_updated": stock.last_updated.isoformat() if stock.last_updated else None
                }
                for stock in stocks
            ]
            return {"ok": True, "data": data}
        except Exception as e:
            logger.error(f"상위 종목 조회 실패: {e}")
            return {"ok": False, "error": str(e)}

class InitializeStockDbTool:
    name = "initialize_stock_db"
    description = "주식 DB 테이블 초기화 (RDB). Args: none"

    def __init__(self, rdb: RdbMCP | None = None):
        self.rdb = rdb or RdbMCP()

    async def call(self, **kwargs):
        try:
            await self.rdb.create_tables()
            return {"ok": True, "message": "Database tables created successfully"}
        except Exception as e:
            logger.error(f"DB 테이블 생성 실패: {e}")
            return {"ok": False, "error": str(e)}