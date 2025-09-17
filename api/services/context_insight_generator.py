"""
LLM 기반 동적 컨텍스트 인사이트 생성기
사용자 질의와 검색 결과를 바탕으로 의미있는 인사이트를 자동 생성
"""
import json
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from api.logging import setup_logging
logger = setup_logging()

try:
    from api.utils.llm_keyword_extractor_simple import SimpleLLMKeywordExtractor
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

from api.logging import setup_logging
logger = setup_logging()

try:
    from api.services.cache_manager import cache_decorator
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

@dataclass
class ContextInsight:
    """컨텍스트 인사이트 정보"""
    title: str
    content: str
    icon: str
    category: str
    confidence: float
    sources: List[str] = None

@dataclass
class InsightGenerationResult:
    """인사이트 생성 결과"""
    insights: List[ContextInsight]
    overall_context: str
    confidence: float
    reasoning: str

class ContextInsightGenerator:
    """LLM 기반 컨텍스트 인사이트 생성기"""
    
    def __init__(self):
        if not LLM_AVAILABLE:
            logger.warning("LLM이 사용 불가능하여 기본 인사이트만 제공됩니다")
            self.llm_extractor = None
        else:
            self.llm_extractor = SimpleLLMKeywordExtractor()
    
    async def generate_insights(
        self, 
        query: str, 
        news_hits: List[Dict] = None,
        graph_summary: Dict = None,
        stock_info: Dict = None
    ) -> InsightGenerationResult:
        """질의와 검색 결과를 바탕으로 컨텍스트 인사이트 생성"""
        
        # 캐싱 적용 (30분)
        if CACHE_AVAILABLE:
            from api.services.cache_manager import cache_manager
            
            # 캐시 키 생성용 간단한 해시
            cache_key_data = f"{query}_{len(news_hits) if news_hits else 0}_{bool(graph_summary)}_{bool(stock_info)}"
            cached_result = cache_manager.get("insight_generation", cache_key_data)
            if cached_result:
                logger.debug("인사이트 생성 캐시 히트")
                return cached_result
        
        # 실제 인사이트 생성
        result = await self._generate_insights_impl(query, news_hits, graph_summary, stock_info)
        
        # 캐시에 저장 (30분)
        if CACHE_AVAILABLE and result.confidence > 0.3:
            cache_manager.set("insight_generation", result, ttl=1800.0, cache_key=cache_key_data)
        
        return result
    
    async def _generate_insights_impl(
        self, 
        query: str, 
        news_hits: List[Dict] = None,
        graph_summary: Dict = None,
        stock_info: Dict = None
    ) -> InsightGenerationResult:
        """질의와 검색 결과를 바탕으로 컨텍스트 인사이트 생성"""
        
        if not self.llm_extractor:
            return self._fallback_insights(query, news_hits, graph_summary, stock_info)
        
        try:
            # 컨텍스트 정보 준비
            context_data = self._prepare_context_data(query, news_hits, graph_summary, stock_info)
            
            # LLM으로 인사이트 생성
            insights_result = await self._generate_llm_insights(query, context_data)
            
            if insights_result.confidence > 0.3:
                return insights_result
            else:
                logger.warning("LLM 인사이트 신뢰도가 낮아 폴백 사용")
                return self._fallback_insights(query, news_hits, graph_summary, stock_info)
                
        except Exception as e:
            logger.error(f"인사이트 생성 실패: {e}")
            return self._fallback_insights(query, news_hits, graph_summary, stock_info)
    
    def _prepare_context_data(
        self, 
        query: str, 
        news_hits: List[Dict], 
        graph_summary: Dict, 
        stock_info: Dict
    ) -> str:
        """컨텍스트 데이터 준비"""
        context_parts = [f"사용자 질의: {query}"]
        
        # 뉴스 요약
        if news_hits:
            news_titles = [hit.get("title", "") for hit in news_hits[:5]]
            context_parts.append(f"관련 뉴스: {', '.join(news_titles)}")
        
        # 그래프 컨텍스트
        if graph_summary:
            context_parts.append(f"관련 엔티티: {graph_summary}")
        
        # 주식 정보
        if stock_info:
            context_parts.append(f"주식 정보: {stock_info.get('symbol', '')} - {stock_info.get('price', '')}")
        
        return " | ".join(context_parts)
    
    async def _generate_llm_insights(self, query: str, context_data: str) -> InsightGenerationResult:
        """LLM을 활용한 인사이트 생성"""
        
        insight_prompt = f"""You are a Korean business analyst. Generate business insights in JSON format only.

Query: "{query}"
Context: {context_data}

Generate insights about Korean business trends, focusing on defense industry, exports, and investments.

Return ONLY valid JSON (no explanations, no markdown):
{{"insights":[{{"title":"방산 수출 확대","content":"K-방산 수출 증가로 관련 기업들의 성장이 예상됩니다","icon":"🚀","category":"market","confidence":0.8,"sources":["news"]}},{{"title":"정부 지원 정책","content":"방산 수출 지원 정책이 업계 성장을 뒷받침합니다","icon":"🏛️","category":"policy","confidence":0.9,"sources":["policy"]}}],"overall_context":"방산업계 성장세 지속","confidence":0.85,"reasoning":"뉴스와 시장 동향 분석 결과"}}"""

        try:
            # LLM 호출 (직접 호출)
            response = self.llm_extractor.llm.invoke(insight_prompt)
            
            # JSON 파싱
            parsed_result = self._parse_insight_response(response)
            
            if parsed_result:
                return parsed_result
            else:
                raise Exception("JSON 파싱 실패")
                
        except Exception as e:
            logger.error(f"LLM 인사이트 생성 실패: {e}")
            raise
    
    def _parse_insight_response(self, response: str) -> Optional[InsightGenerationResult]:
        """LLM 인사이트 응답 파싱"""
        try:
            # JSON 추출
            json_str = self._extract_json_from_response(response)
            parsed = json.loads(json_str)
            
            # 인사이트 객체 생성
            insights = []
            for insight_data in parsed.get("insights", []):
                insight = ContextInsight(
                    title=insight_data.get("title", ""),
                    content=insight_data.get("content", ""),
                    icon=insight_data.get("icon", "📊"),
                    category=insight_data.get("category", "general"),
                    confidence=insight_data.get("confidence", 0.5),
                    sources=insight_data.get("sources", [])
                )
                insights.append(insight)
            
            return InsightGenerationResult(
                insights=insights,
                overall_context=parsed.get("overall_context", ""),
                confidence=parsed.get("confidence", 0.5),
                reasoning=parsed.get("reasoning", "")
            )
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"인사이트 JSON 파싱 오류: {e}")
            return None
    
    def _extract_json_from_response(self, response: str) -> str:
        """응답에서 JSON 부분 추출"""
        response = response.strip()
        
        # 마크다운 코드 블록 제거
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        # JSON 객체 찾기
        start = response.find("{")
        if start >= 0:
            brace_count = 0
            for i, char in enumerate(response[start:], start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return response[start:i+1]
        
        return response
    
    def _fallback_insights(
        self, 
        query: str, 
        news_hits: List[Dict], 
        graph_summary: Dict, 
        stock_info: Dict
    ) -> InsightGenerationResult:
        """기본 인사이트 (LLM 실패 시 폴백)"""
        
        q_lower = query.lower()
        insights = []
        
        # 도메인별 기본 인사이트
        if "지상무기" in q_lower or "방산" in q_lower:
            insights.append(ContextInsight(
                title="방산 산업 성장",
                content="K-방산 수출 증가와 정부 지원 정책으로 국내 방산업계가 성장하고 있습니다.",
                icon="🔫",
                category="defense",
                confidence=0.7
            ))
        
        if "수출" in q_lower:
            insights.append(ContextInsight(
                title="해외 진출 확대",
                content="글로벌 시장 진출과 수출 다변화를 통한 성장 기회가 확대되고 있습니다.",
                icon="🌍",
                category="export",
                confidence=0.6
            ))
        
        if "종목" in q_lower or "주식" in q_lower:
            insights.append(ContextInsight(
                title="투자 기회 분석",
                content="관련 기업들의 실적 개선과 시장 전망을 통한 투자 가치를 검토해볼 수 있습니다.",
                icon="📈",
                category="investment",
                confidence=0.6
            ))
        
        if "최근" in q_lower or "최신" in q_lower:
            insights.append(ContextInsight(
                title="최신 동향",
                content="2024-2025년 최신 이슈와 정책 변화, 시장 반응을 주목할 필요가 있습니다.",
                icon="⏰",
                category="trend",
                confidence=0.5
            ))
        
        # 뉴스 기반 인사이트
        if news_hits and len(news_hits) >= 3:
            insights.append(ContextInsight(
                title="언론 관심도",
                content=f"관련 뉴스 {len(news_hits)}건이 보도되어 높은 시장 관심을 보이고 있습니다.",
                icon="📰",
                category="media",
                confidence=0.8
            ))
        
        return InsightGenerationResult(
            insights=insights[:4],  # 최대 4개
            overall_context="검색 결과를 바탕으로 한 기본 컨텍스트 분석입니다.",
            confidence=0.4,
            reasoning="LLM을 사용할 수 없어 기본 규칙 기반 인사이트를 제공합니다."
        )
    
    def format_insights_for_display(self, result: InsightGenerationResult) -> str:
        """인사이트를 디스플레이용 마크다운으로 포맷팅"""
        if not result.insights:
            return ""
        
        lines = ["### 🔍 컨텍스트 인사이트\n"]
        
        for insight in result.insights:
            lines.append(f"- {insight.icon} **{insight.title}**: {insight.content}")
        
        if result.overall_context:
            lines.append(f"\n**💡 종합 분석**: {result.overall_context}")
        
        lines.append("")
        return "\n".join(lines)

# 기본 인스턴스
insight_generator = ContextInsightGenerator()