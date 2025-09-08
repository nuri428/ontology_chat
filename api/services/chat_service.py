# src/ontology_chat/services/chat_service.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import re
import time
import anyio
from loguru import logger

from api.config import settings
from api.adapters.mcp_opensearch import OpenSearchMCP
from api.adapters.mcp_neo4j import Neo4jMCP
from api.adapters.mcp_stock import StockMCP
from api.services.cypher_builder import build_label_aware_search_cypher
from api.services.formatters import summarize_graph_rows

# --- NEW: 간단한 도메인/룩백 추론 ---
def _infer_domain_and_lookback(query: str) -> tuple[str, int]:
    q = query.lower()
    domain = settings.neo4j_search_default_domain or ""
    lookback = settings.neo4j_search_lookback_days

    # 질의에 '최근', '요즘', '최근 3개월' 류가 있으면 lookback 가변 적용(간단 규칙)
    # 예) "최근 90일", "최근 6개월"
    m = re.search(r"최근\s*(\d+)\s*(일|개월)", q)
    if m:
        val = int(m.group(1))
        unit = m.group(2)
        if unit == "일":
            lookback = max(1, min(365*2, val))
        else:  # 개월
            lookback = max(7, min(365*2, val * 30))

    # 도메인 힌트: 지상무기/전차/자주포/장갑차 등 포함 시 자동 보강
    if any(tok in q for tok in ["지상무기", "전차", "자주포", "장갑차"]):
        domain = (domain + " 지상무기 전차 자주포 장갑차").strip()

    # 회사명 힌트: 한화/한화디펜스 등 포함 시 자동 보강
    if "한화" in q:
        domain = (domain + " 한화 한화디펜스").strip()
    if "kai" in q or "카이" in q:
        domain = (domain + " kai 한국항공우주 k-a1").strip()

    # 중복 공백 정리
    domain = " ".join(domain.split())
    return domain, lookback


def _detect_symbol(text: str) -> Optional[str]:
    m = re.search(r"\b\d{6}\.(KS|KQ)\b", text)
    if m:
        return m.group(0)
    return None


