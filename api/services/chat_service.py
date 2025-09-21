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

    # 상장사/투자 관련 키워드 힌트 (새 스키마 기반)
    if any(tok in q for tok in ["상장사", "투자", "실적", "재무", "매출", "영업이익"]):
        domain = (domain + " 상장사 투자 실적 재무").strip()

    # 회사명 힌트: 대표 상장사들 (동적 확장 가능)
    company_hints = {
        ("삼성전자", "005930"): "삼성전자 반도체 전자",
        ("현대차", "005380"): "현대차 자동차",
        ("LG", "LG전자"): "LG 전자 가전",
        ("SK", "SK하이닉스"): "SK 반도체 메모리"
    }

    for keywords, hint in company_hints.items():
        if any(keyword in q for keyword in keywords):
            domain = (domain + " " + hint).strip()
            break

    # 중복 공백 정리
    domain = " ".join(domain.split())
    return domain, lookback


# @cache_decorator.cached("keyword_extraction", ttl=3600.0)  # 캐싱 비활성화
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
    
    # 2. 산업별 키워드 추출 (동적 확장 가능)
    for industry_name, keywords in keyword_mappings["industry"].items():
        # 산업별 트리거를 설정에서 가져오거나 기본값 사용
        industry_triggers = {
            "technology": ["IT", "소프트웨어", "기술", "AI", "인공지능"],
            "automotive": ["자동차", "전기차", "배터리", "모빌리티"],
            "semiconductor": ["반도체", "칩", "파운드리", "메모리"],
            "energy": ["에너지", "신재생", "태양광", "풍력", "원전", "원자력"],
            "bio": ["바이오", "제약", "헬스케어", "의료"]
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
        # OpenSearchTool 인스턴스 추가 (임베딩 기능 사용)
        from api.mcp.tools import OpenSearchTool
        self.os_tool = OpenSearchTool(self.os)

    async def _get_context_keywords(self, query: str) -> str:
        """LLM을 통한 동적 키워드 추출 및 확장"""
        try:
            # LLM을 통한 쿼리 분석
            analysis_result = await self._analyze_query_with_llm(query)

            # LLM 분석 결과에서 키워드 추출
            if analysis_result and "keywords" in analysis_result:
                keywords = analysis_result["keywords"]
                # 최대 8개 키워드로 제한
                return " ".join(keywords[:8])
            else:
                # LLM 분석 실패시 폴백 - 기본 키워드 추출
                return self._fallback_keyword_extraction(query)

        except Exception as e:
            print(f"[WARNING] LLM 키워드 분석 실패, 폴백 사용: {e}")
            return self._fallback_keyword_extraction(query)

    async def _analyze_query_with_llm(self, query: str) -> dict:
        """LLM을 통한 쿼리 분석"""
        from langchain_ollama import ChatOllama

        # Ollama LLM 설정 (또는 OpenAI 사용 가능)
        llm = ChatOllama(
            model=settings.ollama_model,  # 또는 다른 모델
            temperature=0.1,
            base_url=settings.get_ollama_base_url()
        )

        prompt = f"""
다음 질문을 분석하여 검색에 최적화된 키워드를 추출해주세요.
---주의사항---
너무 일반적인 단어를 지양합니다

질문: "{query}"

다음 JSON 형식으로 응답해주세요:
{{
    "main_topic": "주요 주제 (예: SMR, 반도체, 2차전지 등)",
    "industry": "산업 분야 (예: 원자력, IT, 자동차 등)",
    "keywords": ["검색용 키워드 리스트 (5-8개)"],
    "companies": ["관련 회사명들 (있다면)"],
    "intent": "질문 의도 (예: 투자종목찾기, 뉴스검색, 기술동향 등)"
}}

중요한 점:
1. 한국 상장사 중심으로 생각하세요
2. 검색에 효과적인 키워드를 선택하세요
3. 약어와 전체 용어를 모두 포함하세요 (예: SMR, 소형모듈원자로)
4. 관련 산업 전반의 키워드를 포함하세요
"""

        try:
            response = await llm.ainvoke(prompt)
            content = response.content.strip()

            # JSON 파싱
            import json
            import re

            # JSON 블록 추출
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                print(f"[WARNING] LLM 응답에서 JSON을 찾을 수 없음: {content}")
                return None

        except Exception as e:
            print(f"[ERROR] LLM 호출 실패: {e}")
            return None

    def _fallback_keyword_extraction(self, query: str) -> str:
        """LLM 실패시 폴백 키워드 추출"""
        import re

        # 기본 토큰화
        words = re.findall(r'\b\w+\b', query)

        # 불용어 제거
        stopwords = ["을", "를", "이", "가", "은", "는", "의", "에", "에서", "으로", "로", "와", "과", "관련", "대한"]
        keywords = [w for w in words if len(w) > 1 and w not in stopwords]

        # 최대 5개로 제한
        return " ".join(keywords[:5])

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
            print("[WARNING] 모든 고급 검색 실패, 원본 쿼리로 폴백")
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

    async def _extract_core_keywords(self, query: str) -> List[str]:
        """LLM 기반 핵심 키워드 추출"""
        try:
            # LLM을 통한 키워드 분석
            keywords_str = await self._get_context_keywords(query)
            keywords_list = keywords_str.split()

            # 중복 제거하고 최대 5개 반환
            unique_keywords = []
            seen = set()
            for keyword in keywords_list:
                if keyword.lower() not in seen:
                    unique_keywords.append(keyword)
                    seen.add(keyword.lower())

            return unique_keywords[:5]

        except Exception as e:
            print(f"[WARNING] 핵심 키워드 추출 실패, 기본 처리: {e}")
            # 폴백: 기본 토큰화
            import re
            words = re.findall(r'\b\w+\b', query)
            stopwords = ["를", "을", "이", "가", "의", "에", "관련", "유망", "종목"]
            return [w for w in words if len(w) > 1 and w not in stopwords][:5]

    async def _search_news_with_ontology(self, query: str, size: int = 5) -> Tuple[List[Dict[str, Any]], float, Optional[str]]:
        """온톨로지 강화 뉴스 검색 (뉴스 + 그래프 데이터 통합)"""
        t0 = time.perf_counter()

        try:
            # 1. 핵심 키워드 추출
            core_keywords = await self._extract_core_keywords(query)
            search_text = " ".join(core_keywords) if core_keywords else query

            print(f"[DEBUG] 원본: '{query}' → 핵심 키워드: {core_keywords}")

            # 2. 온톨로지에서 관련 엔티티 확장
            ontology_entities = await self._get_ontology_expansion(core_keywords)

            # 3. 확장된 키워드로 검색
            expanded_keywords = core_keywords + ontology_entities
            expanded_search_text = " ".join(expanded_keywords[:10])  # 최대 10개로 제한

            print(f"[DEBUG] 온톨로지 확장: {ontology_entities}")

            # 4. 하이브리드 검색 실행
            news_hits, search_time, search_error = await self._execute_hybrid_search(
                original_query=query,
                search_text=expanded_search_text,
                core_keywords=expanded_keywords,
                size=size
            )

            # 5. 온톨로지 관련성 점수로 재정렬
            if news_hits and ontology_entities:
                news_hits = await self._rerank_with_ontology_relevance(news_hits, ontology_entities)

            return news_hits, (time.perf_counter() - t0) * 1000.0, search_error

        except Exception as e:
            print(f"[ERROR] 온톨로지 강화 검색 오류: {e}")
            return [], (time.perf_counter() - t0) * 1000.0, str(e)

    async def _get_ontology_expansion(self, keywords: List[str]) -> List[str]:
        """온톨로지 그래프에서 관련 엔티티 확장"""
        try:
            expansion_entities = []

            for keyword in keywords[:3]:  # 상위 3개 키워드만 처리
                # 그래프에서 관련 엔티티 검색
                graph_rows, _ = await self._graph(keyword)

                for row in graph_rows[:5]:  # 각 키워드당 최대 5개
                    node = row.get("n", {})
                    if isinstance(node, dict):
                        # 회사명 추출
                        if "name" in node:
                            company_name = node["name"]
                            if company_name and company_name not in expansion_entities:
                                expansion_entities.append(company_name)

                        # 제품/기술명 추출
                        if "title" in node:
                            product_name = node["title"]
                            if product_name and len(product_name) > 2 and product_name not in expansion_entities:
                                expansion_entities.append(product_name)

            print(f"[DEBUG] 온톨로지 확장 엔티티: {expansion_entities[:8]}")
            return expansion_entities[:8]  # 최대 8개

        except Exception as e:
            print(f"[WARNING] 온톨로지 확장 실패: {e}")
            return []

    async def _execute_hybrid_search(self, original_query: str, search_text: str, core_keywords: List[str], size: int) -> Tuple[List[Dict[str, Any]], float, Optional[str]]:
        """확장 가능한 하이브리드 검색 실행"""
        try:
            os_index = settings.news_embedding_index

            # 검색 전략 구성 클래스 (향후 분리 가능)
            search_config = self._build_search_config(original_query, search_text, core_keywords)

            # 적응적 쿼리 구성
            bool_clauses = []

            # 1. 다단계 매칭 전략
            for strategy in search_config['matching_strategies']:
                if strategy['enabled']:
                    clause = self._build_matching_clause(
                        query=strategy['query'],
                        fields=strategy['fields'],
                        type=strategy['type'],
                        options=strategy.get('options', {})
                    )
                    if clause:
                        bool_clauses.append(clause)

            # 2. 동적 필터링
            filters = self._build_dynamic_filters(original_query, core_keywords)

            # 3. 벡터 검색 구성
            vector_config = await self._build_vector_config(search_text, size)

            # 하이브리드 쿼리 구성
            body = {
                "query": {
                    "hybrid": {
                        "queries": [
                            {
                                "bool": {
                                    "should": bool_clauses,
                                    "must": filters.get('must', []),
                                    "must_not": filters.get('must_not', []),
                                    "filter": filters.get('filter', []),
                                    "minimum_should_match": 1
                                }
                            },
                            vector_config
                        ]
                    }
                },
                "sort": self._build_sort_strategy(original_query),
                "size": size * 2,  # 더 많은 후보 확보
                "_source": self._get_source_fields(),
                "highlight": self._build_highlight_config()
            }

            # 검색 실행
            result = await self.os.search(index=os_index, query=body, size=size * 2)

            if result and "hits" in result and "hits" in result["hits"]:
                hits = result["hits"]["hits"]
                # 하이라이트 정보 포함하여 포맷팅
                formatted_hits = self._format_with_highlights(hits, size * 2)
                return formatted_hits, 0.0, None
            else:
                return [], 0.0, "검색 결과가 없습니다"

        except Exception as e:
            # print(f"[ERROR] 하이브리드 검색 실행 오류: {e}")
            from api.logging import setup_logging
            logger = setup_logging()
            logger.error(f"[ERROR] 하이브리드 검색 실행 오류: {e}")
            return [], 0.0, str(e)

    def _build_search_config(self, original_query: str, search_text: str, core_keywords: List[str]) -> dict:
        """검색 구성 동적 생성 (확장 가능)"""
        config = {
            'matching_strategies': []
        }

        # 핵심 키워드 정확 매칭
        if core_keywords:
            config['matching_strategies'].append({
                'enabled': True,
                'query': search_text,
                'fields': ["title^4", "content^2", "metadata.title^4", "metadata.content^2"],
                'type': 'multi_match',
                'options': {
                    'type': 'best_fields',
                    'minimum_should_match': '60%',
                    'boost': 2.0
                }
            })

            # 첫 번째 키워드 강조 (와일드카드)
            if len(core_keywords) > 0:
                config['matching_strategies'].append({
                    'enabled': True,
                    'query': core_keywords[0],
                    'fields': ["title"],
                    'type': 'wildcard',
                    'options': {
                        'boost': 1.5
                    }
                })

        # 폴백 전략 (퍼지 매칭)
        config['matching_strategies'].append({
            'enabled': True,
            'query': original_query,
            'fields': ["title^2", "content"],
            'type': 'multi_match',
            'options': {
                'type': 'best_fields',
                'fuzziness': 'AUTO',
                'boost': 1.0
            }
        })

        # 구문 매칭 추가 (정확한 구문 검색)
        if len(original_query.split()) > 1:
            config['matching_strategies'].append({
                'enabled': True,
                'query': original_query,
                'fields': ["title^3", "content"],
                'type': 'match_phrase',
                'options': {
                    'slop': 2,  # 단어 간 거리 허용
                    'boost': 1.5
                }
            })

        return config

    def _build_matching_clause(self, query: str, fields: List[str], type: str, options: dict) -> dict:
        """매칭 절 동적 생성"""
        if type == 'multi_match':
            return {
                "multi_match": {
                    "query": query,
                    "fields": fields,
                    **options
                }
            }
        elif type == 'wildcard':
            field = fields[0] if fields else "title"
            return {
                "wildcard": {
                    field: {
                        "value": f"*{query}*",
                        "boost": options.get('boost', 1.0)
                    }
                }
            }
        elif type == 'match_phrase':
            return {
                "multi_match": {
                    "query": query,
                    "fields": fields,
                    "type": "phrase",
                    "slop": options.get('slop', 0),
                    "boost": options.get('boost', 1.0)
                }
            }
        return {}

    def _build_dynamic_filters(self, query: str, keywords: List[str]) -> dict:
        """동적 필터 구성 (확장 가능)"""
        filters = {
            'must': [],
            'must_not': [],
            'filter': []
        }

        # 시간 범위 필터 (설정 가능)
        if hasattr(settings, 'search_date_range_days'):
            filters['filter'].append({
                "range": {
                    "created_datetime": {
                        "gte": f"now-{settings.search_date_range_days}d"
                    }
                }
            })

        # 품질 필터 (스팸 제거)
        if hasattr(settings, 'exclude_spam_keywords'):
            spam_keywords = settings.exclude_spam_keywords
            if spam_keywords:
                filters['must_not'].append({
                    "terms": {"title": spam_keywords}
                })
                filters['must_not'].append({
                    "terms": {"content": spam_keywords}
                })

        return filters

    async def _build_vector_config(self, search_text: str, size: int) -> dict:
        vector_field_name = getattr(settings, 'vector_field_name', 'vector_field')
        embedded_vector = await self.os_tool.embed_query(search_text)
        return {
            "knn": {
                vector_field_name: {
                    "vector": embedded_vector,
                    "k": size * 3
                }
            }
        }

    def _build_sort_strategy(self, query: str) -> List[dict]:
        """정렬 전략 동적 구성"""
        sort_strategy = []

        # 최신순 우선
        sort_strategy.append({
            "created_datetime": {
                "order": "desc",
                "missing": "_last"
            }
        })

        # 관련도 점수
        sort_strategy.append("_score")

        return sort_strategy

    def _get_source_fields(self) -> dict:
        """반환할 필드 구성"""
        return {
            "includes": [
                "title", "url", "media", "portal",
                "image_url", "created_date", "created_datetime",
                "content", "metadata.title", "metadata.content"
            ]
        }

    def _build_highlight_config(self) -> dict:
        """하이라이트 구성"""
        return {
            "fields": {
                "title": {"number_of_fragments": 0},
                "content": {"fragment_size": 150, "number_of_fragments": 3}
            },
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"]
        }

    def _format_with_highlights(self, hits: List[dict], limit: int) -> List[Dict[str, Any]]:
        """하이라이트 정보 포함 포맷팅"""
        formatted = []
        for hit in hits[:limit]:
            source = hit.get("_source", {})
            highlight = hit.get("highlight", {})

            formatted_hit = {
                "id": hit.get("_id"),
                "title": source.get("title") or source.get("metadata", {}).get("title", "(no title)"),
                "url": source.get("url") or source.get("metadata", {}).get("url"),
                "date": source.get("created_datetime") or source.get("created_date"),
                "media": source.get("media") or source.get("portal", "Unknown"),
                "score": hit.get("_score"),
                "index": hit.get("_index")
            }

            # 하이라이트 정보 추가
            if highlight:
                formatted_hit["highlights"] = {
                    "title": highlight.get("title", []),
                    "content": highlight.get("content", [])
                }

            formatted.append(formatted_hit)

        return formatted

    async def _rerank_with_ontology_relevance(self, news_hits: List[Dict], ontology_entities: List[str]) -> List[Dict]:
        """온톨로지 관련성 기반 재정렬"""
        try:
            for hit in news_hits:
                title = hit.get("title", "").lower()
                content = hit.get("content", "").lower()

                # 온톨로지 엔티티 매칭 점수 계산
                ontology_score = 0
                for entity in ontology_entities:
                    entity_lower = entity.lower()
                    if entity_lower in title:
                        ontology_score += 3  # 제목에 있으면 높은 점수
                    elif entity_lower in content:
                        ontology_score += 1  # 내용에 있으면 기본 점수

                # 기존 점수에 온톨로지 점수 추가
                original_score = hit.get("score", 0)
                hit["ontology_score"] = ontology_score
                hit["combined_score"] = original_score + (ontology_score * 0.5)

            # 통합 점수로 재정렬
            news_hits.sort(key=lambda x: x.get("combined_score", 0), reverse=True)

            print(f"[DEBUG] 온톨로지 재정렬 완료: 평균 온톨로지 점수 {sum(h.get('ontology_score', 0) for h in news_hits)/len(news_hits):.1f}")

            return news_hits

        except Exception as e:
            print(f"[WARNING] 온톨로지 재정렬 실패: {e}")
            return news_hits

    # 기존 메소드를 온톨로지 통합 버전으로 대체
    async def _search_news_simple_hybrid(self, query: str, size: int = 5) -> Tuple[List[Dict[str, Any]], float, Optional[str]]:
        """온톨로지 통합된 하이브리드 검색 (기존 인터페이스 유지)"""
        return await self._search_news_with_ontology(query, size)

    @with_error_handling("opensearch", fallback_value=([], 0.0, "OpenSearch 서비스 사용 불가"))
    @with_retry(max_retries=2, exceptions=(Exception,))
    # @cache_decorator.cached("news_search", ttl=180.0)  # 캐싱 비활성화
    async def _search_news(self, query: str, size: int = 5) -> Tuple[List[Dict[str, Any]], float, Optional[str]]:
        t0 = time.perf_counter()
        err: Optional[str] = None
        try:
            os_index = settings.news_embedding_index
            # 키워드 변환 사용 (원본 질문보다 정확한 키워드 사용)
            search_keywords = self._get_context_keywords(query)
            print(f"[DEBUG] 원본 쿼리: '{query}' → 검색 키워드: '{search_keywords}'")

            body = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": search_keywords,
                                    "fields": ["title^4", "content^2", "text^3", "metadata.title^4", "metadata.content^2"],
                                    "type": "best_fields",
                                    "operator": "and",  # AND 연산으로 정확도 향상
                                    "minimum_should_match": "60%"
                                }
                            },
                            {
                                "query_string": {
                                    "query": search_keywords,
                                    "fields": ["title^3", "content", "metadata.title^3", "metadata.content", "text"],
                                    "default_operator": "AND",  # AND 연산으로 정확도 향상
                                }
                            },
                            {
                                "multi_match": {
                                    "query": search_keywords,
                                    "fields": ["title^2", "content"],
                                    "type": "best_fields",
                                    "operator": "or",
                                }
                            }
                        ],
                        "must": [],
                        "must_not": [],
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
    # @cache_decorator.cached("graph_query", ttl=600.0)  # 캐싱 비활성화
    async def _query_graph(self, query: str, limit: int = 10):
        t0 = time.perf_counter()
        try:
            cypher = settings.resolve_search_cypher()
            if not cypher:
                # 라벨별 키 매핑으로 동적 생성 (백업)
                keys_map = settings.get_graph_search_keys()
                cypher = build_label_aware_search_cypher(keys_map)

            # --- NEW: 새 스키마 파라미터 (domain 제거) ---
            _, lookback_infer = _infer_domain_and_lookback(query)
            lookback_default = settings.neo4j_search_lookback_days

            params = {
                "q": query,
                "limit": limit,
                "lookback_days": lookback_infer or lookback_default or 180,
            }

            rows = await self.neo.query(cypher, params)
            return rows, (time.perf_counter() - t0) * 1000.0, None
        except Exception as e:
            print(f"[ERROR] [/chat] Neo4j label-aware search error: {e}")
            return [], (time.perf_counter() - t0) * 1000.0, str(e)

    @with_error_handling("stock_api", fallback_value=(None, 0.0, "주식 API 서비스 사용 불가"))
    @with_retry(max_retries=2, exceptions=(Exception,))
    # @cache_decorator.cached("stock_price", ttl=60.0)  # 캐싱 비활성화
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
            keywords_str = await self._get_context_keywords(query)
            keywords = keywords_str.split() if keywords_str else [query]
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
                        # 단순 OpenSearch + 벡터 하이브리드 검색 사용
                        hits, ms, err = await self._search_news_simple_hybrid(query, size=5)

                        news_res.update({
                            "hits": hits,
                            "latency_ms": ms,
                            "error": err,
                            "search_strategy": "hybrid_search",
                            "search_confidence": 0.8,
                            "query_used": query
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
                        
                        # 검색 결과가 부족할 때 추가 시도 (핵심 키워드)
                        if not rows or len(rows) < 3:
                            # 일반적인 비즈니스 키워드로 대체
                            core_keywords = [k for k in keywords if k in ["상장사", "투자", "실적", "기업", "매출", "성장"]]
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
- **시장 동향**: 실시간 정보는 별도 확인이 필요합니다
- **투자 참고**: 전문가 상담을 권장합니다
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