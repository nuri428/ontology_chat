# src/ontology_chat/services/langgraph_report_service.py
"""
LangGraph 기반 고급 컨텍스트 엔지니어링 리포트 생성 서비스

주요 특징:
1. 다단계 정보 수집 및 검증
2. 컨텍스트 간 관계 분석
3. 동적 분석 깊이 조절
4. 품질 기반 재시도 메커니즘
5. 구조화된 인사이트 생성
"""

from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from dataclasses import dataclass
from enum import Enum
import json

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaLLM

from api.logging import setup_logging
from api.adapters.mcp_neo4j import Neo4jMCP
from api.adapters.mcp_opensearch import OpenSearchMCP
from api.adapters.mcp_stock import StockMCP
from api.adapters.ollama_embedding import OllamaEmbeddingMCP
from api.services.report_service import ReportService
from api.config import settings
import traceback 
from icecream import ic
logger = setup_logging()

# ========== 상태 정의 ==========

class AnalysisDepth(Enum):
    SHALLOW = "shallow"      # 기본 정보만
    STANDARD = "standard"    # 일반적 분석
    DEEP = "deep"           # 심화 분석
    COMPREHENSIVE = "comprehensive"  # 종합 분석

class ReportQuality(Enum):
    POOR = "poor"           # 재시도 필요
    ACCEPTABLE = "acceptable"  # 최소 기준 충족
    GOOD = "good"           # 양호
    EXCELLENT = "excellent"    # 우수

@dataclass
class ContextItem:
    """컨텍스트 정보 단위"""
    source: str          # 출처 (neo4j, opensearch, stock, llm)
    type: str           # 유형 (news, contract, company, analysis)
    content: Dict[str, Any]  # 실제 데이터
    confidence: float   # 신뢰도 (0.0-1.0)
    relevance: float    # 관련성 (0.0-1.0)
    timestamp: str      # 수집 시간

class LangGraphReportState(TypedDict):
    """LangGraph 상태 정의"""
    # 입력 정보
    query: str
    domain: Optional[str]
    lookback_days: int
    analysis_depth: AnalysisDepth

    # 수집된 컨텍스트
    contexts: List[ContextItem]

    # 분석 결과
    insights: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]

    # 리포트 생성
    report_sections: Dict[str, str]
    final_report: str

    # 품질 관리
    quality_score: float
    quality_level: ReportQuality
    retry_count: int

    # 메타데이터
    execution_log: List[str]
    processing_time: float

# ========== LangGraph 노드 함수들 ==========

