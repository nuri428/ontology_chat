# src/ontology_chat/services/report_service.py
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from api.adapters.mcp_neo4j import Neo4jMCP
from api.adapters.mcp_opensearch import OpenSearchMCP
from api.adapters.mcp_stock import StockMCP
from api.adapters.ollama_embedding import OllamaEmbeddingMCP
from api.config import settings
from api.logging import setup_logging
from api.services.cypher_builder import build_label_aware_search_cypher
from icecream import ic
logger = setup_logging()
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
    query: str = Field(..., description="자연어 질의, 예: '기업명 제품 수주'")
    domain: Optional[str] = Field(None, description="도메인 보조 키워드, 예: '제품 시스템 서비스 플랫폼'")
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
        self.embedding = OllamaEmbeddingMCP() if settings.enable_hybrid_search else None

    def _extract_keywords(self, query: str, domain: Optional[str] = None) -> List[str]:
        """쿼리에서 핵심 키워드 추출"""
        import re

        # 불용어 제거
        stop_words = {'은', '는', '이', '가', '을', '를', '의', '에', '에서', '로', '와', '과', '관련', '에서는', '?', '!'}

        # 쿼리 정제
        query_words = re.findall(r'\b\w+\b', query.lower())
        keywords = [word for word in query_words if word not in stop_words and len(word) >= 2]

        # 도메인 키워드 추가
        if domain:
            domain_words = re.findall(r'\b\w+\b', domain.lower())
            domain_keywords = [word for word in domain_words if word not in stop_words and len(word) >= 2]
            keywords.extend(domain_keywords)

        # 중요도 순서 정렬 (길이 기준)
        keywords = sorted(set(keywords), key=len, reverse=True)

        return keywords[:10]  # 상위 10개만

    async def _vector_search(self, index: str, query_vector: List[float], size: int = 10) -> List[Dict[str, Any]]:
        """벡터 유사도 검색 (news_article_embedding 인덱스)"""
        vector_query = {
            "size": size,
            "query": {
                "knn": {
                    "vector_field": {
                        "vector": query_vector,
                        "k": size
                    }
                }
            },
            "_source": {
                "includes": ["title", "url", "created_date", "created_datetime", "text", "metadata"]
            }
        }

        try:
            vector_res = await self.os.search(index=index, query=vector_query, size=size)
            hits = vector_res.get("hits", {}).get("hits", [])
            logger.debug(f"[ReportService] Vector search returned {len(hits)} results")
            return hits
        except Exception as e:
            logger.warning(f"[ReportService] Vector search failed: {e}")
            return []

    async def _keyword_search(self, index: str, query: str, size: int = 10) -> List[Dict[str, Any]]:
        """키워드 검색 (기존 로직)"""
        keyword_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "text^2", "content^1.5"],
                    "type": "best_fields"
                }
            },
            "_source": {
                "includes": ["title", "url", "created_date", "created_datetime", "text", "content"]
            }
        }

        try:
            keyword_res = await self.os.search(index=index, query=keyword_query, size=size)
            return keyword_res.get("hits", {}).get("hits", [])
        except Exception as e:
            logger.warning(f"[ReportService] Keyword search failed: {e}")
            return []

    def _merge_rrf(self, keyword_results: List[Dict[str, Any]], vector_results: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion으로 키워드/벡터 검색 결과 결합"""

        # 문서별 점수 계산
        doc_scores = {}

        # 키워드 검색 결과 점수 (가중치 0.6)
        for rank, hit in enumerate(keyword_results):
            doc_id = hit.get("_id")
            if doc_id:
                rrf_score = 0.6 / (k + rank + 1)
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
                if doc_id not in [h.get("_id") for h in doc_scores.get("docs", [])]:
                    doc_scores.setdefault("docs", []).append(hit)

        # 벡터 검색 결과 점수 (가중치 0.4)
        for rank, hit in enumerate(vector_results):
            doc_id = hit.get("_id")
            if doc_id:
                rrf_score = 0.4 / (k + rank + 1)
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
                if doc_id not in [h.get("_id") for h in doc_scores.get("docs", [])]:
                    doc_scores.setdefault("docs", []).append(hit)

        # 점수순으로 정렬
        merged_docs = doc_scores.get("docs", [])
        for doc in merged_docs:
            doc_id = doc.get("_id")
            doc["_score"] = doc_scores.get(doc_id, 0)

        merged_docs.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return merged_docs

    async def _hybrid_search(self, query: str, size: int = 20) -> List[Dict[str, Any]]:
        """하이브리드 검색: 키워드 + 벡터 검색 결합"""
        if not settings.enable_hybrid_search or not self.embedding:
            # 하이브리드 검색 비활성화시 키워드 검색만
            return await self._keyword_search(settings.news_bulk_index, query, size)

        try:
            # BGE-M3로 쿼리 임베딩 생성
            query_vector = await self.embedding.encode(query)

            # 병렬로 키워드/벡터 검색 실행
            keyword_task = self._keyword_search(settings.news_embedding_index, query, size)
            vector_task = self._vector_search(settings.news_embedding_index, query_vector, size)

            keyword_results, vector_results = await keyword_task, await vector_task

            # RRF로 결합
            merged_results = self._merge_rrf(keyword_results, vector_results)

            logger.info(f"[ReportService] Hybrid search: keyword={len(keyword_results)}, vector={len(vector_results)}, merged={len(merged_results)}")
            return merged_results[:size]

        except Exception as e:
            logger.error(f"[ReportService] Hybrid search failed: {e}")
            # 실패시 기존 키워드 검색으로 fallback
            return await self._keyword_search(settings.news_bulk_index, query, size)

    def _build_fallback_query(self, strategy: dict) -> dict:
        """Fallback 검색 쿼리 생성"""
        if strategy["strategy"] == "individual_keywords":
            return {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": keyword,
                                    "fields": ["title^4", "content^1.5", "text^2", "metadata.title^4"],
                                    "type": "best_fields",
                                    "boost": 3.0 - i * 0.5  # 중요도에 따라 부스트 조정
                                }
                            }
                            for i, keyword in enumerate(strategy["keywords"])
                        ],
                        "minimum_should_match": 1
                    }
                },
                "sort": ["_score", {"created_datetime": {"order": "desc", "missing": "_last"}}],
                "_source": {"includes": ["title", "url", "created_date", "created_datetime", "content"]}
            }

        elif strategy["strategy"] == "fuzzy_match":
            return {
                "query": {
                    "multi_match": {
                        "query": strategy["query"],
                        "fields": ["title^3", "content", "text^1.5"],
                        "type": "best_fields",
                        "fuzziness": strategy.get("fuzziness", "AUTO"),
                        "prefix_length": 1,
                        "max_expansions": 50
                    }
                },
                "sort": ["_score", {"created_datetime": {"order": "desc", "missing": "_last"}}],
                "_source": {"includes": ["title", "url", "created_date", "created_datetime", "content"]}
            }

        elif strategy["strategy"] == "wildcard":
            return {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "wildcard": {
                                    "title": {"value": f"*{keyword}*", "boost": 2.0}
                                }
                            }
                            for keyword in strategy["keywords"]
                        ] + [
                            {
                                "wildcard": {
                                    "content": {"value": f"*{keyword}*", "boost": 1.0}
                                }
                            }
                            for keyword in strategy["keywords"]
                        ],
                        "minimum_should_match": 1
                    }
                },
                "sort": ["_score", {"created_datetime": {"order": "desc", "missing": "_last"}}],
                "_source": {"includes": ["title", "url", "created_date", "created_datetime", "content"]}
            }

        # 기본 쿼리 (fallback의 fallback)
        return {
            "query": {"match_all": {}},
            "sort": [{"created_datetime": {"order": "desc", "missing": "_last"}}],
            "_source": {"includes": ["title", "url", "created_date", "created_datetime"]},
            "size": 10
        }

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
        # --- OpenSearch: 하이브리드 검색 (키워드 + 벡터) 또는 기존 검색 ---
        try:
            # 하이브리드 검색 시도
            news_hits = await self._hybrid_search(query, news_size)

            if news_hits:
                logger.info(f"[ReportService] Hybrid search successful: {len(news_hits)} results")
            else:
                logger.info("[ReportService] Hybrid search returned no results, trying fallback")
        except Exception as e:
            logger.warning(f"[ReportService] Hybrid search failed: {e}")
            news_hits = []
        # 개선된 Fallback: 단계별 유연성 증가
        if not news_hits:
            fallback_strategies = [
                # 전략 1: 키워드별 개별 검색
                {
                    "strategy": "individual_keywords",
                    "keywords": query_keywords[:2],  # 상위 2개 키워드만
                    "operator": "OR"
                },
                # 전략 2: 매우 유연한 부분 매칭
                {
                    "strategy": "fuzzy_match",
                    "query": query,
                    "fuzziness": "AUTO"
                },
                # 전략 3: 와일드카드 검색
                {
                    "strategy": "wildcard",
                    "keywords": [kw for kw in query_keywords if len(kw) >= 3][:3]
                }
            ]

            for strategy in fallback_strategies:
                try:
                    for fallback_index in ["news-*", "news_article_bulk", "news*"]:
                        try:
                            fallback_body = self._build_fallback_query(strategy)
                            news_res_fb = await self.os.search(index=fallback_index, query=fallback_body, size=news_size)
                            news_hits = news_res_fb.get("hits", {}).get("hits", [])
                            if news_hits:
                                logger.info(f"[ReportService] Fallback success with {strategy['strategy']} on {fallback_index}")
                                break
                        except Exception as fb_e:
                            logger.warning(f"[ReportService] Fallback {strategy['strategy']} on {fallback_index} failed: {fb_e}")
                            continue

                    if news_hits:  # 성공하면 중단
                        break

                except Exception as e:
                    logger.warning(f"[ReportService] Fallback strategy {strategy['strategy']} failed: {e}")
                    continue

        # --- Neo4j (검색 Cypher 우선: 파일/환경에서 로드 → 없으면 라벨어웨어 빌드) ---
        cypher = settings.resolve_search_cypher()
        ic(cypher)
        if not cypher:
            keys_map = settings.get_graph_search_keys()
            ic(keys_map)
            cypher = build_label_aware_search_cypher(keys_map)
        ic(cypher)
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
            "hybrid_search_enabled": settings.enable_hybrid_search,
            "bge_m3_host": settings.bge_m3_host if settings.enable_hybrid_search else None,
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
        - 연결 단서(Company/Program/Product 등 이름 샘플)
        """
        label_counter = Counter()
        contracts: List[Dict[str, Any]] = []
        companies: List[str] = []
        programs: List[str] = []
        products: List[str] = []
        events_sample: List[Dict[str, Any]] = []

        # 새로운 스키마에 맞춘 데이터 수집
        companies: List[Dict[str, Any]] = []  # 상장사 정보 확장
        products: List[str] = []  # 새로 추가
        financial_metrics: List[Dict[str, Any]] = []  # 새로 추가
        investments: List[Dict[str, Any]] = []  # 새로 추가

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
                company_info = {
                    "name": n.get("name"),
                    "ticker": n.get("ticker"),
                    "market": n.get("market"),
                    "sector": n.get("sector"),
                    "market_cap": n.get("market_cap"),
                    "is_listed": n.get("is_listed", False),
                }
                if company_info["name"]:
                    companies.append(company_info)

            if "Program" in labels:
                name = n.get("label") or n.get("code")
                if name:
                    programs.append(name)

            if "Product" in labels:  # 새로 추가
                name = n.get("name")
                if name:
                    products.append(name)

            # Product 또는 WeaponSystem (호환성 유지)
            if "Product" in labels or "WeaponSystem" in labels:
                name = n.get("label") or n.get("name") or n.get("productName")
                if name:
                    products.append(name)

            if "FinancialMetric" in labels:  # 새로 추가
                financial_metrics.append({
                    "metric_type": n.get("metric_type"),
                    "amount": n.get("amount"),
                    "currency": n.get("currency"),
                    "period": n.get("period"),
                    "year_over_year": n.get("year_over_year"),
                })

            if "Investment" in labels:  # 새로 추가
                investments.append({
                    "investment_type": n.get("investment_type"),
                    "amount": n.get("amount"),
                    "currency": n.get("currency"),
                    "stake_percentage": n.get("stake_percentage"),
                    "purpose": n.get("purpose"),
                })

            if "Event" in labels:
                events_sample.append({
                    "event_type": n.get("event_type"),
                    "title": n.get("title"),
                    "published_at": _safe_dt(n.get("published_at")),
                    "sentiment": n.get("sentiment"),
                    "confidence": n.get("confidence"),
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

        # 재무지표 분석
        total_revenue = 0.0
        total_operating_profit = 0.0
        for fm in financial_metrics:
            try:
                amount = float(fm.get("amount", 0))
                if fm.get("metric_type") == "revenue":
                    total_revenue += amount
                elif fm.get("metric_type") == "operating_profit":
                    total_operating_profit += amount
            except Exception:
                pass

        # 투자 분석
        total_investment = 0.0
        for inv in investments:
            try:
                if inv.get("amount") is not None:
                    total_investment += float(inv["amount"])
            except Exception:
                pass

        # 상장사 분석 (상장사 우선 정렬)
        listed_companies = [c for c in companies if c.get("is_listed")]
        unlisted_companies = [c for c in companies if not c.get("is_listed")]

        # 시가총액 기준 정렬
        listed_companies.sort(key=lambda x: x.get("market_cap", 0), reverse=True)

        # 회사명 리스트 (상장사 우선)
        company_names = ([c["name"] for c in listed_companies] +
                        [c["name"] for c in unlisted_companies])

        return {
            "label_distribution": label_counter.most_common(),
            "contract_total_amount": total_amt,
            "contract_top": top_contracts,
            "companies_top": [k for k, _ in Counter(company_names).most_common(8)],
            "listed_companies": listed_companies[:5],  # 상위 5개 상장사
            "programs_top": [k for k, _ in Counter(programs).most_common(8)],
            "products_top": [k for k, _ in Counter(products).most_common(8)],
            "weapons_top": [k for k, _ in Counter(products).most_common(8)],  # 호환성 유지
            "products_top": [k for k, _ in Counter(products).most_common(8)],  # 새로 추가
            "events_sample": events_sample[:8],
            "financial_summary": {  # 새로 추가
                "total_revenue": total_revenue,
                "total_operating_profit": total_operating_profit,
                "revenue_companies": len([fm for fm in financial_metrics if fm.get("metric_type") == "revenue"]),
            },
            "investment_summary": {  # 새로 추가
                "total_amount": total_investment,
                "count": len(investments),
                "types": list(set([inv.get("investment_type") for inv in investments if inv.get("investment_type")])),
            },
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
        lines.append("# 📊 상장사 분석 리포트\n")
        lines.append(f"**질의**: `{ctx.query}`  \n"
                     f"**분석 기간**: 최근 {ctx.lookback_days}일  "
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

        # 상장사 정보
        if g["listed_companies"]:
            lines.append("**📈 주요 상장사**")
            for company in g["listed_companies"]:
                name = company["name"]
                ticker = f"({company['ticker']})" if company.get("ticker") else ""
                market = f"[{company['market']}]" if company.get("market") else ""
                market_cap = f" · 시총 {_fmt_ccy(company['market_cap'])}" if company.get("market_cap") else ""
                sector = f" · {company['sector']}" if company.get("sector") else ""
                lines.append(f"- {name} {ticker} {market}{market_cap}{sector}")
            lines.append("")

        # 재무 정보
        financial = g["financial_summary"]
        if financial["total_revenue"] > 0 or financial["total_operating_profit"] > 0:
            lines.append("**💰 재무 정보**")
            if financial["total_revenue"] > 0:
                lines.append(f"- 총 매출: **{_fmt_ccy(financial['total_revenue'])}**")
            if financial["total_operating_profit"] > 0:
                lines.append(f"- 총 영업이익: **{_fmt_ccy(financial['total_operating_profit'])}**")
            if financial["revenue_companies"] > 0:
                lines.append(f"- 실적 발표 기업: {financial['revenue_companies']}개사")
            lines.append("")

        # 투자 정보
        investment = g["investment_summary"]
        if investment["total_amount"] > 0:
            lines.append("**💼 투자 정보**")
            lines.append(f"- 총 투자 규모: **{_fmt_ccy(investment['total_amount'])}**")
            lines.append(f"- 투자 건수: {investment['count']}건")
            if investment["types"]:
                types_str = ", ".join(investment["types"])
                lines.append(f"- 투자 유형: {types_str}")
            lines.append("")

        # 엔터티 Top
        if g["companies_top"]:
            lines.append("**🏢 연관 회사 Top**: " + ", ".join([f"`{x}`" for x in g["companies_top"]]))
        if g["products_top"]:  # 새로 추가
            lines.append("**🛠️ 관련 제품 Top**: " + ", ".join([f"`{x}`" for x in g["products_top"]]))
        if g["programs_top"]:
            lines.append("**🎯 연관 프로그램 Top**: " + ", ".join([f"`{x}`" for x in g["programs_top"]]))
        if g.get("products_top"):  # products_top을 우선 확인
            lines.append("**🛠️ 관련 제품/시스템 Top**: " + ", ".join([f"`{x}`" for x in g["products_top"]]))
        elif g.get("weapons_top"):  # 호환성 유지
            lines.append("**🛠️ 관련 시스템 Top**: " + ", ".join([f"`{x}`" for x in g["weapons_top"]]))
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
        if g.get("products_top"):  # products_top을 우선 확인
            insight_bullets.append(f"핵심 제품/시스템: {', '.join(g['products_top'][:3])}")
        elif g.get("weapons_top"):  # 호환성 유지
            insight_bullets.append(f"핵심 시스템: {', '.join(g['weapons_top'][:3])}")
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

    # ========== 리포트 전용 고급 기능들 ==========

    async def generate_comparative_report(
        self,
        queries: List[str],
        *,
        domain: Optional[str] = None,
        lookback_days: int = 180,
        news_size: int = 20,
        graph_limit: int = 50,
    ) -> Dict[str, Any]:
        """비교 분석 리포트 생성 (리포트만의 고유 기능)"""

        comparisons = []
        all_contexts = []

        for query in queries:
            ctx = await self.fetch_context(
                query=query,
                news_size=news_size,
                graph_limit=graph_limit,
                lookback_days=lookback_days,
                domain=domain,
            )
            all_contexts.append(ctx)

            metrics = {
                "graph": self.compute_graph_metrics(ctx.graph_rows),
                "news": self.compute_news_metrics(ctx.news_hits),
            }

            comparisons.append({
                "query": query,
                "metrics": metrics,
                "contract_total": metrics["graph"]["contract_total_amount"],
                "news_count": metrics["news"]["count"],
                "top_companies": metrics["graph"]["companies_top"][:3],
            })

        # 비교 분석 마크다운 생성
        md_lines = ["# 📊 비교 분석 리포트\n"]
        md_lines.append(f"**분석 대상**: {len(queries)}개 항목")
        md_lines.append(f"**기간**: 최근 {lookback_days}일\n")

        # 요약 테이블
        md_lines.append("## 📈 핵심 지표 비교")
        md_lines.append("| 항목 | 계약 규모 | 뉴스 건수 | 주요 기업 |")
        md_lines.append("|------|-----------|-----------|-----------|")

        for comp in comparisons:
            companies_str = ", ".join(comp["top_companies"]) if comp["top_companies"] else "-"
            md_lines.append(f"| {comp['query']} | {_fmt_ccy(comp['contract_total'])} | {comp['news_count']}건 | {companies_str} |")

        md_lines.append("\n## 📋 상세 분석")

        # 각 항목별 상세 분석
        for i, (comp, ctx) in enumerate(zip(comparisons, all_contexts), 1):
            md_lines.append(f"### {i}. {comp['query']}")

            # 핵심 지표
            graph_metrics = comp["metrics"]["graph"]
            md_lines.append(f"- **계약 총액**: {_fmt_ccy(comp['contract_total'])}")
            md_lines.append(f"- **관련 뉴스**: {comp['news_count']}건")
            md_lines.append(f"- **그래프 노드**: {len(ctx.graph_rows)}개")

            if graph_metrics["label_distribution"]:
                top_labels = graph_metrics["label_distribution"][:3]
                label_str = ", ".join([f"{label}({count})" for label, count in top_labels])
                md_lines.append(f"- **주요 유형**: {label_str}")

            md_lines.append("")

        # 인사이트 및 권장사항
        md_lines.append("## 💡 비교 인사이트")

        # 계약 규모 순위
        sorted_by_contract = sorted(comparisons, key=lambda x: x["contract_total"], reverse=True)
        if sorted_by_contract[0]["contract_total"] > 0:
            md_lines.append(f"- **계약 규모 1위**: `{sorted_by_contract[0]['query']}` ({_fmt_ccy(sorted_by_contract[0]['contract_total'])})")

        # 뉴스 활발도 순위
        sorted_by_news = sorted(comparisons, key=lambda x: x["news_count"], reverse=True)
        md_lines.append(f"- **뉴스 활발도 1위**: `{sorted_by_news[0]['query']}` ({sorted_by_news[0]['news_count']}건)")

        md_lines.append("\n---\n*비교 분석 리포트는 리포트 전용 기능입니다.*")

        return {
            "markdown": "\n".join(md_lines),
            "comparisons": comparisons,
            "contexts": all_contexts,
            "type": "comparative"
        }

    async def generate_trend_analysis(
        self,
        query: str,
        *,
        domain: Optional[str] = None,
        periods: List[int] = [30, 90, 180],  # 기간별 트렌드 분석
    ) -> Dict[str, Any]:
        """시계열 트렌드 분석 리포트 생성"""

        trend_data = []

        for period in periods:
            ctx = await self.fetch_context(
                query=query,
                lookback_days=period,
                news_size=50,
                graph_limit=100,
                domain=domain,
            )

            metrics = {
                "graph": self.compute_graph_metrics(ctx.graph_rows),
                "news": self.compute_news_metrics(ctx.news_hits),
            }

            trend_data.append({
                "period": period,
                "contract_total": metrics["graph"]["contract_total_amount"],
                "news_count": metrics["news"]["count"],
                "graph_nodes": len(ctx.graph_rows),
                "top_companies": metrics["graph"]["companies_top"][:5],
                "events_count": len(metrics["graph"]["events_sample"]),
            })

        # 트렌드 마크다운 생성
        md_lines = ["# 📈 시계열 트렌드 분석\n"]
        md_lines.append(f"**분석 대상**: `{query}`")
        md_lines.append(f"**분석 기간**: {periods}일 구간별 비교\n")

        # 트렌드 테이블
        md_lines.append("## 📊 기간별 추이")
        md_lines.append("| 기간 | 계약 규모 | 뉴스 건수 | 그래프 노드 | 이벤트 수 |")
        md_lines.append("|------|-----------|-----------|-------------|-----------|")

        for trend in trend_data:
            md_lines.append(f"| 최근 {trend['period']}일 | {_fmt_ccy(trend['contract_total'])} | {trend['news_count']}건 | {trend['graph_nodes']}개 | {trend['events_count']}개 |")

        # 트렌드 분석
        md_lines.append("\n## 📋 트렌드 해석")

        if len(trend_data) >= 2:
            recent = trend_data[0]  # 최단기
            longer = trend_data[-1]  # 최장기

            # 계약 트렌드
            if recent["contract_total"] > longer["contract_total"] * 0.5:
                md_lines.append("- **계약 트렌드**: 📈 최근 활발한 계약 활동 감지")
            else:
                md_lines.append("- **계약 트렌드**: 📉 계약 활동이 상대적으로 저조")

            # 뉴스 트렌드
            news_ratio = recent["news_count"] / max(longer["news_count"], 1) * (longer["period"] / recent["period"])
            if news_ratio > 1.2:
                md_lines.append("- **언론 관심**: 📈 최근 언론 관심도 급증")
            elif news_ratio < 0.8:
                md_lines.append("- **언론 관심**: 📉 언론 관심도 하락 추세")
            else:
                md_lines.append("- **언론 관심**: ➡️ 언론 관심도 안정적 유지")

        # 기간별 주요 기업 변화
        md_lines.append("\n## 🏢 기간별 주요 기업")
        for trend in trend_data:
            companies_str = ", ".join(trend["top_companies"]) if trend["top_companies"] else "없음"
            md_lines.append(f"- **최근 {trend['period']}일**: {companies_str}")

        md_lines.append("\n---\n*트렌드 분석은 리포트 전용 고급 기능입니다.*")

        return {
            "markdown": "\n".join(md_lines),
            "trend_data": trend_data,
            "type": "trend_analysis"
        }

    def generate_executive_summary(self, ctx: ReportContext) -> str:
        """경영진 요약 리포트 (간결한 핵심 정보만)"""

        g = self.compute_graph_metrics(ctx.graph_rows)
        n = self.compute_news_metrics(ctx.news_hits)

        lines = ["# 🎯 경영진 요약 리포트\n"]
        lines.append(f"**질의**: `{ctx.query}`")
        lines.append(f"**분석 기간**: 최근 {ctx.lookback_days}일\n")

        # 핵심 숫자
        lines.append("## 📊 핵심 지표")
        lines.append(f"- **총 계약 규모**: {_fmt_ccy(g['contract_total_amount'])}")
        lines.append(f"- **관련 뉴스**: {n['count']}건")
        lines.append(f"- **분석 데이터**: {len(ctx.graph_rows)}개 엔터티")

        # 톱3 요약
        if g["companies_top"]:
            lines.append(f"- **주요 기업**: {', '.join(g['companies_top'][:3])}")

        # 최신 뉴스 1건
        if n["top_news"]:
            latest = n["top_news"][0]
            lines.append(f"- **최신 이슈**: [{latest.get('title', '제목없음')}]({latest.get('url', '')})")

        # 간단한 결론
        lines.append("\n## 💡 핵심 포인트")
        if g["contract_total_amount"] > 1000000000:  # 10억 이상
            lines.append("- 🟢 **대형 계약** 규모로 주목 필요")
        elif g["contract_total_amount"] > 100000000:  # 1억 이상
            lines.append("- 🟡 **중간 규모** 계약 활동")
        else:
            lines.append("- 🔴 **소규모** 또는 계약 정보 제한적")

        if n["count"] > 10:
            lines.append("- 📈 **높은 언론 관심도**")
        elif n["count"] > 5:
            lines.append("- 📊 **보통 언론 관심도**")
        else:
            lines.append("- 📉 **낮은 언론 관심도**")

        lines.append("\n---\n*1분 읽기용 경영진 요약 리포트*")

        return "\n".join(lines)
