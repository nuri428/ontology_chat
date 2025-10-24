"""
질의 라우팅 시스템
사용자 질의를 의도별로 분석하여 적절한 핸들러로 라우팅
"""

from typing import Dict, Any, List
import logging
import time
import asyncio

from api.services.intent_classifier import classify_query_intent, QueryIntent
from api.services.news_handler import NewsQueryHandler
from api.services.stock_analysis_handler import StockAnalysisHandler
from api.services.context_answer_generator import generate_context_answer

# 모니터링 및 트레이싱
try:
    from api.monitoring.metrics_collector import track_query, query_metrics, session_manager, QueryTracker
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    def track_query(*args, **kwargs):
        from contextlib import nullcontext
        return nullcontext()

logger = logging.getLogger(__name__)

class QueryRouter:
    """질의 라우팅 및 처리 관리자 (하이브리드: 단순 핸들러 + Multi-Agent LangGraph)"""

    def __init__(self, chat_service, response_formatter, langgraph_engine=None):
        self.chat_service = chat_service
        self.response_formatter = response_formatter
        self.langgraph_engine = langgraph_engine  # LangGraph Multi-Agent 엔진

        # 핸들러 초기화
        self.news_handler = NewsQueryHandler(chat_service)
        self.stock_handler = StockAnalysisHandler(chat_service, response_formatter)

    async def process_query(self, query: str, user_id: str = "anonymous", session_id: str = None, force_deep_analysis: bool = False) -> Dict[str, Any]:
        """질의 처리 메인 엔트리포인트 (하이브리드 라우팅: 단순/복잡 자동 판단)"""
        start_time = time.time()

        # 세션 관리
        if MONITORING_AVAILABLE and session_id:
            session_manager.record_query(session_id)

        # 질의 추적 시작
        async with track_query(query, user_id, session_id) as tracker:
            logger.info(f"[라우터] 질의 처리 시작: {query}")

            try:
                # 1. 의도 분석
                tracker.start_stage("intent_classification")
                intent_result = classify_query_intent(query)
                tracker.end_stage("intent_classification", {
                    "intent": intent_result.intent.value,
                    "confidence": intent_result.confidence
                })

                # 트레이커에 의도 설정
                tracker.set_intent(intent_result.intent.value, intent_result.confidence)

                logger.info(f"[라우터] 의도 분석: {intent_result.intent.value} (신뢰도: {intent_result.confidence:.2f})")

                # 2. 복잡도 판단 (하이브리드 라우팅)
                complexity_score = self._analyze_query_complexity(query, intent_result)
                requires_deep = self._requires_deep_analysis(query)

                logger.info(f"[라우터] 복잡도: {complexity_score:.2f}, 심층분석 필요: {requires_deep}, 강제: {force_deep_analysis}")

                # 3. 라우팅 결정
                tracker.start_stage("query_processing")

                # 복잡한 질문이거나 명시적 요청 → LangGraph Multi-Agent
                # 임계값 0.7 → 0.85로 상향 조정 (더 많은 질의를 빠른 핸들러로 처리)
                if force_deep_analysis or complexity_score >= 0.85 or requires_deep:
                    logger.info(f"[라우터] → LangGraph Multi-Agent 사용")
                    response = await self._route_to_langgraph(query, intent_result, tracker, complexity_score, force_deep=force_deep_analysis)

                # 단순 질문 → 기존 빠른 핸들러
                elif intent_result.intent == QueryIntent.NEWS_INQUIRY:
                    logger.info(f"[라우터] → 빠른 뉴스 핸들러")
                    response = await self.news_handler.handle_news_query(query, intent_result, tracker)

                elif intent_result.intent == QueryIntent.STOCK_ANALYSIS:
                    logger.info(f"[라우터] → 빠른 주식 분석 핸들러")
                    response = await self.stock_handler.handle_stock_query(query, intent_result, tracker)

                elif intent_result.intent == QueryIntent.GENERAL_QA:
                    logger.info(f"[라우터] → 일반 QA 핸들러")
                    response = await self._handle_general_qa(query, intent_result, tracker)

                else:
                    # UNKNOWN이거나 분류 실패한 경우 - 기존 방식 사용
                    logger.info(f"[라우터] → 폴백 핸들러")
                    response = await self._handle_fallback(query, tracker)

                tracker.end_stage("query_processing", {
                    "response_type": response.get("type"),
                    "response_length": len(response.get("markdown", ""))
                })

                # 3. 공통 메타데이터 추가
                processing_time = (time.time() - start_time) * 1000
                response["meta"] = response.get("meta", {})
                response["meta"].update({
                    "processing_time_ms": processing_time,
                    "intent": intent_result.intent.value,
                    "confidence": intent_result.confidence,
                    "reasoning": intent_result.reasoning,
                    "router_version": "1.0",
                    "user_id": user_id,
                    "session_id": session_id
                })

                # 품질 메트릭 기록
                if MONITORING_AVAILABLE:
                    quality_score = min(1.0, intent_result.confidence * 0.7 + 0.3)
                    tracker.record_quality_metrics({
                        "intent_confidence": intent_result.confidence,
                        "overall_quality": quality_score
                    })

                # 트래커에 응답 설정
                if MONITORING_AVAILABLE and hasattr(tracker, 'set_response'):
                    tracker.set_response(response)

                logger.info(f"[라우터] 처리 완료: {processing_time:.1f}ms")
                return response

            except Exception as e:
                logger.error(f"[라우터] 처리 실패: {e}")
                # 트래커에 오류 기록
                tracker.record_error("processing_error", "query_router", str(e))
                # 오류 발생시 폴백
                return await self._handle_error_fallback(query, str(e), tracker)

    async def _handle_general_qa(self, query: str, intent_result, tracker: QueryTracker = None) -> Dict[str, Any]:
        """일반 질문 처리"""
        logger.info(f"[일반 QA] 처리: {query}")

        if tracker:
            tracker.start_stage("general_qa_processing")

        # 간단한 일반 질문 응답 생성
        markdown_sections = []

        if any(word in query.lower() for word in ["per", "pbr", "roe", "배당"]):
            # 금융 용어 질문
            markdown_sections.extend(self._generate_financial_term_explanation(query))
        else:
            # 기타 일반 질문
            markdown_sections.extend(self._generate_general_response(query))

        if tracker:
            tracker.end_stage("general_qa_processing", {
                "qa_type": "financial_terms" if any(word in query.lower() for word in ["per", "pbr", "roe", "배당"]) else "general",
                "sections_count": len(markdown_sections)
            })

        return {
            "type": "general_qa",
            "markdown": "\\n".join(markdown_sections),
            "meta": {
                "query": query,
                "analysis_type": "general_qa"
            }
        }

    async def _handle_fallback(self, query: str, tracker: QueryTracker = None) -> Dict[str, Any]:
        """폴백 처리 - 기존 방식 사용 (재귀 방지를 위해 _generate_answer_legacy 직접 호출)"""
        logger.info(f"[폴백] 기존 방식으로 처리: {query}")

        if tracker:
            tracker.start_stage("fallback_processing")

        try:
            # 재귀 방지: _generate_answer_legacy 직접 호출
            result = await self.chat_service._generate_answer_legacy(query)

            # 결과 형태 통일
            if isinstance(result, dict) and "answer" in result:
                # meta 정보 병합 (graph_samples_shown 등 포함)
                result_meta = result.get("meta", {})
                combined_meta = {
                    "query": query,
                    "analysis_type": "fallback",
                    "fallback_reason": "intent_classification_failed",
                    "graph_samples_shown": result_meta.get("graph_samples_shown", 0),
                    "total_latency_ms": result_meta.get("total_latency_ms", 0),
                    **result_meta  # 기존 meta 정보도 포함
                }

                return {
                    "type": "fallback",
                    "markdown": result["answer"],
                    "sources": result.get("sources", []),
                    "graph_samples": result.get("graph_samples", []),  # 그래프 샘플 추가
                    "meta": combined_meta
                }
            else:
                return {
                    "type": "fallback",
                    "markdown": str(result),
                    "meta": {
                        "query": query,
                        "analysis_type": "fallback"
                    }
                }
        except Exception as e:
            logger.error(f"폴백 처리도 실패: {e}")
            if tracker:
                tracker.record_error("fallback_error", "fallback_processing", str(e))
            return await self._handle_error_fallback(query, str(e), tracker)
        finally:
            if tracker:
                tracker.end_stage("fallback_processing")

    async def _handle_fallback_fast(self, query: str, intent_result, tracker: QueryTracker = None) -> Dict[str, Any]:
        """빠른 폴백 처리 - LangGraph 타임아웃 시 사용 (의도 기반 라우팅)"""
        logger.info(f"[빠른 폴백] 의도 기반 빠른 처리: {query} (의도: {intent_result.intent.value})")

        if tracker:
            tracker.start_stage("fast_fallback_processing")

        try:
            # 의도에 따라 적절한 빠른 핸들러 사용
            if intent_result.intent == QueryIntent.NEWS_INQUIRY:
                response = await self.news_handler.handle_news_query(query, intent_result, tracker)
            elif intent_result.intent == QueryIntent.STOCK_ANALYSIS:
                response = await self.stock_handler.handle_stock_query(query, intent_result, tracker)
            else:
                # 기본 폴백
                response = await self._handle_fallback(query, tracker)

            # 타임아웃 경고 추가
            response["meta"] = response.get("meta", {})
            response["meta"]["langgraph_timeout"] = True
            response["meta"]["fallback_reason"] = "langgraph_timeout"

            if tracker:
                tracker.end_stage("fast_fallback_processing")

            return response

        except Exception as e:
            logger.error(f"빠른 폴백 처리도 실패: {e}")
            if tracker:
                tracker.record_error("fast_fallback_error", "fast_fallback_processing", str(e))
                tracker.end_stage("fast_fallback_processing")
            return await self._handle_error_fallback(query, str(e), tracker)

    async def _handle_error_fallback(self, query: str, error_msg: str, tracker: QueryTracker = None) -> Dict[str, Any]:
        """오류 발생시 최종 폴백"""
        return {
            "type": "error",
            "markdown": f"""## ⚠️ 처리 중 오류가 발생했습니다

죄송합니다. 요청을 처리하는 중 문제가 발생했습니다.

**요청**: {query}

다시 시도해주시거나, 다른 방식으로 질문해주세요.

**예시:**
- "삼성전자 관련 뉴스 보여줘"
- "방산 유망주 추천해줘"
- "PER이 뭐야?"
""",
            "meta": {
                "query": query,
                "error": error_msg,
                "analysis_type": "error"
            }
        }

    def _generate_financial_term_explanation(self, query: str) -> List[str]:
        """금융 용어 설명 생성"""
        sections = []

        sections.append("## 📚 금융 용어 설명")
        sections.append("")

        query_lower = query.lower()

        if "per" in query_lower:
            sections.extend([
                "### PER (Price Earning Ratio)",
                "- **정의**: 주가수익비율, 주가를 주당순이익(EPS)으로 나눈 값",
                "- **해석**: 낮을수록 저평가, 높을수록 고평가 (업종별 차이 고려 필요)",
                "- **활용**: 같은 업종 내 기업 비교나 과거 PER과 비교시 유용",
                ""
            ])

        if "pbr" in query_lower:
            sections.extend([
                "### PBR (Price Book-value Ratio)",
                "- **정의**: 주가순자산비율, 주가를 주당순자산(BPS)으로 나눈 값",
                "- **해석**: 1 미만이면 청산가치 대비 저평가",
                "- **한계**: 자산의 실제 가치와 장부가치 간 차이 존재",
                ""
            ])

        if "roe" in query_lower:
            sections.extend([
                "### ROE (Return On Equity)",
                "- **정의**: 자기자본이익률, 당기순이익을 자기자본으로 나눈 값",
                "- **해석**: 기업이 자기자본을 활용해 얼마나 효율적으로 이익을 창출하는지 측정",
                "- **기준**: 일반적으로 10% 이상이면 양호",
                ""
            ])

        if "배당" in query_lower:
            sections.extend([
                "### 배당 관련 지표",
                "- **배당수익률**: 연간 배당금을 현재 주가로 나눈 값",
                "- **배당성향**: 당기순이익 중 배당으로 지급하는 비율",
                "- **배당 안정성**: 꾸준한 배당 지급 이력과 향후 지속 가능성",
                ""
            ])

        return sections

    def _generate_general_response(self, query: str) -> List[str]:
        """일반 응답 생성"""
        return [
            "## 💡 질문 답변",
            "",
            f"**질문**: {query}",
            "",
            "더 구체적인 정보를 원하시면 다음과 같이 질문해주세요:",
            "",
            "**뉴스 관련:**",
            '- "삼성전자 관련 뉴스 보여줘"',
            '- "방산 관련 최근 소식은?"',
            "",
            "**투자 분석:**",
            '- "에코프로 전망 어때?"',
            '- "2차전지 유망주 추천해줘"',
            "",
            "**금융 용어:**",
            '- "PER이 뭐야?"',
            '- "배당수익률 계산법은?"'
        ]

    def _analyze_query_complexity(self, query: str, intent_result) -> float:
        """질문 복잡도 점수 계산 (0.0-1.0)"""
        score = 0.0

        # 1. 길이 기반 복잡도
        if len(query) > 80:
            score += 0.3
        elif len(query) > 50:
            score += 0.2

        # 2. 복잡한 키워드 감지 (개선: 가중치 조정)
        complex_keywords = [
            "비교", "분석", "전망", "트렌드", "보고서", "종합",
            "심층", "상세", "자세히", "vs", "대비", "추이",
            "전략", "경쟁력", "밸류체인", "포지셔닝"  # 추가
        ]
        matched_keywords = sum(1 for kw in complex_keywords if kw in query)
        # 키워드 1개: +0.2, 2개: +0.4, 3개 이상: +0.5
        if matched_keywords >= 3:
            score += 0.5
        elif matched_keywords >= 2:
            score += 0.4
        elif matched_keywords >= 1:
            score += 0.2

        # 3. 의도 신뢰도 기반 (불명확하면 복잡도 증가)
        if intent_result.confidence < 0.6:
            score += 0.2
        elif intent_result.confidence < 0.4:
            score += 0.3

        # 4. 다중 엔티티 감지 (여러 회사/산업 언급)
        companies = ["삼성", "LG", "SK", "현대", "포스코", "네이버", "카카오", "에코프로", "마이크론"]
        company_count = sum(1 for company in companies if company in query)
        if company_count >= 3:
            score += 0.4  # 3개 이상이면 확실히 복잡
        elif company_count >= 2:
            score += 0.3

        # 5. 시계열 키워드 감지 (추이, 변화 등)
        temporal_keywords = ["6개월", "3개월", "최근", "변화", "추이", "회복", "성장"]
        if any(kw in query for kw in temporal_keywords):
            score += 0.15

        # 6. 비교 + 분석 조합 감지 (P0-1: 핵심 개선)
        # "비교 분석", "경쟁력 비교" 같은 고난이도 질의 감지
        comparison_keywords = ["비교", "대비", "vs", "versus", "경쟁"]
        analysis_keywords = ["분석", "평가", "전망", "전략", "경쟁력"]

        has_comparison = any(kw in query for kw in comparison_keywords)
        has_analysis = any(kw in query for kw in analysis_keywords)

        # 비교 + 분석 조합 = 최고 난이도 (comprehensive 필요)
        if has_comparison and has_analysis:
            score += 0.35  # 추가 보너스로 0.9+ 보장
            logger.debug(f"[복잡도] 비교+분석 조합 감지 → +0.35 보너스")

        return min(1.0, score)

    def _requires_deep_analysis(self, query: str) -> bool:
        """명시적 심층 분석 요청 키워드 감지 (개선)"""
        deep_keywords = [
            "상세히", "자세히", "보고서", "종합 분석", "비교 분석",
            "심층", "깊이", "전문적", "완벽한", "전체적",
            "추이 분석", "변화 추이", "트렌드 분석"  # 추가
        ]

        # 다중 키워드 조합 감지 (트렌드 + 비교, 추이 + 분석 등)
        has_trend = any(kw in query for kw in ["트렌드", "추이", "변화"])
        has_analysis = any(kw in query for kw in ["분석", "비교", "전략"])

        # 트렌드/추이 + 분석 조합은 심층 분석
        if has_trend and has_analysis:
            return True

        return any(kw in query for kw in deep_keywords)

    async def _route_to_langgraph(self, query: str, intent_result, tracker, complexity_score: float, force_deep: bool = False) -> Dict[str, Any]:
        """복잡한 질문을 LangGraph Multi-Agent로 라우팅 (타임아웃 처리 포함)"""

        if not self.langgraph_engine:
            logger.warning("[라우터] LangGraph 엔진 없음, 폴백 사용")
            return await self._handle_fallback(query, tracker)

        try:
            # force_deep_analysis=true 시 복잡도 점수 강제 상향
            if force_deep:
                complexity_score = max(complexity_score, 0.95)
                logger.info(f"[LangGraph] 강제 심층 분석 모드 활성화 → 복잡도 점수 강제 상향: {complexity_score:.2f}")

            # 복잡도에 따른 분석 깊이 결정 (고품질 우선 - 타임아웃 여유 확보)
            # P0-2: 각 depth별 20-30% 여유 시간 추가
            if complexity_score >= 0.9:
                analysis_depth = "comprehensive"
                timeout_seconds = 240.0  # 4분 (기존 3분 → +60초 여유, 10단계+ 워크플로우)
            elif complexity_score >= 0.85:
                analysis_depth = "deep"
                timeout_seconds = 180.0  # 3분 (기존 2분 → +60초 여유, 8단계+ 워크플로우)
            elif complexity_score >= 0.7:
                analysis_depth = "standard"
                timeout_seconds = 120.0  # 2분 (기존 1.5분 → +30초 여유, 6단계+ 워크플로우)
            else:
                analysis_depth = "shallow"
                timeout_seconds = 90.0   # 1.5분 (기존 1분 → +30초 여유, 4단계+ 워크플로우)

            logger.info(f"[LangGraph] 분석 깊이: {analysis_depth} (복잡도: {complexity_score:.2f}, 타임아웃: {timeout_seconds}초)")

            if tracker:
                tracker.start_stage("langgraph_multi_agent")

            # LangGraph 실행 (타임아웃 적용)
            try:
                result = await asyncio.wait_for(
                    self.langgraph_engine.generate_langgraph_report(
                        query=query,
                        domain=None,  # 자동 추론
                        lookback_days=30,
                        analysis_depth=analysis_depth,
                        symbol=None
                    ),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.warning(f"[LangGraph] 타임아웃 ({timeout_seconds}초) → 빠른 핸들러로 폴백")

                if tracker:
                    tracker.record_error("langgraph_timeout", "langgraph_multi_agent", f"Timeout after {timeout_seconds}s")
                    tracker.end_stage("langgraph_multi_agent")

                # 타임아웃 시 빠른 핸들러로 폴백
                return await self._handle_fallback_fast(query, intent_result, tracker)

            if tracker:
                tracker.end_stage("langgraph_multi_agent", {
                    "analysis_depth": analysis_depth,
                    "quality_score": result.get("quality_score", 0),
                    "contexts_count": result.get("contexts_count", 0),
                    "insights_count": result.get("insights_count", 0)
                })

            return {
                "type": "langgraph_analysis",
                "markdown": result.get("markdown", "보고서 생성 실패"),
                "report": result,  # 전체 리포트 데이터 포함
                "meta": {
                    "processing_method": "multi_agent_langgraph",
                    "analysis_depth": analysis_depth,
                    "complexity_score": complexity_score,
                    "quality_score": result.get("quality_score", 0),
                    "quality_level": result.get("quality_level", "unknown"),
                    "contexts_count": result.get("contexts_count", 0),
                    "insights_count": result.get("insights_count", 0),
                    "relationships_count": result.get("relationships_count", 0),
                    "processing_time": result.get("processing_time", 0.0),
                    "retry_count": result.get("retry_count", 0),
                    "execution_log": result.get("execution_log", [])
                }
            }

        except Exception as e:
            logger.error(f"[LangGraph] 처리 실패: {e}, 폴백 사용")
            if tracker:
                tracker.record_error("langgraph_error", "multi_agent", str(e))
            return await self._handle_fallback(query, tracker)

# 전역 인스턴스는 나중에 초기화