def _format_sources(hits: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for h in hits[:limit]:
        src = h.get("_source", {}) or {}
        meta = src.get("metadata") or {}
        out.append(
            {
                "id": h.get("_id"),
                "title": src.get("title") or meta.get("title") or "(no title)",
                "url": src.get("url") or meta.get("url"),
                "date": (
                    src.get("created_datetime")
                    or src.get("created_date")
                    or meta.get("created_datetime")
                    or meta.get("created_date")
                ),
                "score": h.get("_score"),
                "index": h.get("_index"),
            }
        )
    return out


class ChatService:
    def __init__(self):
        self.os = OpenSearchMCP()
        self.neo = Neo4jMCP()
        self.st = StockMCP()

    async def _graph(self, query: str) -> tuple[list[dict], dict | None]:
        rows, ms, err = await self._query_graph(query, limit=30)
        summary = summarize_graph_rows(rows, max_each=5) if rows else None
        return rows, summary

    async def _search_news(self, query: str, size: int = 5) -> Tuple[List[Dict[str, Any]], float, Optional[str]]:
        t0 = time.perf_counter()
        err: Optional[str] = None
        try:
            os_index = settings.news_bulk_index or "news_article_bulk"
            body = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^4", "content^2", "text^3", "metadata.title^4", "metadata.content^2"],
                                    "type": "best_fields",
                                    "operator": "and",
                                }
                            },
                            {
                                "query_string": {
                                    "query": query,
                                    "fields": ["title^3", "content", "metadata.title^3", "metadata.content", "text"],
                                    "default_operator": "AND",
                                }
                            }
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "sort": [
                    {"created_datetime": {"order": "desc", "missing": "_last"}},
                    {"created_date": {"order": "desc", "missing": "_last"}},
                    "_score"
                ],
                "_source": {"includes": ["title", "url", "media", "portal", "image_url", "created_date", "created_datetime"]}
            }
            res = await self.os.search(index=os_index, query=body, size=size)
            hits = res.get("hits", {}).get("hits", [])
            return hits, (time.perf_counter() - t0) * 1000.0, None
        except Exception as e:
            logger.exception("[/chat] OpenSearch error")
            err = str(e)
            return [], (time.perf_counter() - t0) * 1000.0, err

    async def _query_graph(self, query: str, limit: int = 10):
        t0 = time.perf_counter()
        try:
            cypher = settings.resolve_search_cypher()
            if not cypher:
                # 라벨별 키 매핑으로 동적 생성 (백업)
                keys_map = settings.get_graph_search_keys()
                cypher = build_label_aware_search_cypher(keys_map)

            # --- NEW: 기본/추론 파라미터 합성 ---
            domain_default, lookback_default = settings.get_graph_search_defaults().values()
            domain_infer, lookback_infer = _infer_domain_and_lookback(query)

            params = {
                "q": query,
                "limit": limit,
                "domain": domain_infer or domain_default or "",
                "lookback_days": lookback_infer or lookback_default or 180,
            }

            rows = await self.neo.query(cypher, params)
            return rows, (time.perf_counter() - t0) * 1000.0, None
        except Exception as e:
            logger.exception("[/chat] Neo4j label-aware search error")
            return [], (time.perf_counter() - t0) * 1000.0, str(e)

    async def _get_stock(self, symbol: Optional[str]) -> Tuple[Optional[Dict[str, Any]], float, Optional[str]]:
        t0 = time.perf_counter()
        if not symbol:
            return None, 0.0, None
        try:
            price = await self.st.get_price(symbol)
            return price, (time.perf_counter() - t0) * 1000.0, None
        except Exception as e:
            logger.exception("[/chat] Stock error")
            return None, (time.perf_counter() - t0) * 1000.0, str(e)

    def _compose_answer(
        self,
        query: str,
        news_hits: List[Dict[str, Any]],
        graph_rows: List[Dict[str, Any]],
        stock: Optional[Dict[str, Any]],
    ) -> str:
        lines: List[str] = []
        lines.append(f"### 질의\n- {query}\n")

        if stock and stock.get("price") is not None:
            lines.append(f"### 주가 스냅샷\n- `{stock['symbol']}` 현재가(근사): **{stock['price']}**\n")

        if news_hits:
            lines.append("### 관련 뉴스 상위\n")
            for i, h in enumerate(_format_sources(news_hits, limit=5), 1):
                title = h.get("title") or "(제목 없음)"
                url = h.get("url") or ""
                date = h.get("date") or ""
                lines.append(f"{i}. [{title}]({url}) — {date}")

        if graph_rows:
            lines.append("\n### 그래프 컨텍스트 (샘플)\n")
            for i, r in enumerate(graph_rows[:5], 1):
                n = r.get("n", {})
                labels = r.get("labels", [])
                name = n.get("name") or n.get("title") or n.get("id") or n.get("contractId") or "(노드)"
                lines.append(f"- {i}) {name}  `labels={labels}`")

        if not (news_hits or graph_rows or stock):
            lines.append("> 관련 결과를 찾지 못했습니다. 키워드나 심볼을 조금 더 구체적으로 입력해 보세요.")

        return "\n".join(lines)

    async def generate_answer(self, query: str) -> Dict[str, Any]:
        symbol = _detect_symbol(query)

        async with anyio.create_task_group() as tg:
            news_res: Dict[str, Any] = {}
            graph_res: Dict[str, Any] = {}
            stock_res: Dict[str, Any] = {}

            async def _news():
                hits, ms, err = await self._search_news(query, size=5)
                news_res.update({"hits": hits, "latency_ms": ms, "error": err})

            async def _graph():
                rows, ms, err = await self._query_graph(query, limit=30)
                # 간단 요약을 메타로도 넣고 싶으면 여기서 생성
                graph_res.update({"rows": rows, "latency_ms": ms, "error": err})

            async def _stock():
                price, ms, err = await self._get_stock(symbol)
                stock_res.update({"price": price, "latency_ms": ms, "error": err})

            tg.start_soon(_news)
            tg.start_soon(_graph)
            tg.start_soon(_stock)

        answer = self._compose_answer(
            query=query,
            news_hits=news_res.get("hits") or [],
            graph_rows=graph_res.get("rows") or [],
            stock=stock_res.get("price"),
        )

        meta = {
            "orchestrator": "v0",
            "latency_ms": {
                "opensearch": round(news_res.get("latency_ms", 0.0), 2),
                "neo4j": round(graph_res.get("latency_ms", 0.0), 2),
                "stock": round(stock_res.get("latency_ms", 0.0), 2),
            },
            "errors": {
                "opensearch": news_res.get("error"),
                "neo4j": graph_res.get("error"),
                "stock": stock_res.get("error"),
            },
            "symbol_detected": symbol,
            "indices": {
                "news_bulk_index": settings.news_bulk_index,
                "news_embedding_index": settings.news_embedding_index,
            },
            "database": settings.neo4j_database,
        }

        sources = _format_sources(news_res.get("hits") or [], limit=5)

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "graph_samples": graph_res.get("rows")[:3] if graph_res.get("rows") else [],
            "graph_summary": summarize_graph_rows(graph_res.get("rows") or [], max_each=5) if graph_res.get("rows") else None,
            "stock": stock_res.get("price"),
            "meta": meta,
        }