class LangGraphReportEngine:
    """LangGraph 기반 리포트 생성 엔진"""

    def __init__(self):
        self.neo4j = Neo4jMCP()
        self.opensearch = OpenSearchMCP()
        self.stock = StockMCP()
        self.report_service = ReportService()

        # Ollama 임베딩 클라이언트 초기화 (직접 벡터 유사도 계산용)
        try:
            self.embedding_client = OllamaEmbeddingMCP()
            logger.info(f"[LangGraph] Ollama 임베딩 클라이언트 초기화 완료")
        except Exception as e:
            logger.warning(f"Ollama 임베딩 초기화 실패, 키워드 검색만 사용: {e}")
            self.embedding_client = None

        # LLM 초기화 (비동기 호환)
        self.llm = OllamaLLM(
            model=settings.ollama_model,
            base_url=settings.get_ollama_base_url(),
            temperature=0.1,
            num_predict=4000
        )
        logger.info(f"[LangGraph] LLM 초기화 완료: {settings.ollama_model} @ {settings.get_ollama_base_url()}")

        # LangGraph 워크플로우 구성
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""

        workflow = StateGraph(LangGraphReportState)

        # 노드 추가
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("collect_parallel_data", self._collect_parallel_data)
        workflow.add_node("cross_validate_contexts", self._cross_validate_contexts)
        workflow.add_node("generate_insights", self._generate_insights)
        workflow.add_node("analyze_relationships", self._analyze_relationships)
        workflow.add_node("synthesize_report", self._synthesize_report)
        workflow.add_node("quality_check", self._quality_check)
        workflow.add_node("enhance_report", self._enhance_report)

        # 워크플로우 연결
        workflow.set_entry_point("analyze_query")

        # 병렬 데이터 수집을 위한 개선된 연결
        workflow.add_edge("analyze_query", "collect_parallel_data")
        workflow.add_edge("collect_parallel_data", "cross_validate_contexts")
        workflow.add_edge("cross_validate_contexts", "generate_insights")
        workflow.add_edge("generate_insights", "analyze_relationships")
        workflow.add_edge("analyze_relationships", "synthesize_report")
        workflow.add_edge("synthesize_report", "quality_check")

        # 조건부 분기
        workflow.add_conditional_edges(
            "quality_check",
            self._should_enhance_report,
            {
                "enhance": "enhance_report",
                "complete": END
            }
        )
        workflow.add_edge("enhance_report", "quality_check")

        return workflow.compile()

    async def _analyze_query(self, state: LangGraphReportState) -> LangGraphReportState:
        """1단계: 쿼리 분석 및 분석 전략 수립"""

        state["execution_log"].append("🔍 쿼리 분석 시작")

        # 개선된 단계별 쿼리 분석
        try:
            # 1단계: 키워드 추출
            keyword_prompt = f"다음 질의에서 핵심 키워드 3-5개를 추출하세요. 질의: '{state['query']}'. 응답 형식: ['키워드1', '키워드2', '키워드3']"
            keyword_response = await self._llm_invoke(keyword_prompt)

            # 2단계: 분석 복잡도 판단
            complexity_prompt = f"다음 질의의 분석 복잡도를 판단하세요. 질의: '{state['query']}'. 응답: shallow, standard, deep, comprehensive 중 하나만"
            complexity_response = await self._llm_invoke(complexity_prompt)

            # 안전한 파싱
            keywords = self._safe_parse_keywords(keyword_response)
            complexity = self._safe_parse_complexity(complexity_response)

            state["analysis_depth"] = AnalysisDepth(complexity)
            state["query_analysis"] = {
                "keywords": keywords,
                "complexity": complexity,
                "focus_areas": [state['query']]  # 기본값
            }

            state["execution_log"].append(f"✅ 분석 깊이 설정: {complexity}, 키워드: {keywords}")

        except Exception as e:
            logger.warning(f"쿼리 분석 중 오류: {e}")
            state["analysis_depth"] = AnalysisDepth.STANDARD
            state["query_analysis"] = {"keywords": [state['query']], "complexity": "standard"}
            state["execution_log"].append("⚠️ 기본 분석 모드로 설정")

        return state

    async def _collect_parallel_data(self, state: LangGraphReportState) -> LangGraphReportState:
        """2단계: 병렬 데이터 수집 (성능 최적화)"""

        state["execution_log"].append("🚀 병렬 데이터 수집 시작")

        try:
            # 병렬로 실행할 작업들
            tasks = []

            # 1. 구조화된 데이터 수집 (Neo4j, Stock)
            tasks.append(self._collect_structured_data_async(state))

            # 2. 비구조화된 데이터 수집 (OpenSearch)
            tasks.append(self._collect_unstructured_data_async(state))

            # 병렬 실행
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 통합
            structured_contexts = []
            unstructured_contexts = []

            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"병렬 데이터 수집 중 오류: {result}")
                    continue

                if result.get("type") == "structured":
                    structured_contexts.extend(result.get("contexts", []))
                elif result.get("type") == "unstructured":
                    unstructured_contexts.extend(result.get("contexts", []))

            # 상태에 통합
            state["contexts"].extend(structured_contexts)
            state["contexts"].extend(unstructured_contexts)

            state["execution_log"].append(f"✅ 병렬 데이터 수집 완료: 구조화({len(structured_contexts)}) + 비구조화({len(unstructured_contexts)})")

        except Exception as e:
            logger.error(f"병렬 데이터 수집 실패: {e}")
            state["execution_log"].append(f"❌ 병렬 데이터 수집 실패: {e}")

        return state

    async def _collect_structured_data_async(self, state: LangGraphReportState) -> Dict[str, Any]:
        """구조화된 데이터 비동기 수집"""
        contexts = []

        try:
            # Neo4j 데이터 수집
            graph_context = await self.report_service.fetch_context(
                query=state["query"],
                lookback_days=state["lookback_days"],
                domain=state.get("domain"),
                graph_limit=100
            )

            # 그래프 데이터를 ContextItem으로 변환
            for row in graph_context.graph_rows:
                context_item = ContextItem(
                    source="neo4j",
                    type=self._determine_graph_type(row),
                    content=row,
                    confidence=0.8,
                    relevance=self._calculate_graph_relevance(row, state["query"]),
                    timestamp=str(asyncio.get_event_loop().time())
                )
                contexts.append(context_item)

            # 주가 데이터 수집 (상장사의 경우)
            await self._collect_stock_data(state, contexts)

            return {"type": "structured", "contexts": contexts}

        except Exception as e:
            logger.error(f"구조화된 데이터 수집 오류: {e}")
            return {"type": "structured", "contexts": []}

    async def _collect_unstructured_data_async(self, state: LangGraphReportState) -> Dict[str, Any]:
        """비구조화된 데이터 비동기 수집"""
        contexts = []

        try:
            # 하이브리드 검색 사용 (Ollama 임베딩 + 키워드)
            news_hits = await self._langgraph_hybrid_search(
                query=state["query"],
                lookback_days=state["lookback_days"],
                size=50
            )

            # 뉴스 데이터를 ContextItem으로 변환
            for hit in news_hits:
                source_data = hit.get("_source", {})
                context_item = ContextItem(
                    source="opensearch",
                    type="news",
                    content=source_data,
                    confidence=min(hit.get("_score", 0) / 10.0, 1.0),
                    relevance=self._calculate_news_relevance(source_data, state["query"]),
                    timestamp=str(asyncio.get_event_loop().time())
                )
                contexts.append(context_item)

            return {"type": "unstructured", "contexts": contexts}

        except Exception as e:
            logger.error(f"비구조화된 데이터 수집 오류: {e}")
            return {"type": "unstructured", "contexts": []}

    async def _collect_structured_data(self, state: LangGraphReportState) -> LangGraphReportState:
        """2단계: 구조화된 데이터 수집 (Neo4j, Stock)"""

        state["execution_log"].append("📊 구조화된 데이터 수집 시작")

        try:
            # Neo4j 데이터 수집
            graph_context = await self.report_service.fetch_context(
                query=state["query"],
                lookback_days=state["lookback_days"],
                domain=state.get("domain"),
                graph_limit=100
            )

            # 그래프 데이터를 ContextItem으로 변환
            for row in graph_context.graph_rows:
                context_item = ContextItem(
                    source="neo4j",
                    type=self._determine_graph_type(row),
                    content=row,
                    confidence=0.9,  # 구조화된 데이터는 높은 신뢰도
                    relevance=self._calculate_relevance(row, state["query"]),
                    timestamp=str(asyncio.get_event_loop().time())
                )
                state["contexts"].append(context_item)

            # 주가 데이터 수집 (종목이 있는 경우)
            if "symbol" in state and state["symbol"]:
                try:
                    stock_data = await self.stock.get_price(state["symbol"])
                    stock_context = ContextItem(
                        source="stock",
                        type="price_data",
                        content=stock_data,
                        confidence=0.95,
                        relevance=0.8,
                        timestamp=str(asyncio.get_event_loop().time())
                    )
                    state["contexts"].append(stock_context)
                except Exception as e:
                    logger.warning(f"주가 데이터 수집 실패: {e}")

            state["execution_log"].append(f"✅ 구조화된 데이터 {len([c for c in state['contexts'] if c.source in ['neo4j', 'stock']])}개 수집")

        except Exception as e:
            logger.error(f"구조화된 데이터 수집 오류: {e}")
            state["execution_log"].append(f"❌ 구조화된 데이터 수집 실패: {e}")

        return state

    async def _collect_unstructured_data(self, state: LangGraphReportState) -> LangGraphReportState:
        """3단계: 비구조화된 데이터 수집 (하이브리드 검색)"""

        state["execution_log"].append("📰 하이브리드 검색 기반 데이터 수집 시작")

        try:
            # 하이브리드 검색 사용 (Ollama 임베딩 + 키워드)
            news_hits = await self._langgraph_hybrid_search(
                query=state["query"],
                lookback_days=state["lookback_days"],
                size=50
            )
            state["execution_log"].append(f"✅ 하이브리드 검색 완료: {len(news_hits)}건")

            # 뉴스 데이터를 ContextItem으로 변환
            for hit in news_hits:
                source_data = hit.get("_source", {})
                context_item = ContextItem(
                    source="opensearch",
                    type="news",
                    content=source_data,
                    confidence=min(hit.get("_score", 0) / 10.0, 1.0),
                    relevance=self._calculate_news_relevance(source_data, state["query"]),
                    timestamp=str(asyncio.get_event_loop().time())
                )
                state["contexts"].append(context_item)

            # 심화 분석이 필요한 경우 추가 검색
            if state["analysis_depth"] in [AnalysisDepth.DEEP, AnalysisDepth.COMPREHENSIVE]:
                # 확장된 키워드로 추가 검색
                extended_queries = await self._generate_extended_queries(state["query"])

                for ext_query in extended_queries:
                    try:
                        # 확장 쿼리도 하이브리드 검색 사용
                        ext_hits = await self._langgraph_hybrid_search(
                            query=ext_query,
                            lookback_days=state["lookback_days"],
                            size=20
                        )

                        for hit in ext_hits:
                            source_data = hit.get("_source", {})
                            context_item = ContextItem(
                                source="opensearch_extended",
                                type="news_extended",
                                content=source_data,
                                confidence=min(hit.get("_score", 0) / 15.0, 0.8),  # 확장 검색은 신뢰도 약간 낮음
                                relevance=self._calculate_news_relevance(source_data, ext_query),
                                timestamp=str(asyncio.get_event_loop().time())
                            )
                            state["contexts"].append(context_item)
                    except Exception as e:
                        logger.warning(f"확장 검색 실패 ({ext_query}): {e}")

            state["execution_log"].append(f"✅ 비구조화된 데이터 {len([c for c in state['contexts'] if c.source.startswith('opensearch')])}개 수집")

        except Exception as e:
            logger.error(f"비구조화된 데이터 수집 오류: {e}")
            state["execution_log"].append(f"❌ 비구조화된 데이터 수집 실패: {e}")

        return state

    async def _cross_validate_contexts(self, state: LangGraphReportState) -> LangGraphReportState:
        """4단계: 컨텍스트 간 교차 검증 및 필터링"""

        state["execution_log"].append("🔗 컨텍스트 교차 검증 시작")

        # 중복 제거
        unique_contexts = []
        seen_contents = set()

        for context in state["contexts"]:
            # 컨텐츠 해시 생성 (단순화)
            content_hash = hash(str(context.content))

            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_contexts.append(context)

        # 신뢰도 및 관련성 기반 필터링
        high_quality_contexts = [
            ctx for ctx in unique_contexts
            if ctx.confidence > 0.3 and ctx.relevance > 0.2
        ]

        # 상위 컨텍스트만 유지 (분석 깊이에 따라)
        max_contexts = {
            AnalysisDepth.SHALLOW: 20,
            AnalysisDepth.STANDARD: 40,
            AnalysisDepth.DEEP: 80,
            AnalysisDepth.COMPREHENSIVE: 150
        }

        # 품질 점수로 정렬 후 상위 N개 선택
        sorted_contexts = sorted(
            high_quality_contexts,
            key=lambda x: x.confidence * x.relevance,
            reverse=True
        )

        state["contexts"] = sorted_contexts[:max_contexts[state["analysis_depth"]]]
        state["execution_log"].append(f"✅ {len(state['contexts'])}개 고품질 컨텍스트 선별")

        return state

    async def _generate_insights(self, state: LangGraphReportState) -> LangGraphReportState:
        """5단계: LLM 기반 인사이트 생성"""

        state["execution_log"].append("💡 인사이트 생성 시작")

        # 컨텍스트를 유형별로 그룹핑
        context_groups = {}
        for ctx in state["contexts"]:
            if ctx.type not in context_groups:
                context_groups[ctx.type] = []
            context_groups[ctx.type].append(ctx)

        insights = []

        for ctx_type, contexts in context_groups.items():
            if len(contexts) < 2:  # 최소 2개 이상 있어야 인사이트 생성
                continue

            # 상장사 특화 인사이트 생성
            data_summary = self._summarize_context_data(contexts[:3])  # 상위 3개만
            insight_prompt = self._generate_sector_specific_insight_prompt(ctx_type, state['query'], data_summary)

            try:
                response = await self._llm_invoke(insight_prompt)

                insight = {
                    "type": ctx_type,
                    "content": response,
                    "source_count": len(contexts),
                    "confidence": sum(ctx.confidence for ctx in contexts) / len(contexts),
                    "timestamp": str(asyncio.get_event_loop().time())
                }
                insights.append(insight)

            except Exception as e:
                logger.warning(f"인사이트 생성 실패 ({ctx_type}): {e}")

        state["insights"] = insights
        state["execution_log"].append(f"✅ {len(insights)}개 인사이트 생성")

        return state

    async def _analyze_relationships(self, state: LangGraphReportState) -> LangGraphReportState:
        """6단계: 컨텍스트 간 관계 분석"""

        state["execution_log"].append("🔗 관계 분석 시작")

        relationships = []

        # 컨텍스트 유형별 분류 (모든 상장사 대응)
        news_contexts = [ctx for ctx in state["contexts"] if ctx.type.startswith("news")]
        company_contexts = [ctx for ctx in state["contexts"] if ctx.type == "company"]
        financial_contexts = [ctx for ctx in state["contexts"] if ctx.type in ["financial", "investment", "stock"]]
        business_contexts = [ctx for ctx in state["contexts"] if ctx.type in ["contract", "deal", "announcement"]]

        # 1. 뉴스-기업 관계 분석
        if news_contexts and company_contexts:
            await self._analyze_news_company_relationship(state, news_contexts, company_contexts, relationships)

        # 2. 재무-뉴스 관계 분석
        if financial_contexts and news_contexts:
            await self._analyze_financial_news_relationship(state, financial_contexts, news_contexts, relationships)

        # 3. 비즈니스 이벤트-뉴스 관계 분석
        if business_contexts and news_contexts:
            await self._analyze_business_news_relationship(state, business_contexts, news_contexts, relationships)

        state["relationships"] = relationships
        state["execution_log"].append(f"✅ {len(relationships)}개 관계 분석 완료")

        return state

    async def _analyze_news_company_relationship(self, state, news_contexts, company_contexts, relationships):
        """뉴스-기업 관계 분석"""
        try:
            relationship_prompt = f"""
            다음 뉴스와 기업 정보 간의 관계를 분석해주세요:

            뉴스 데이터 (최신 5개):
            {json.dumps([ctx.content for ctx in news_contexts[:5]], ensure_ascii=False, indent=2)}

            기업 데이터:
            {json.dumps([ctx.content for ctx in company_contexts[:3]], ensure_ascii=False, indent=2)}

            다음을 분석해주세요:
            1. 뉴스가 기업에 미치는 영향 (긍정/부정/중립)
            2. 기업 가치 및 주가에 대한 시사점
            3. 산업 내 경쟁력 변화
            4. 향후 예상되는 기업 전략 변화

            상장사 투자 관점에서 구체적인 분석을 해주세요.
            """

            response = await self._llm_invoke(relationship_prompt)

            relationship = {
                "type": "news_company_correlation",
                "analysis": response,
                "confidence": 0.8,
                "timestamp": str(asyncio.get_event_loop().time())
            }
            relationships.append(relationship)

        except Exception as e:
            logger.warning(f"뉴스-기업 관계 분석 실패: {e}")

    async def _analyze_financial_news_relationship(self, state, financial_contexts, news_contexts, relationships):
        """재무-뉴스 관계 분석"""
        try:
            relationship_prompt = f"""
            다음 재무 정보와 뉴스 간의 관계를 분석해주세요:

            재무 데이터:
            {json.dumps([ctx.content for ctx in financial_contexts[:3]], ensure_ascii=False, indent=2)}

            관련 뉴스 (최신 3개):
            {json.dumps([ctx.content for ctx in news_contexts[:3]], ensure_ascii=False, indent=2)}

            다음을 분석해주세요:
            1. 재무 성과와 뉴스 이벤트 간의 인과관계
            2. 재무 지표 변화가 시장에 미치는 영향
            3. 투자자 관점에서의 리스크/기회 요소
            4. 재무 건전성에 대한 종합 평가

            투자 의사결정에 도움이 되는 분석을 해주세요.
            """

            response = await self._llm_invoke(relationship_prompt)

            relationship = {
                "type": "financial_news_correlation",
                "analysis": response,
                "confidence": 0.7,
                "timestamp": str(asyncio.get_event_loop().time())
            }
            relationships.append(relationship)

        except Exception as e:
            logger.warning(f"재무-뉴스 관계 분석 실패: {e}")

    async def _analyze_business_news_relationship(self, state, business_contexts, news_contexts, relationships):
        """비즈니스 이벤트-뉴스 관계 분석"""
        try:
            relationship_prompt = f"""
            다음 비즈니스 이벤트와 뉴스 간의 관계를 분석해주세요:

            비즈니스 이벤트:
            {json.dumps([ctx.content for ctx in business_contexts[:3]], ensure_ascii=False, indent=2)}

            관련 뉴스:
            {json.dumps([ctx.content for ctx in news_contexts[:3]], ensure_ascii=False, indent=2)}

            다음을 분석해주세요:
            1. 비즈니스 이벤트가 기업 성장에 미치는 영향
            2. 시장 포지션 변화 및 경쟁 우위
            3. 매출 및 수익성에 대한 영향 예측
            4. 장기적 사업 전략 관점에서의 의미

            기업 분석 관점에서 종합적인 평가를 해주세요.
            """

            response = await self._llm_invoke(relationship_prompt)

            relationship = {
                "type": "business_news_correlation",
                "analysis": response,
                "confidence": 0.75,
                "timestamp": str(asyncio.get_event_loop().time())
            }
            relationships.append(relationship)

        except Exception as e:
            logger.warning(f"비즈니스-뉴스 관계 분석 실패: {e}")

    async def _synthesize_report(self, state: LangGraphReportState) -> LangGraphReportState:
        """7단계: 종합 리포트 합성"""

        state["execution_log"].append("📝 리포트 합성 시작")

        # 섹션별 리포트 생성
        sections = {}

        # 1. 개요 섹션
        overview_prompt = f"""
        다음 정보를 바탕으로 '{state['query']}'에 대한 개요를 작성해주세요:

        수집된 데이터:
        - 총 컨텍스트: {len(state['contexts'])}개
        - 생성된 인사이트: {len(state['insights'])}개
        - 관계 분석: {len(state['relationships'])}개

        분석 깊이: {state['analysis_depth'].value}

        간결하면서도 포괄적인 개요를 작성해주세요.
        """

        try:
            overview_response = await self._llm_invoke(overview_prompt)
            sections["overview"] = overview_response
        except Exception as e:
            sections["overview"] = f"개요 생성 중 오류 발생: {e}"

        # 2. 핵심 발견사항
        if state["insights"]:
            key_findings = "\n\n".join([
                f"**{insight['type']} 분석**\n{insight['content']}"
                for insight in state["insights"]
            ])
            sections["key_findings"] = key_findings

        # 3. 관계 분석
        if state["relationships"]:
            relationship_analysis = "\n\n".join([
                f"**{rel['type']}**\n{rel['analysis']}"
                for rel in state["relationships"]
            ])
            sections["relationships"] = relationship_analysis

        # 4. 데이터 요약
        data_summary = self._generate_data_summary(state["contexts"])
        sections["data_summary"] = data_summary

        # 5. 최종 리포트 합성
        final_report_prompt = f"""
        다음 섹션들을 종합하여 전문적인 분석 리포트를 작성해주세요:

        질의: {state['query']}

        섹션별 내용:

        ## 개요
        {sections.get('overview', 'N/A')}

        ## 핵심 발견사항
        {sections.get('key_findings', 'N/A')}

        ## 관계 분석
        {sections.get('relationships', 'N/A')}

        ## 데이터 요약
        {sections.get('data_summary', 'N/A')}

        다음 구조로 전문적인 리포트를 작성해주세요:
        1. 요약 (Executive Summary)
        2. 상세 분석
        3. 시사점 및 전망
        4. 권장사항

        마크다운 형식으로 작성하고, 비즈니스 의사결정에 도움이 되는 실용적인 내용으로 구성해주세요.
        """

        try:
            final_response = await self._llm_invoke(final_report_prompt)
            state["final_report"] = final_response
            state["report_sections"] = sections
        except Exception as e:
            state["final_report"] = f"리포트 생성 중 오류 발생: {e}"
            state["report_sections"] = sections

        state["execution_log"].append("✅ 리포트 합성 완료")

        return state

    async def _quality_check(self, state: LangGraphReportState) -> LangGraphReportState:
        """8단계: 개선된 품질 검증"""

        state["execution_log"].append("🎯 품질 검증 시작")

        # 상장사 분석에 특화된 품질 평가 요소들
        quality_factors = {}

        # 1. 데이터 다양성 (상장사 분석에 필요한 다양한 데이터 소스)
        context_types = set(ctx.type for ctx in state["contexts"])
        expected_types = {"company", "news", "financial", "stock"}
        type_coverage = len(context_types.intersection(expected_types)) / len(expected_types)
        quality_factors["data_diversity"] = type_coverage

        # 2. 투자 관련 컨텐츠 품질
        investment_keywords = ["주가", "투자", "재무", "수익", "성장", "배당", "밸류에이션", "리스크"]
        content_quality = self._evaluate_investment_content_quality(state["final_report"], state["query"], investment_keywords)
        quality_factors["investment_content_quality"] = content_quality

        # 3. 상장사 분석 구조적 완성도
        required_sections = ["기업분석", "재무분석", "투자포인트", "리스크", "전망"]
        structure_score = sum(1 for section in required_sections
                            if any(keyword in state["final_report"] for keyword in [section, section.lower()]))
        quality_factors["analysis_structure"] = structure_score / len(required_sections)

        # 4. 정량적 분석 포함도
        quantitative_keywords = ["매출", "영업이익", "순이익", "ROE", "PER", "PBR", "부채비율", "%"]
        quant_score = sum(1 for keyword in quantitative_keywords if keyword in state["final_report"])
        quality_factors["quantitative_analysis"] = min(quant_score / len(quantitative_keywords), 1.0)

        # 5. 관계 분석 품질 (상장사는 다양한 이해관계자 분석이 중요)
        quality_factors["relationship_quality"] = min(len(state["relationships"]) / 2.0, 1.0)

        # 6. 인사이트 깊이 (상장사는 투자 관점의 깊은 인사이트 필요)
        insight_depth = self._evaluate_insight_depth(state["insights"])
        quality_factors["insight_depth"] = insight_depth

        # 가중 평균으로 품질 점수 계산 (상장사 분석에 맞게 조정)
        weights = {
            "data_diversity": 0.2,           # 데이터 다양성
            "investment_content_quality": 0.3,  # 투자 관련 내용 품질
            "analysis_structure": 0.2,       # 분석 구조
            "quantitative_analysis": 0.1,    # 정량적 분석
            "relationship_quality": 0.1,     # 관계 분석
            "insight_depth": 0.1            # 인사이트 깊이
        }

        quality_score = sum(score * weights[factor] for factor, score in quality_factors.items())
        state["quality_score"] = quality_score

        # 품질 등급 결정
        if quality_score >= 0.75:
            quality_level = ReportQuality.EXCELLENT
        elif quality_score >= 0.55:
            quality_level = ReportQuality.GOOD
        elif quality_score >= 0.35:
            quality_level = ReportQuality.ACCEPTABLE
        else:
            quality_level = ReportQuality.POOR

        state["quality_level"] = quality_level
        state["execution_log"].append(f"✅ 품질 점수: {quality_score:.2f} ({quality_level.value})")
        state["execution_log"].append(f"   세부 점수: {quality_factors}")

        return state

    async def _enhance_report(self, state: LangGraphReportState) -> LangGraphReportState:
        """9단계: 리포트 개선"""

        retry_count = state.get("retry_count", 0)
        quality_score = state.get("quality_score", 0.0)

        # quality_level 안전 체크
        quality_level = state.get("quality_level", ReportQuality.POOR)
        if not isinstance(quality_level, ReportQuality):
            quality_level = ReportQuality.POOR
            state["quality_level"] = quality_level

        state["execution_log"].append(f"🔧 리포트 개선 시작 (재시도 {retry_count}회차)")

        try:
            # 품질 문제 진단
            issues = []
            if len(state.get("final_report", "")) < 300:
                issues.append("리포트 길이 부족")
            if len(state.get("insights", [])) < 1:
                issues.append("인사이트 부족")
            if quality_score < 0.4:
                issues.append("전반적 품질 저하")

            # 개선 전략 결정
            enhancement_strategy = self._determine_enhancement_strategy(issues)

            # 맞춤형 개선 프롬프트 생성
            if enhancement_strategy == "expand_content":
                enhancement_prompt = f"""
                다음 리포트가 너무 짧습니다. 내용을 확장하고 보완해주세요:

                현재 리포트:
                {state['final_report']}

                사용 가능한 추가 데이터:
                - 수집된 컨텍스트: {len(state.get('contexts', []))}개
                - 생성된 인사이트: {len(state.get('insights', []))}개

                다음을 포함하여 리포트를 확장해주세요:
                1. 상세한 분석 내용
                2. 구체적인 수치와 근거
                3. 시장 영향 분석
                4. 향후 전망과 권장사항

                최소 800자 이상의 전문적인 리포트로 작성해주세요.
                """

            elif enhancement_strategy == "add_insights":
                # 인사이트 부족 시 추가 생성
                available_contexts = [ctx for ctx in state.get("contexts", []) if ctx.confidence > 0.5]
                context_summary = self._summarize_context_data(available_contexts[:5])

                enhancement_prompt = f"""
                현재 리포트에 분석적 인사이트가 부족합니다. 다음 데이터를 바탕으로 리포트를 개선해주세요:

                현재 리포트:
                {state['final_report']}

                추가 데이터:
                {context_summary}

                다음 관점에서 인사이트를 추가해주세요:
                1. 핵심 발견사항과 그 의미
                2. 비즈니스 영향도 분석
                3. 경쟁사 대비 위치
                4. 투자 및 사업 기회
                5. 리스크 요소와 대응방안

                분석적이고 실용적인 인사이트가 풍부한 리포트로 개선해주세요.
                """

            else:  # general_improvement
                enhancement_prompt = f"""
                다음 리포트의 전반적인 품질을 개선해주세요:

                현재 리포트:
                {state['final_report']}

                품질 문제점: {', '.join(issues)}

                개선 요구사항:
                1. 논리적 구조 강화 (도입-본론-결론)
                2. 구체적 데이터와 수치 보강
                3. 전문성과 신뢰성 향상
                4. 읽기 쉬운 문체와 형식
                5. 실행 가능한 권장사항

                전문적이고 완성도 높은 비즈니스 리포트로 재작성해주세요.
                """

            # LLM을 통한 리포트 개선
            enhanced_response = await self._llm_invoke(enhancement_prompt)

            # 개선 결과 검증
            if len(enhanced_response) > len(state.get("final_report", "")):
                state["final_report"] = enhanced_response
                state["execution_log"].append(f"✅ 리포트 개선 완료 ({enhancement_strategy})")
            else:
                state["execution_log"].append("⚠️ 개선 효과 미미, 기존 리포트 유지")

        except Exception as e:
            logger.error(f"[LangGraph] 리포트 개선 실패: {e}")
            state["execution_log"].append(f"❌ 리포트 개선 실패: {e}")

        return state

    def _determine_enhancement_strategy(self, issues: List[str]) -> str:
        """개선 전략 결정"""
        if "리포트 길이 부족" in issues:
            return "expand_content"
        elif "인사이트 부족" in issues:
            return "add_insights"
        else:
            return "general_improvement"

    def _should_enhance_report(self, state: LangGraphReportState) -> str:
        """개선된 품질 검증 후 개선 여부 결정"""

        # 품질 레벨이 없거나 잘못된 값이면 POOR로 설정
        if "quality_level" not in state or not isinstance(state.get("quality_level"), ReportQuality):
            state["quality_level"] = ReportQuality.POOR
            logger.warning("[LangGraph] quality_level이 누락되었거나 잘못된 값입니다. POOR로 설정합니다.")
            return "enhance"

        quality_level = state["quality_level"]
        retry_count = state.get("retry_count", 0)
        quality_score = state.get("quality_score", 0.0)

        # 재시도 횟수 제한 (최대 3회)
        if retry_count >= 3:
            logger.warning(f"[LangGraph] 최대 재시도 횟수 초과: {retry_count}회")
            state["execution_log"].append("⚠️ 최대 재시도 횟수 초과, 현재 결과로 완료")
            return "complete"

        # 품질 기준에 따른 재시도 결정
        should_retry = False

        # POOR 품질은 항상 재시도
        if quality_level == ReportQuality.POOR:
            should_retry = True

        # ACCEPTABLE도 점수가 너무 낮으면 재시도
        elif quality_level == ReportQuality.ACCEPTABLE and quality_score < 0.45:
            should_retry = True

        # 리포트가 너무 짧으면 재시도
        elif len(state.get("final_report", "")) < 300:
            should_retry = True
            state["execution_log"].append("⚠️ 리포트가 너무 짧아 재시도")

        # 인사이트가 부족하면 재시도
        elif len(state.get("insights", [])) < 1:
            should_retry = True
            state["execution_log"].append("⚠️ 인사이트 부족으로 재시도")

        if should_retry:
            state["retry_count"] = retry_count + 1
            state["execution_log"].append(f"🔄 품질 개선 재시도 {state['retry_count']}회차 (점수: {quality_score:.2f})")
            return "enhance"

        # 품질이 충분하면 완료
        state["execution_log"].append(f"✅ 품질 기준 충족, 리포트 완료 (점수: {quality_score:.2f})")
        return "complete"

    # ========== 헬퍼 메서드들 ==========

    async def _llm_invoke(self, prompt: str) -> str:
        """LLM 호출을 위한 비동기 래퍼"""
        try:
            # OllamaLLM은 동기 호출만 지원하므로 비동기로 래핑
            import anyio
            response = await anyio.to_thread.run_sync(self.llm.invoke, prompt)
            return response
        except Exception as e:
            logger.error(f"[LangGraph] LLM 호출 실패: {e}")
            return "LLM 응답 생성 중 오류가 발생했습니다."

    def _safe_parse_keywords(self, content: str) -> List[str]:
        """LLM 응답에서 키워드 안전하게 추출"""
        try:
            # JSON 배열 형태 파싱 시도
            if '[' in content and ']' in content:
                start = content.find('[')
                end = content.rfind(']') + 1
                keywords_json = content[start:end]
                return json.loads(keywords_json)

            # 콤마 구분 텍스트 파싱
            keywords = [k.strip().strip('"\'') for k in content.split(',')]
            return keywords[:5]  # 최대 5개
        except Exception:
            # 실패 시 기본값
            return ["키워드"]

    def _safe_parse_complexity(self, content: str) -> str:
        """LLM 응답에서 복잡도 안전하게 추출"""
        content_lower = content.lower().strip()
        valid_complexities = ["shallow", "standard", "deep", "comprehensive"]

        for complexity in valid_complexities:
            if complexity in content_lower:
                return complexity

        return "standard"  # 기본값

    def _evaluate_content_quality(self, report: str, query: str) -> float:
        """리포트 컨텐츠 품질 평가"""
        if not report or len(report) < 100:
            return 0.0

        query_words = set(query.lower().split())
        report_words = set(report.lower().split())

        # 키워드 포함률
        keyword_coverage = len(query_words.intersection(report_words)) / len(query_words)

        # 문장 구조 평가 (간단한 휴리스틱)
        sentences = report.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

        # 적절한 문장 길이 (10-30 단어)
        length_score = 1.0 if 10 <= avg_sentence_length <= 30 else 0.5

        return (keyword_coverage * 0.7 + length_score * 0.3)

    def _summarize_context_data(self, contexts: List[ContextItem]) -> str:
        """컨텍스트 데이터를 요약하여 프롬프트용으로 변환"""
        summaries = []
        for i, ctx in enumerate(contexts[:3], 1):
            content = ctx.content
            if isinstance(content, dict):
                title = content.get('title', content.get('name', f'{ctx.type} {i}'))
                summary = f"{i}. {title}"
                if 'amount' in content:
                    summary += f" (금액: {content['amount']})"
                if 'date' in content:
                    summary += f" ({content['date']})"
            else:
                summary = f"{i}. {str(content)[:100]}..."
            summaries.append(summary)
        return "\n".join(summaries)

    def _determine_graph_type(self, row: Dict[str, Any]) -> str:
        """그래프 데이터 타입 결정 (모든 상장사 대응)"""
        labels = row.get("labels", [])

        # 기업 관련
        if "Company" in labels:
            return "company"
        elif "Industry" in labels or "Sector" in labels:
            return "industry"
        elif "Stock" in labels or "Security" in labels:
            return "stock"

        # 재무/계약 관련
        elif "Contract" in labels or "Deal" in labels:
            return "contract"
        elif "Financial" in labels or "Revenue" in labels:
            return "financial"
        elif "Investment" in labels or "Funding" in labels:
            return "investment"

        # 뉴스/이벤트 관련
        elif "Event" in labels:
            return "event"
        elif "News" in labels or "Article" in labels:
            return "news"
        elif "Announcement" in labels or "Disclosure" in labels:
            return "announcement"

        # 기타 비즈니스 엔터티
        elif "Product" in labels or "Service" in labels:
            return "product"
        elif "Person" in labels or "Executive" in labels:
            return "person"
        elif "Location" in labels or "Region" in labels:
            return "location"
        elif "Technology" in labels or "Patent" in labels:
            return "technology"

        # 규제/정책 관련
        elif "Regulation" in labels or "Policy" in labels:
            return "regulation"
        elif "ESG" in labels or "Sustainability" in labels:
            return "esg"

        else:
            return "entity"

    def _calculate_relevance(self, row: Dict[str, Any], query: str) -> float:
        """그래프 데이터 관련성 계산"""
        # 간단한 키워드 매칭 기반 관련성 계산
        query_words = query.lower().split()
        content_text = json.dumps(row, ensure_ascii=False).lower()

        matches = sum(1 for word in query_words if word in content_text)
        return min(matches / len(query_words), 1.0)

    def _calculate_news_relevance(self, source_data: Dict[str, Any], query: str) -> float:
        """뉴스 데이터 관련성 계산"""
        query_words = query.lower().split()
        title = source_data.get("title", "").lower()
        content = source_data.get("content", "").lower()

        title_matches = sum(1 for word in query_words if word in title)
        content_matches = sum(1 for word in query_words if word in content)

        # 제목 매치에 더 높은 가중치
        relevance = (title_matches * 2 + content_matches) / (len(query_words) * 3)
        return min(relevance, 1.0)

    async def _generate_extended_queries(self, original_query: str) -> List[str]:
        """확장 검색 쿼리 생성"""
        expand_prompt = f"""
        다음 원본 쿼리와 관련된 확장 검색 키워드 3개를 생성해주세요:

        원본 쿼리: {original_query}

        연관성 있는 키워드들을 JSON 배열로 반환해주세요:
        ["확장키워드1", "확장키워드2", "확장키워드3"]
        """

        try:
            response = await self._llm_invoke(expand_prompt)
            extended_queries = json.loads(response)
            return extended_queries[:3]  # 최대 3개만
        except Exception:
            # 실패 시 기본 확장 키워드 반환
            return [f"{original_query} 분석", f"{original_query} 전망", f"{original_query} 동향"]

    def _generate_data_summary(self, contexts: List[ContextItem]) -> str:
        """데이터 요약 생성"""
        summary_lines = [
            f"📊 **총 수집 데이터**: {len(contexts)}개",
            "",
            "**데이터 출처별 분포:**"
        ]

        # 출처별 통계
        source_counts = {}
        for ctx in contexts:
            source_counts[ctx.source] = source_counts.get(ctx.source, 0) + 1

        for source, count in source_counts.items():
            summary_lines.append(f"- {source}: {count}개")

        summary_lines.extend([
            "",
            "**데이터 품질:**",
            f"- 평균 신뢰도: {(sum(ctx.confidence for ctx in contexts) / len(contexts)) if len(contexts) else 0 :.2f}",
            f"- 평균 관련성: {(sum(ctx.relevance for ctx in contexts) / len(contexts)) if len(contexts) else 0 :.2f}"
        ])

        return "\n".join(summary_lines)

    def _initialize_state(
        self,
        query: str,
        domain: Optional[str] = None,
        lookback_days: int = 180,
        analysis_depth: str = "standard",
        symbol: Optional[str] = None
    ) -> LangGraphReportState:
        """안전한 상태 초기화"""

        # 입력 검증 및 정규화
        query = query.strip() if query else ""
        if not query:
            raise ValueError("쿼리가 비어있습니다")

        domain = domain.strip() if domain else None
        lookback_days = max(1, min(lookback_days, 365))  # 1~365일 범위 제한

        # 분석 깊이 검증
        try:
            depth_enum = AnalysisDepth(analysis_depth)
        except ValueError:
            logger.warning(f"알 수 없는 분석 깊이: {analysis_depth}, 기본값으로 설정")
            depth_enum = AnalysisDepth.STANDARD

        # 기본 상태 생성
        state = LangGraphReportState(
            # 입력 정보
            query=query,
            domain=domain,
            lookback_days=lookback_days,
            analysis_depth=depth_enum,

            # 수집된 컨텍스트
            contexts=[],

            # 분석 결과
            insights=[],
            relationships=[],

            # 리포트 생성
            report_sections={},
            final_report="",

            # 품질 관리
            quality_score=0.0,
            quality_level=ReportQuality.POOR,
            retry_count=0,

            # 메타데이터
            execution_log=[f"🚀 LangGraph 워크플로우 시작 - 쿼리: {query}"],
            processing_time=0.0
        )

        # 선택적 파라미터 추가
        if symbol and symbol.strip():
            state["symbol"] = symbol.strip()

        return state

    # ========== 공개 API ==========

    async def generate_langgraph_report(
        self,
        query: str,
        *,
        domain: Optional[str] = None,
        lookback_days: int = 180,
        analysis_depth: str = "standard",
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """LangGraph 기반 고급 리포트 생성"""

        import time
        start_time = time.time()

        try:
            # 안전한 상태 초기화
            initial_state = self._initialize_state(
                query=query,
                domain=domain,
                lookback_days=lookback_days,
                analysis_depth=analysis_depth,
                symbol=symbol
            )

            logger.info(f"[LangGraph] 리포트 생성 시작 - 쿼리: {query}, 깊이: {analysis_depth}")

            # LangGraph 워크플로우 실행
            final_state = await self.workflow.ainvoke(initial_state)

            # 실행 시간 계산
            final_state["processing_time"] = time.time() - start_time

            # 품질 레벨 안전 접근
            quality_level = "poor"  # 기본값을 poor로 변경
            if "quality_level" in final_state:
                if isinstance(final_state["quality_level"], ReportQuality):
                    quality_level = final_state["quality_level"].value
                else:
                    # 문자열이나 다른 타입인 경우
                    quality_level = str(final_state["quality_level"]).lower()
                    # 유효한 값인지 확인
                    if quality_level not in ["poor", "acceptable", "good", "excellent"]:
                        quality_level = "poor"

            logger.info(f"[LangGraph] 리포트 생성 완료 - 품질점수: {final_state['quality_score']:.2f}, 처리시간: {final_state['processing_time']:.2f}초")

            return {
                "markdown": final_state.get("final_report", "리포트 생성 중 오류가 발생했습니다."),
                "quality_score": final_state.get("quality_score", 0.0),
                "quality_level": quality_level,
                "contexts_count": len(final_state.get("contexts", [])),
                "insights_count": len(final_state.get("insights", [])),
                "relationships_count": len(final_state.get("relationships", [])),
                "processing_time": final_state.get("processing_time", 0.0),
                "retry_count": final_state.get("retry_count", 0),
                "execution_log": final_state.get("execution_log", []),
                "sections": final_state.get("report_sections", {}),
                "type": "langgraph_enhanced",
                "meta": {
                    "query": query,
                    "domain": domain,
                    "lookback_days": lookback_days,
                    "analysis_depth": analysis_depth,
                    "confidence": final_state.get("quality_score", 0.0) * 100,
                    "coverage": min(len(final_state.get("contexts", [])) / 50 * 100, 100),
                    "search_time": final_state.get("processing_time", 0.0)
                }
            }

        except ValueError as e:
            logger.error(f"입력 검증 오류: {e}")
            return {
                "markdown": f"# 입력 오류\n\n{str(e)}",
                "quality_score": 0.0,
                "quality_level": "poor",
                "error": str(e),
                "processing_time": time.time() - start_time,
                "type": "langgraph_validation_error"
            }
        except Exception as e:
            logger.error(f"LangGraph 리포트 생성 실패: {e}")
            logger.error(traceback.format_exc())
            return {
                "markdown": f"# 리포트 생성 실패\n\n시스템 오류가 발생했습니다: {str(e)}",
                "quality_score": 0.0,
                "quality_level": "poor",
                "error": str(e),
                "processing_time": time.time() - start_time,
                "type": "langgraph_system_error"
            }

    # ========== 하이브리드 검색 지원 메서드 ==========

    async def _langgraph_hybrid_search(
        self,
        query: str,
        lookback_days: int = 180,
        size: int = 50
    ) -> List[Dict[str, Any]]:
        """LangGraph 전용 하이브리드 검색 (한번의 쿼리로 키워드 + 벡터)"""

        try:
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

            # 임베딩이 있으면 하이브리드, 없으면 키워드만
            if self.embedding_client:
                try:
                    # 쿼리 임베딩 생성
                    query_embedding = await self.embedding_client.encode(query)

                    # 간단한 키워드 검색 (임베딩은 나중에 후처리로)
                    hybrid_query = {
                        "size": size * 2,  # 벡터 필터링을 위해 더 많이 가져옴
                        "query": {
                            "bool": {
                                "should": [
                                    {
                                        "multi_match": {
                                            "query": query,
                                            "fields": ["title^3", "text^2", "content"],
                                            "type": "best_fields",
                                            "fuzziness": "AUTO"
                                        }
                                    },
                                    {
                                        "match_phrase": {
                                            "title": {
                                                "query": query,
                                                "boost": 2.0
                                            }
                                        }
                                    }
                                ],
                                "filter": [
                                    {
                                        "range": {
                                            "created_datetime": {
                                                "gte": cutoff_date
                                            }
                                        }
                                    }
                                ]
                            }
                        },
                        "_source": ["text", "title", "url", "created_datetime", "metadata"]
                    }

                    result = await self.opensearch.search(
                        index=settings.news_bulk_index,
                        query=hybrid_query,
                        size=size * 2
                    )
                    hits = result.get("hits", {}).get("hits", [])

                    # 벡터 유사도로 재정렬
                    if hits:
                        scored_hits = []
                        for hit in hits:
                            source = hit.get("_source", {})
                            doc_text = f"{source.get('title', '')} {source.get('text', source.get('content', ''))}"

                            if doc_text.strip():
                                try:
                                    doc_embedding = await self.embedding_client.encode(doc_text[:500])
                                    similarity = self._calculate_cosine_similarity(query_embedding, doc_embedding)

                                    # 키워드 점수와 벡터 유사도 결합
                                    keyword_score = hit.get("_score", 0)
                                    combined_score = (keyword_score * 0.4) + (similarity * 10)  # 벡터에 높은 가중치

                                    hit["_vector_similarity"] = similarity
                                    hit["_combined_score"] = combined_score
                                    scored_hits.append(hit)

                                except Exception as e:
                                    logger.warning(f"문서 임베딩 실패: {e}")
                                    hit["_combined_score"] = hit.get("_score", 0)
                                    scored_hits.append(hit)

                        # 결합 점수로 정렬 후 상위 N개 반환
                        scored_hits.sort(key=lambda x: x.get("_combined_score", 0), reverse=True)
                        hits = scored_hits[:size]

                    logger.info(f"하이브리드 검색 완료: {len(hits)}건")
                    return hits

                except Exception as e:
                    logger.warning(f"하이브리드 검색 실패, 키워드만 사용: {e}")

            # 키워드 검색만
            keyword_query = {
                "size": size,
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^3", "text^2", "content"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO"
                                }
                            }
                        ],
                        "filter": [
                            {
                                "range": {
                                    "created_datetime": {
                                        "gte": cutoff_date
                                    }
                                }
                            }
                        ]
                    }
                },
                "_source": ["text", "title", "url", "created_datetime", "metadata"]
            }

            result = await self.opensearch.search(
                index=settings.news_bulk_index,
                query=keyword_query,
                size=size
            )
            hits = result.get("hits", {}).get("hits", [])
            logger.info(f"키워드 검색 완료: {len(hits)}건")
            return hits

        except Exception as e:
            logger.error(f"검색 오류: {e}")
            return []

    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """두 벡터 간의 코사인 유사도 계산"""
        try:
            import numpy as np

            # numpy 배열로 변환
            a = np.array(vec1)
            b = np.array(vec2)

            # 벡터 크기가 다르면 0 반환
            if len(a) != len(b):
                return 0.0

            # 코사인 유사도 계산
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)

            # 0으로 나누기 방지
            if norm_a == 0 or norm_b == 0:
                return 0.0

            similarity = dot_product / (norm_a * norm_b)

            # -1 ~ 1 범위를 0 ~ 1 범위로 정규화
            return (similarity + 1.0) / 2.0

        except Exception as e:
            logger.warning(f"코사인 유사도 계산 실패: {e}")
            return 0.0

    def _calculate_graph_relevance(self, row: Dict[str, Any], query: str) -> float:
        """그래프 데이터의 관련성 계산"""
        try:
            relevance = 0.0
            query_lower = query.lower()

            # 라벨 기반 관련성
            labels = row.get("labels", [])
            for label in labels:
                if any(keyword in label.lower() for keyword in query_lower.split()):
                    relevance += 0.3

            # 속성 기반 관련성
            for key, value in row.items():
                if isinstance(value, str) and any(keyword in value.lower() for keyword in query_lower.split()):
                    relevance += 0.2

            # 계약 금액이 있으면 가중치 추가
            if "amount" in row and row.get("amount"):
                relevance += 0.1

            return min(relevance, 1.0)

        except Exception:
            return 0.5  # 기본값

    def _generate_sector_specific_insight_prompt(self, ctx_type: str, query: str, data_summary: str) -> str:
        """섹터별 맞춤형 인사이트 프롬프트 생성"""

        base_template = f"질의 '{query}'에 대한 {ctx_type} 데이터 분석:\n\n{data_summary}\n\n"

        if ctx_type == "company":
            return base_template + """
상장사 기업 분석 관점에서 다음 인사이트를 제공해주세요:
1. [기업 경쟁력] - 시장 내 포지션 및 차별화 요소
2. [재무 건전성] - 수익성, 성장성, 안정성 종합 평가
3. [투자 매력도] - 주가 전망 및 투자 포인트
4. [리스크 요소] - 주요 우려사항 및 대응 전략

각 항목을 2-3문장으로 구체적으로 분석해주세요."""

        elif ctx_type in ["financial", "investment", "stock"]:
            return base_template + """
재무/투자 분석 관점에서 다음 인사이트를 제공해주세요:
1. [수익성 분석] - 매출, 영업이익, 순이익 추세 및 마진 분석
2. [성장성 평가] - 전년 대비 성장률 및 미래 성장 동력
3. [밸류에이션] - 주가 적정성 및 투자 시점 판단
4. [배당/주주환원] - 배당 정책 및 주주 친화 정책

투자자 관점에서 실용적인 분석을 해주세요."""

        elif ctx_type in ["news", "announcement"]:
            return base_template + """
뉴스/공시 분석 관점에서 다음 인사이트를 제공해주세요:
1. [시장 반응] - 뉴스가 주가 및 시장 센티먼트에 미치는 영향
2. [사업 영향] - 기업의 중장기 사업 전략에 대한 시사점
3. [경쟁 환경] - 동종 업계 및 경쟁사 대비 상대적 위치 변화
4. [투자 임팩트] - 투자자 행동 변화 및 주목해야 할 포인트

시장 분석가 관점에서 전문적인 해석을 해주세요."""

        elif ctx_type in ["industry", "sector"]:
            return base_template + """
산업/섹터 분석 관점에서 다음 인사이트를 제공해주세요:
1. [산업 트렌드] - 업계 전반의 성장 동력 및 변화 요인
2. [경쟁 구도] - 주요 플레이어들의 시장 점유율 및 경쟁 전략
3. [규제 환경] - 정책 변화가 업계에 미치는 영향
4. [투자 기회] - 섹터 내 유망 종목 및 투자 테마

섹터 애널리스트 관점에서 종합적인 분석을 해주세요."""

        elif ctx_type in ["technology", "product"]:
            return base_template + """
기술/제품 분석 관점에서 다음 인사이트를 제공해주세요:
1. [기술 혁신] - 신기술 도입 및 특허 포트폴리오 강화 효과
2. [시장 확장] - 신제품/서비스를 통한 시장 확대 가능성
3. [수익 기여] - 기술/제품이 매출 및 수익성에 미치는 영향
4. [경쟁 우위] - 기술력 기반 지속가능한 경쟁 우위 구축

기술 분석 전문가 관점에서 평가해주세요."""

        else:
            # 기본 템플릿
            return base_template + """
다음 관점에서 핵심 인사이트를 제공해주세요:
1. [주요 발견사항] - 데이터에서 나타나는 핵심 트렌드
2. [비즈니스 영향] - 기업 운영 및 전략에 미치는 영향
3. [시장 의미] - 주식시장 및 투자자들에게 주는 시사점
4. [향후 전망] - 예상되는 변화 및 주목할 포인트

전문 애널리스트 관점에서 분석해주세요."""

    async def _collect_stock_data(self, state: LangGraphReportState, contexts: List[ContextItem]):
        """주가 및 재무 데이터 수집"""
        try:
            # 기업명 또는 심볼에서 주가 데이터 수집
            company_names = []
            symbols = []

            # 컨텍스트에서 기업 정보 추출
            for ctx in contexts:
                if ctx.type == "company":
                    content = ctx.content
                    if isinstance(content, dict):
                        if "name" in content:
                            company_names.append(content["name"])
                        if "symbol" in content or "ticker" in content:
                            symbol = content.get("symbol") or content.get("ticker")
                            if symbol:
                                symbols.append(symbol)

            # 쿼리에서도 심볼 추출 시도
            if state.get("symbol"):
                symbols.append(state["symbol"])

            # 주가 데이터 수집
            for symbol in symbols[:3]:  # 최대 3개 심볼
                try:
                    # StockMCP를 통한 주가 데이터 수집
                    stock_data = await self._fetch_stock_info(symbol)

                    if stock_data:
                        stock_context = ContextItem(
                            source="stock_api",
                            type="stock",
                            content=stock_data,
                            confidence=0.9,
                            relevance=0.8,
                            timestamp=str(asyncio.get_event_loop().time())
                        )
                        contexts.append(stock_context)

                except Exception as e:
                    logger.warning(f"주가 데이터 수집 실패 ({symbol}): {e}")

        except Exception as e:
            logger.warning(f"주가 데이터 수집 중 오류: {e}")

    async def _fetch_stock_info(self, symbol: str) -> Dict[str, Any]:
        """주식 정보 조회"""
        try:
            # 여기서는 간단한 더미 데이터를 반환
            # 실제로는 외부 API (Yahoo Finance, Alpha Vantage 등) 연동
            return {
                "symbol": symbol,
                "current_price": "조회 필요",
                "price_change": "조회 필요",
                "price_change_percent": "조회 필요",
                "volume": "조회 필요",
                "market_cap": "조회 필요",
                "pe_ratio": "조회 필요",
                "dividend_yield": "조회 필요",
                "52_week_high": "조회 필요",
                "52_week_low": "조회 필요",
                "note": "실제 API 연동 시 실시간 데이터 제공"
            }

        except Exception as e:
            logger.error(f"주식 정보 조회 실패 ({symbol}): {e}")
            return None

    def _evaluate_investment_content_quality(self, report: str, query: str, investment_keywords: List[str]) -> float:
        """투자 관련 컨텐츠 품질 평가"""
        try:
            if not report or len(report) < 100:
                return 0.0

            # 투자 키워드 포함 정도
            keyword_count = sum(1 for keyword in investment_keywords if keyword in report)
            keyword_score = min(keyword_count / len(investment_keywords), 1.0)

            # 쿼리 관련성
            query_words = set(query.lower().split())
            report_words = set(report.lower().split())
            relevance_score = len(query_words.intersection(report_words)) / len(query_words)

            # 투자 분석 문구 확인
            analysis_phrases = ["투자 포인트", "리스크 요인", "목표주가", "투자의견", "재무 분석"]
            phrase_score = sum(1 for phrase in analysis_phrases if phrase in report) / len(analysis_phrases)

            # 가중 평균
            return (keyword_score * 0.4 + relevance_score * 0.3 + phrase_score * 0.3)

        except Exception:
            return 0.5

    def _evaluate_insight_depth(self, insights: List[Dict[str, Any]]) -> float:
        """인사이트 깊이 평가"""
        try:
            if not insights:
                return 0.0

            depth_score = 0.0
            total_insights = len(insights)

            for insight in insights:
                content = insight.get("content", "")
                if isinstance(content, str):
                    # 분석 깊이 지표들
                    depth_indicators = [
                        "분석", "영향", "전망", "예상", "평가",
                        "비교", "변화", "성장", "위험", "기회"
                    ]

                    indicator_count = sum(1 for indicator in depth_indicators if indicator in content)

                    # 문장 길이도 고려 (더 긴 설명 = 더 깊은 분석)
                    sentence_length_score = min(len(content) / 200, 1.0)

                    insight_depth = (indicator_count / len(depth_indicators)) * 0.7 + sentence_length_score * 0.3
                    depth_score += insight_depth

            return min(depth_score / total_insights, 1.0)

        except Exception:
            return 0.5