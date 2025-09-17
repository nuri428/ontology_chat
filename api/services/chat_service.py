# src/ontology_chat/services/chat_service.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import re
import time
import anyio
# from api.logging import setup_logging
# logger = setup_logging()

from api.config import settings
from api.adapters.mcp_opensearch import OpenSearchMCP
from api.adapters.mcp_neo4j import Neo4jMCP
from api.adapters.mcp_stock import StockMCP
from api.services.cypher_builder import build_label_aware_search_cypher
from api.services.formatters import summarize_graph_rows
from api.services.search_strategy import advanced_search_engine, SearchResult
from api.services.response_formatter import response_formatter
from api.services.cache_manager import cache_decorator, cache_manager
from api.services.error_handler import error_handler, with_retry, with_error_handling

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


@cache_decorator.cached("keyword_extraction", ttl=3600.0)  # 1시간 캐시
def _extract_keywords_for_search(query: str) -> List[str]:
    """개선된 키워드 추출 로직 - 동적 확장, 가중치 기반, 형태소 분석 (컨텍스트 엔지니어링 강화)"""
    from api.config.keyword_mappings import get_all_keyword_mappings
    from api.utils.text_analyzer import enhance_query_with_morphology, suggest_related_terms
    
    q = query.lower()
    keyword_mappings = get_all_keyword_mappings()
    
    # 가중치가 있는 키워드 저장소
    weighted_keywords = []
    
    # 0. 형태소 분석을 통한 쿠리 강화
    morphology_result = enhance_query_with_morphology(query)
    high_importance_words = morphology_result["high_importance_keywords"]
    companies = morphology_result["companies"]
    tech_terms = morphology_result["tech_terms"]
    finance_terms = morphology_result["finance_terms"]
    
    # 형태소 분석 결과로 추가 가중치 부여
    for word in high_importance_words:
        weighted_keywords.append((word, 2.0))
    
    for word in companies:
        weighted_keywords.append((word, 2.5))
        # 연관 용어 추가
        related = suggest_related_terms(word)
        for rel_word in related[:3]:  # 상위 3개만
            weighted_keywords.append((rel_word, 1.8))
    
    for word in tech_terms:
        weighted_keywords.append((word, 2.2))
    
    for word in finance_terms:
        weighted_keywords.append((word, 2.3))
    
    # 1. 도메인별 키워드 추출
    for domain_name, domain_data in keyword_mappings["domain"].items():
        for trigger in domain_data["triggers"]:
            if trigger in q:
                # 확장 키워드 추가 (가중치 순으로 정렬)
                for kw in sorted(domain_data["expansions"], key=lambda x: (x.priority, -x.weight)):
                    weighted_keywords.append((kw.keyword, kw.weight))
                
                # 유사어 추가
                for base_word, synonyms in domain_data.get("synonyms", {}).items():
                    if base_word in q:
                        for syn in synonyms:
                            weighted_keywords.append((syn, 1.2))  # 유사어는 기본 가중치
                break
    
    # 2. 산업별 키워드 추출
    for industry_name, keywords in keyword_mappings["industry"].items():
        industry_triggers = {
            "defense": ["방산", "무기", "국방", "군사"],
            "aerospace": ["항공", "우주", "위성"],
            "nuclear": ["원전", "원자력", "핵"]
        }.get(industry_name, [])
        
        if any(trigger in q for trigger in industry_triggers):
            for kw in keywords:
                weighted_keywords.append((kw.keyword, kw.weight))
    
    # 3. 회사별 키워드 추출
    for company_name, company_data in keyword_mappings["company"].items():
        for trigger in company_data["triggers"]:
            if trigger in q:
                for kw in company_data["expansions"]:
                    weighted_keywords.append((kw.keyword, kw.weight))
                break
    
    # 4. 시간 관련 키워드 추출
    for time_type, time_data in keyword_mappings["time"].items():
        for trigger in time_data["triggers"]:
            if trigger in q:
                for kw in time_data["expansions"]:
                    weighted_keywords.append((kw.keyword, kw.weight))
                break
    
    # 5. 지역별 키워드 추출
    for region_name, region_data in keyword_mappings["region"].items():
        for trigger in region_data["triggers"]:
            if trigger in q:
                for kw in region_data["expansions"]:
                    weighted_keywords.append((kw.keyword, kw.weight))
                break
    
    # 6. 가중치 기반 정렬 및 중복 제거
    keyword_weights = {}
    for keyword, weight in weighted_keywords:
        if keyword not in keyword_weights:
            keyword_weights[keyword] = weight
        else:
            # 중복 키워드는 최대 가중치 사용
            keyword_weights[keyword] = max(keyword_weights[keyword], weight)
    
    # 가중치 순으로 정렬
    sorted_keywords = sorted(keyword_weights.items(), key=lambda x: -x[1])
    
    # 7. 키워드가 부족하면 원본 질문에서 추가 추출
    if len(sorted_keywords) < 5:
        stopwords = keyword_mappings["stopwords"]
        # 형탄소 분석 결과를 활용한 추가 키워드
        key_phrases = morphology_result["key_phrases"]
        for phrase, importance in key_phrases:
            if phrase not in keyword_weights and importance > 1.0:
                sorted_keywords.append((phrase, importance * 0.8))  # 약간 낮은 가중치
        
        # 여전히 부족하면 기본 처리
        if len(sorted_keywords) < 5:
            words = [w for w in q.split() if len(w) > 1 and w not in stopwords]
            for word in words:
                if word not in keyword_weights:
                    sorted_keywords.append((word, 0.5))
    
    # 8. 최종 키워드 리스트 반환 (상위 15개)
    final_keywords = [kw[0] for kw in sorted_keywords[:15]]
    
    # 로그로 분석 결과 추가 (개발용)
    # logger.info(f"형태소 분석 결과: 중요 키워드={high_importance_words}, 회사={companies}")
    
    return final_keywords


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
        
        # 제목 추출 (여러 필드에서 시도)
        title = (
            src.get("title") or 
            meta.get("title") or 
            src.get("headline") or 
            "(no title)"
        )
        
        # URL 추출
        url = (
            src.get("url") or 
            meta.get("url") or 
            src.get("link") or 
            src.get("article_url")
        )
        
        # 날짜 추출 (여러 필드에서 시도)
        date = (
            src.get("created_datetime") or
            src.get("created_date") or
            src.get("published_at") or
            src.get("publish_date") or
            meta.get("created_datetime") or
            meta.get("created_date") or
            meta.get("published_at")
        )
        
        # 미디어 정보 추출
        media = src.get("media") or meta.get("media") or src.get("source") or "Unknown"
        
        out.append(
            {
                "id": h.get("_id"),
                "title": title,
                "url": url,
                "date": date,
                "media": media,
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

    async def _search_news_advanced(
        self, 
        original_query: str, 
        keywords: List[str], 
        size: int = 5
    ) -> Tuple[SearchResult, float, Optional[str]]:
        """고급 다단계 뉴스 검색"""
        t0 = time.perf_counter()
        
        # 1. 도메인 감지 및 엔티티 추출
        domains = advanced_search_engine.detect_query_domain(original_query)
        entities = advanced_search_engine.extract_entities(original_query)
        
        print(f"[INFO] 검색 도메인: {domains}, 추출 엔티티: {entities}")
        
        # 2. 검색 전략 생성
        search_strategies = advanced_search_engine.build_enhanced_queries(
            original_query, keywords, domains, entities
        )
        
        best_result = None
        best_quality = 0.0
        
        # 3. 전략별 순차 검색
        for strategy in search_strategies[:4]:  # 상위 4개 전략만 시도
            try:
                print(f"[INFO] 검색 전략 시도: {strategy.name} - {strategy.query}")
                
                hits, ms, err = await self._search_news(strategy.query, size)
                
                if hits:
                    # 품질 평가
                    quality = advanced_search_engine.evaluate_search_quality(
                        hits, original_query, strategy
                    )
                    
                    print(f"[INFO] 전략 {strategy.name} 품질: {quality:.2f}, 결과: {len(hits)}건")
                    
                    if quality > best_quality:
                        best_quality = quality
                        best_result = SearchResult(
                            hits=hits,
                            query_used=strategy.query,
                            strategy=strategy.name,
                            confidence=quality,
                            latency_ms=ms,
                            total_found=len(hits)
                        )
                    
                    # 품질이 충분히 높으면 조기 종료
                    if quality > 0.8:
                        break
                        
            except Exception as e:
                print(f"[WARNING] 검색 전략 {strategy.name} 실패: {e}")
                continue
        
        # 4. 결과 반환
        total_time = (time.perf_counter() - t0) * 1000.0
        
        if best_result:
            print(f"[INFO] 최종 선택: {best_result.strategy} (품질: {best_result.confidence:.2f})")
            return best_result, total_time, None
        else:
            # 완전 폴백: 원본 쿼리로 재시도
            print(f"[WARNING] 모든 고급 검색 실패, 원본 쿼리로 폴백")
            hits, ms, err = await self._search_news(original_query, size)
            
            fallback_result = SearchResult(
                hits=hits or [],
                query_used=original_query,
                strategy="fallback_original",
                confidence=0.3,
                latency_ms=ms,
                total_found=len(hits) if hits else 0
            )
            
            return fallback_result, total_time, err

    @with_error_handling("opensearch", fallback_value=([], 0.0, "OpenSearch 서비스 사용 불가"))
    @with_retry(max_retries=2, exceptions=(Exception,))
    @cache_decorator.cached("news_search", ttl=180.0)  # 3분 캐시
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
                                    "operator": "or",
                                }
                            },
                            {
                                "query_string": {
                                    "query": query,
                                    "fields": ["title^3", "content", "metadata.title^3", "metadata.content", "text"],
                                    "default_operator": "OR",
                                }
                            },
                            {
                                "multi_match": {
                                    "query": "한화 로봇 방산 무기 수출 국방 K-방산",
                                    "fields": ["title^2", "content"],
                                    "type": "best_fields",
                                    "operator": "or",
                                }
                            },
                            {
                                "multi_match": {
                                    "query": "한화시스템 한화에어로스페이스 한화디펜스",
                                    "fields": ["title^3", "content"],
                                    "type": "best_fields",
                                    "operator": "or",
                                }
                            }
                        ],
                        "must_not": [
                            {
                                "terms": {
                                    "title": ["뷰티", "K열풍", "피부과", "미용", "화장품", "스킨케어"]
                                }
                            },
                            {
                                "terms": {
                                    "content": ["뷰티", "K열풍", "피부과", "미용", "화장품", "스킨케어"]
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
            # OpenSearch 직접 호출 (복잡한 쿼리 지원)
            result = await self.os.search(
                index=os_index,
                query=body,
                size=size
            )
            
            if result and result.get("hits"):
                hits = result["hits"].get("hits", [])
                out = _format_sources(hits)
                return out, (time.perf_counter() - t0) * 1000.0, None
            else:
                return [], (time.perf_counter() - t0) * 1000.0, "No results found"
                
        except Exception as e:
            print(f"[ERROR] [/chat] OpenSearch error: {e}")
            err = str(e)
            return [], (time.perf_counter() - t0) * 1000.0, err

    @with_error_handling("neo4j", fallback_value=([], 0.0, "Neo4j 서비스 사용 불가"))
    @with_retry(max_retries=2, exceptions=(Exception,))
    @cache_decorator.cached("graph_query", ttl=600.0)  # 10분 캐시
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
            print(f"[ERROR] [/chat] Neo4j label-aware search error: {e}")
            return [], (time.perf_counter() - t0) * 1000.0, str(e)

    @with_error_handling("stock_api", fallback_value=(None, 0.0, "주식 API 서비스 사용 불가"))
    @with_retry(max_retries=2, exceptions=(Exception,))
    @cache_decorator.cached("stock_price", ttl=60.0)  # 1분 캐시
    async def _get_stock(self, symbol: Optional[str]) -> Tuple[Optional[Dict[str, Any]], float, Optional[str]]:
        t0 = time.perf_counter()
        if not symbol:
            return None, 0.0, None
        try:
            price = await self.st.get_price(symbol)
            return price, (time.perf_counter() - t0) * 1000.0, None
        except Exception as e:
            print(f"[ERROR] [/chat] Stock error: {e}")
            return None, (time.perf_counter() - t0) * 1000.0, str(e)

    async def _compose_answer(
        self,
        query: str,
        news_hits: List[Dict[str, Any]],
        graph_rows: List[Dict[str, Any]],
        stock: Optional[Dict[str, Any]],
        search_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """새로운 포맷터를 사용한 답변 생성"""
        
        # LLM 기반 컨텍스트 인사이트 생성 (임시 비활성화)
        insights_content = None
        # try:
        #     from api.services.context_insight_generator import insight_generator
        #     
        #     # 비동기로 인사이트 생성 요청
        #     insight_result = await insight_generator.generate_insights(
        #         query=query,
        #         news_hits=news_hits,
        #         graph_summary=summarize_graph_rows(graph_rows, max_each=5) if graph_rows else None,
        #         stock_info=stock
        #     )
        #     
        #     # 인사이트가 생성되면 포맷팅
        #     if insight_result.insights:
        #         insights_content = insight_generator.format_insights_for_display(insight_result)
        #         logger.info(f"동적 인사이트 생성 성공: {len(insight_result.insights)}개, 신뢰도: {insight_result.confidence:.2f}")
        #     else:
        #         logger.warning("동적 인사이트 생성 실패")
        #         
        # except Exception as e:
        #     logger.error(f"인사이트 생성 오류: {e}")
        
        # 새로운 포맷터로 종합 답변 생성
        return response_formatter.format_comprehensive_answer(
            query=query,
            news_hits=news_hits,
            graph_rows=graph_rows, 
            stock=stock,
            insights=insights_content,
            search_meta=search_meta
        )

    async def generate_answer(self, query: str) -> Dict[str, Any]:
        """메인 답변 생성 메서드 - 강화된 오류 처리 포함"""
        start_time = time.time()
        services_attempted = []
        try:
            symbol = _detect_symbol(query)
            
            # 기존 키워드 추출 사용 (LLM은 인사이트 생성에서만 사용)
            keywords = _extract_keywords_for_search(query)
            search_query = " ".join(keywords) if keywords else query
            
            print(f"[INFO] 원본 질문: {query}")
            print(f"[INFO] 추출된 키워드: {keywords}")
            print(f"[INFO] 검색 쿼리: {search_query}")

            async with anyio.create_task_group() as tg:
                news_res: Dict[str, Any] = {}
                graph_res: Dict[str, Any] = {}
                stock_res: Dict[str, Any] = {}

                async def _news():
                    try:
                        services_attempted.append("opensearch")
                        # 고급 다단계 검색 사용
                        search_result, ms, err = await self._search_news_advanced(query, keywords, size=5)
                        
                        news_res.update({
                            "hits": search_result.hits, 
                            "latency_ms": ms, 
                            "error": err,
                            "search_strategy": search_result.strategy,
                            "search_confidence": search_result.confidence,
                            "query_used": search_result.query_used
                        })
                        
                        if not err:
                            error_handler.record_success("opensearch")
                    except Exception as e:
                        error_handler.record_error("opensearch", e)
                        # 폴백 뉴스 데이터
                        news_res.update({
                            "hits": [], 
                            "latency_ms": 0.0, 
                            "error": f"뉴스 검색 실패: {str(e)}",
                            "search_strategy": "fallback",
                            "search_confidence": 0.1,
                            "query_used": query
                        })

                async def _graph():
                    try:
                        services_attempted.append("neo4j")
                        # 단계별 그래프 검색 전략 (오류 처리는 메서드 데코레이터에서)
                        rows, ms, err = await self._query_graph(search_query, limit=30)
                        
                        # 검색 결과가 부족할 때 추가 시도
                        if not rows or len(rows) < 3:
                            core_keywords = [k for k in keywords if k in ["지상무기", "무기", "방산", "한화", "수출", "해외"]]
                            if core_keywords:
                                core_query = " ".join(core_keywords)
                                rows2, ms2, err2 = await self._query_graph(core_query, limit=30)
                                if len(rows2) > len(rows):
                                    rows, ms, err = rows2, ms2, err2
                        
                        graph_res.update({"rows": rows, "latency_ms": ms, "error": err})
                        
                        if not err:
                            error_handler.record_success("neo4j")
                    except Exception as e:
                        error_handler.record_error("neo4j", e)
                        graph_res.update({"rows": [], "latency_ms": 0.0, "error": f"그래프 검색 실패: {str(e)}"})

                async def _stock():
                    try:
                        services_attempted.append("stock_api")
                        price, ms, err = await self._get_stock(symbol)
                        stock_res.update({"price": price, "latency_ms": ms, "error": err})
                        
                        if not err:
                            error_handler.record_success("stock_api")
                    except Exception as e:
                        error_handler.record_error("stock_api", e)
                        stock_res.update({"price": None, "latency_ms": 0.0, "error": f"주가 조회 실패: {str(e)}"})

                tg.start_soon(_news)
                tg.start_soon(_graph)
                tg.start_soon(_stock)

            # 검색 메타데이터 준비
            search_meta = {
                "search_strategy": news_res.get("search_strategy"),
                "search_confidence": news_res.get("search_confidence"),
                "query_used": news_res.get("query_used")
            }

            # 답변 생성 (오류 발생 시에도 최대한 정보 제공)
            answer = await self._compose_answer(
                query=query,
                news_hits=news_res.get("hits") or [],
                graph_rows=graph_res.get("rows") or [],
                stock=stock_res.get("price"),
                search_meta=search_meta
            )

            # 전체 처리 시간 계산
            total_time = (time.time() - start_time) * 1000.0
            
            # 메타데이터 구성
            meta = {
                "orchestrator": "v0_enhanced",
                "total_latency_ms": round(total_time, 2),
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
                "services_attempted": services_attempted,
                "system_health": error_handler.get_health_report(),
                "symbol_detected": symbol,
                "indices": {
                    "news_bulk_index": settings.news_bulk_index,
                    "news_embedding_index": settings.news_embedding_index,
                },
                "database": settings.neo4j_database,
            }

            sources = news_res.get("hits") or []

            result = {
                "query": query,
                "answer": answer,
                "sources": sources,
                "graph_samples": graph_res.get("rows")[:3] if graph_res.get("rows") else [],
                "graph_summary": summarize_graph_rows(graph_res.get("rows") or [], max_each=5) if graph_res.get("rows") else None,
                "stock": stock_res.get("price"),
                "meta": meta,
            }
            
            print(f"[INFO] 답변 생성 완료: {total_time:.2f}ms, 서비스: {services_attempted}")
            return result
            
        except Exception as e:
            # 최종 폴백: 시스템 전체 오류 시에도 기본 응답 제공
            error_handler.record_error("system", e, context={"query": query})
            total_time = (time.time() - start_time) * 1000.0
            
            print(f"[ERROR] 전체 시스템 오류: {e}")
            
            # 최소한의 응답 생성
            fallback_answer = f"""## ⚠️ 시스템 일시 장애

죄송합니다. 현재 시스템에 일시적인 문제가 발생했습니다.

**질의**: {query}

### 📊 일반적인 시장 정보
- **방산 산업**: K-방산 수출 증가 추세로 관련 기업들이 주목받고 있습니다
- **투자 참고**: 실시간 정보는 별도 확인이 필요합니다
- **서비스 상태**: 복구 중이며 곧 정상 서비스됩니다

### 🔧 추천 조치
- 잠시 후 다시 시도해 주세요
- 더 구체적인 키워드로 질의해 보세요
- 시스템 관리자에게 문의하세요

**오류 ID**: {int(time.time())}
"""

            return {
                "query": query,
                "answer": fallback_answer,
                "sources": [],
                "graph_samples": [],
                "graph_summary": None,
                "stock": None,
                "meta": {
                    "orchestrator": "fallback",
                    "total_latency_ms": round(total_time, 2),
                    "error": str(e),
                    "services_attempted": services_attempted,
                    "system_health": error_handler.get_health_report()
                }
            }