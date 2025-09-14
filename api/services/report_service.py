# src/ontology_chat/services/report_service.py
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from loguru import logger

from api.adapters.mcp_neo4j import Neo4jMCP
from api.adapters.mcp_opensearch import OpenSearchMCP
from api.adapters.mcp_stock import StockMCP
from api.config import settings
from api.services.cypher_builder import build_label_aware_search_cypher

# ========== 유틸 ==========

def _safe_dt(s: Any) -> Optional[str]:
    """neo4j DateTime/str -> ISO8601 문자열로 정규화."""
    try:
        # neo4j python 드라이버의 DateTime 객체는 str()로 ISO 비슷하게 나옴
        return str(s) if s else None
    except Exception:
        return None

def _fmt_ccy(v: Any, ccy: str | None = None) -> str:
    try:
        fv = float(v)
        if fv >= 1_0000_0000:  # 억 단위 표시 (KRW 기준 감)
            return f"{fv/1_0000_0000:.1f}억" + (f" {ccy}" if ccy else "")
        if fv >= 1_0000:       # 만 단위
            return f"{fv/1_0000:.1f}만" + (f" {ccy}" if ccy else "")
        return f"{fv:,.0f}" + (f" {ccy}" if ccy else "")
    except Exception:
        return str(v)

def _flatten_news_hits(hits: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
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

# ========== 데이터 컨테이너 ==========

class ReportRequest(BaseModel):
    query: str = Field(..., description="자연어 질의, 예: '한화 지상무기 수주'")
    domain: Optional[str] = Field(None, description="도메인 보조 키워드, 예: '지상무기 전차 자주포 장갑차'")
    lookback_days: int = Field(180, ge=1, le=720)
    news_size: int = Field(20, ge=5, le=200)
    graph_limit: int = Field(50, ge=10, le=200)
    symbol: Optional[str] = Field(None, description="주가 심볼(선택). 예: '005930.KS'")

class ReportResponse(BaseModel):
    markdown: str
    metrics: Dict[str, Any]
    meta: Dict[str, Any]
    
@dataclass
class ReportContext:
    query: str
    lookback_days: int
    domain: Optional[str]
    news_hits: List[Dict[str, Any]]
    graph_rows: List[Dict[str, Any]]
    stock: Optional[Dict[str, Any]]
    meta: Dict[str, Any]

# ========== 핵심 서비스 ==========

class ReportService:
    """
    - ES, Neo4j, Stock에서 데이터를 끌어와 간단한 지표를 만들고
    - Markdown 보고서(텍스트)로 조립
    """
    def __init__(self):
        self.os = OpenSearchMCP()
        self.neo = Neo4jMCP()
        self.st = StockMCP()

    async def fetch_context(
        self,
        query: str,
        *,
        news_size: int = 20,
        graph_limit: int = 50,
        lookback_days: int = 180,
        domain: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> ReportContext:
        # --- OpenSearch ---
        os_index = settings.news_bulk_index or "news_article_bulk"
        os_body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "title^4", "content^2", "text^3",
                                    "metadata.title^4", "metadata.content^2"
                                ],
                                "type": "best_fields",
                                "operator": "and",
                            }
                        },
                        {
                            "query_string": {
                                "query": query,
                                "fields": [
                                    "title^3","content","metadata.title^3","metadata.content","text"
                                ],
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
            "_source": {
                "includes": ["title","url","media","portal","image_url","created_date","created_datetime"]
            }
        }
        news_res = await self.os.search(index=os_index, query=os_body, size=news_size)
        news_hits = news_res.get("hits", {}).get("hits", [])
        # Fallback: 인덱스/쿼리 불일치로 결과 0인 경우, 와일드카드 및 단순 쿼리 재시도
        if not news_hits:
            try:
                fallback_index = "news-*"
                fallback_body = {
                    "query": {
                        "query_string": {
                            "query": query,
                            "fields": ["title^3","content","text","metadata.title^3","metadata.content"],
                            "default_operator": "OR",
                        }
                    },
                    "sort": [
                        {"created_datetime": {"order": "desc", "missing": "_last"}},
                        {"created_date": {"order": "desc", "missing": "_last"}},
                        "_score"
                    ],
                    "_source": {"includes": ["title","url","created_date","created_datetime"]}
                }
                news_res_fb = await self.os.search(index=fallback_index, query=fallback_body, size=news_size)
                news_hits = news_res_fb.get("hits", {}).get("hits", [])
            except Exception as e:
                logger.warning(f"[ReportService] OpenSearch fallback failed: {e}")

        # --- Neo4j (검색 Cypher 우선: 파일/환경에서 로드 → 없으면 라벨어웨어 빌드) ---
        cypher = settings.resolve_search_cypher()
        if not cypher:
            keys_map = settings.get_graph_search_keys()
            cypher = build_label_aware_search_cypher(keys_map)

        params = {"q": query, "limit": graph_limit}
        # 옵션 파라미터(존재해도 Cypher에서 안 쓰면 무시됨)
        params["lookback_days"] = lookback_days
        if domain:
            params["domain"] = domain

        graph_rows = await self.neo.query(cypher, params)

        # --- Stock ---
        stock_data = None
        if symbol:
            try:
                stock_data = await self.st.get_price(symbol)
            except Exception as e:
                logger.warning(f"[ReportService] Stock error: {e}")

        meta = {
            "indices": {
                "news_bulk_index": settings.news_bulk_index,
                "news_embedding_index": settings.news_embedding_index,
            },
            "database": settings.neo4j_database,
            "lookback_days": lookback_days,
            "domain": domain,
            "news_hits_count": len(news_hits),
            "news_index_used": os_index,
        }
        return ReportContext(
            query=query,
            lookback_days=lookback_days,
            domain=domain,
            news_hits=news_hits,
            graph_rows=graph_rows,
            stock=stock_data,
            meta=meta,
        )

    # --------- 지표 계산 ---------

    def compute_graph_metrics(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        - 라벨 분포
        - 계약(Contract) 합계/상위 샘플
        - 연결 단서(Company/Program/Weapon 등 이름 샘플)
        """
        label_counter = Counter()
        contracts: List[Dict[str, Any]] = []
        companies: List[str] = []
        programs: List[str] = []
        weapons: List[str] = []
        events_sample: List[Dict[str, Any]] = []

        for r in rows:
            labels = r.get("labels", []) or []
            label_counter.update(labels)
            n = r.get("n") or {}

            if "Contract" in labels:
                contracts.append({
                    "contractId": n.get("contractId"),
                    "amount": n.get("amount"),
                    "value_ccy": n.get("value_ccy"),
                    "award_date": n.get("award_date"),
                })
            if "Company" in labels:
                name = n.get("name")
                if name:
                    companies.append(name)
            if "Program" in labels:
                name = n.get("label") or n.get("code")
                if name:
                    programs.append(name)
            if "Weapon" in labels or "WeaponSystem" in labels:
                name = n.get("label") or n.get("name")
                if name:
                    weapons.append(name)
            if "Event" in labels:
                events_sample.append({
                    "event_type": n.get("event_type"),
                    "title": n.get("title"),
                    "published_at": _safe_dt(n.get("published_at")),
                    "sentiment": n.get("sentiment"),
                })

        # 계약 합계/상위
        total_amt = 0.0
        for c in contracts:
            try:
                if c.get("amount") is not None:
                    total_amt += float(c["amount"])
            except Exception:
                pass

        top_contracts = sorted(
            contracts, key=lambda x: (x.get("amount") or 0), reverse=True
        )[:5]

        return {
            "label_distribution": label_counter.most_common(),
            "contract_total_amount": total_amt,
            "contract_top": top_contracts,
            "companies_top": [k for k, _ in Counter(companies).most_common(8)],
            "programs_top": [k for k, _ in Counter(programs).most_common(8)],
            "weapons_top": [k for k, _ in Counter(weapons).most_common(8)],
            "events_sample": events_sample[:8],
        }

    def compute_news_metrics(self, hits: List[Dict[str, Any]]) -> Dict[str, Any]:
        items = _flatten_news_hits(hits, limit=10)
        return {
            "top_news": items,
            "count": len(hits),
        }

    def compute_stock_metrics(self, stock: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not stock:
            return {}
        return {
            "symbol": stock.get("symbol"),
            "price": stock.get("price"),
        }

    # --------- 리포트 생성 (Markdown) ---------

    def generate_markdown(self, ctx: ReportContext) -> str:
        g = self.compute_graph_metrics(ctx.graph_rows)
        n = self.compute_news_metrics(ctx.news_hits)
        s = self.compute_stock_metrics(ctx.stock)

        lines: List[str] = []
        lines.append("# 방산 온톨로지 리포트\n")
        lines.append(f"**질의**: `{ctx.query}`  \n"
                     f"**Lookback**: {ctx.lookback_days}일  "
                     f"{'(도메인: ' + ctx.domain + ')' if ctx.domain else ''}\n")
        lines.append("---")

        # Stock
        if s:
            lines.append("## 주가 스냅샷")
            lines.append(f"- `{s.get('symbol')}` 현재가(근사): **{s.get('price')}**\n")

        # Graph metrics
        lines.append("## 그래프 컨텍스트 요약")
        # 라벨 분포
        if g["label_distribution"]:
            lines.append("**라벨 분포 Top-8**")
            lines.append("")
            for label, cnt in g["label_distribution"][:8]:
                lines.append(f"- `{label}`: {cnt}개")
            lines.append("")

        # 계약 합계 / 상위
        lines.append("**계약(Contract) 합계/상위**")
        lines.append(f"- 합계(표면상): **{_fmt_ccy(g['contract_total_amount'])}**")
        if g["contract_top"]:
            lines.append("- 상위 계약:")
            for c in g["contract_top"]:
                amount_s = _fmt_ccy(c.get("amount"), c.get("value_ccy"))
                lines.append(f"  - `{c.get('contractId')}` · {amount_s} · {c.get('award_date')}")
        lines.append("")

        # 엔터티 Top
        if g["companies_top"]:
            lines.append("**연관 회사 Top**: " + ", ".join([f"`{x}`" for x in g["companies_top"]]))
        if g["programs_top"]:
            lines.append("**연관 프로그램 Top**: " + ", ".join([f"`{x}`" for x in g["programs_top"]]))
        if g["weapons_top"]:
            lines.append("**연관 무기체계 Top**: " + ", ".join([f"`{x}`" for x in g["weapons_top"]]))
        lines.append("")

        # 이벤트 샘플
        if g["events_sample"]:
            lines.append("**이벤트 샘플**")
            for e in g["events_sample"]:
                title = e.get("title") or "(제목 없음)"
                lines.append(f"- {e.get('event_type') or '?'} · {e.get('sentiment') or '-'} · {e.get('published_at') or '-'}")
                if title:
                    lines.append(f"  - {title}")
            lines.append("")

        # 뉴스 Top
        lines.append("## 관련 뉴스 Top-10")
        if n["top_news"]:
            for i, item in enumerate(n["top_news"], 1):
                title = item.get("title") or "(제목 없음)"
                url = item.get("url") or ""
                date = item.get("date") or ""
                lines.append(f"{i}. [{title}]({url}) — {date}")
        else:
            lines.append("> 관련 뉴스가 없습니다.")
        lines.append("")

        # 시사점(초안)
        lines.append("## 시사점 (초안)")
        insight_bullets = []
        if g["contract_total_amount"] > 0:
            insight_bullets.append("최근 기간 계약 규모가 유의미함 → 실적/주가 반영 가능성 검토.")
        if g["companies_top"]:
            insight_bullets.append(f"핵심 참여사: {', '.join(g['companies_top'][:3])}")
        if g["weapons_top"]:
            insight_bullets.append(f"핵심 무기체계: {', '.join(g['weapons_top'][:3])}")
        if not insight_bullets:
            insight_bullets.append("데이터가 제한적이므로 기간/키워드를 조정하거나 그래프 스키마 확충 필요.")
        for b in insight_bullets:
            lines.append(f"- {b}")

        lines.append("\n---\n*이 리포트는 Neo4j 그래프/뉴스 인덱스/주가 스냅샷을 결합하여 자동 생성되었습니다.*\n")
        return "\n".join(lines)

    async def generate_report(
        self,
        query: str,
        *,
        domain: Optional[str] = None,
        lookback_days: int = 180,
        news_size: int = 20,
        graph_limit: int = 50,
        symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        최상위 API:
        - 컨텍스트 수집 → 지표 계산 → Markdown 조립
        - 반환: {"markdown": ..., "ctx": ReportContext, "metrics": {...}}
        """
        ctx = await self.fetch_context(
            query=query,
            news_size=news_size,
            graph_limit=graph_limit,
            lookback_days=lookback_days,
            domain=domain,
            symbol=symbol,
        )
        md = self.generate_markdown(ctx)
        metrics = {
            "graph": self.compute_graph_metrics(ctx.graph_rows),
            "news": self.compute_news_metrics(ctx.news_hits),
            "stock": self.compute_stock_metrics(ctx.stock),
        }
        return {"markdown": md, "ctx": ctx, "metrics": metrics}
