"""
질의 라우팅 시스템
사용자 질의를 의도별로 분석하여 적절한 핸들러로 라우팅
"""

from typing import Dict, Any, List
import logging
import time

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
    """질의 라우팅 및 처리 관리자"""

    def __init__(self, chat_service, response_formatter):
        self.chat_service = chat_service
        self.response_formatter = response_formatter

        # 핸들러 초기화
        self.news_handler = NewsQueryHandler(chat_service)
        self.stock_handler = StockAnalysisHandler(chat_service, response_formatter)

    async def process_query(self, query: str, user_id: str = "anonymous", session_id: str = None) -> Dict[str, Any]:
        """질의 처리 메인 엔트리포인트 (트레이싱 포함)"""
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

                # 2. 의도별 핸들러로 라우팅
                tracker.start_stage("query_processing")

                if intent_result.intent == QueryIntent.NEWS_INQUIRY:
                    response = await self.news_handler.handle_news_query(query, intent_result, tracker)

                elif intent_result.intent == QueryIntent.STOCK_ANALYSIS:
                    response = await self.stock_handler.handle_stock_query(query, intent_result, tracker)

                elif intent_result.intent == QueryIntent.GENERAL_QA:
                    response = await self._handle_general_qa(query, intent_result, tracker)

                else:
                    # UNKNOWN이거나 분류 실패한 경우 - 기존 방식 사용
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

# 전역 인스턴스는 나중에 초기화