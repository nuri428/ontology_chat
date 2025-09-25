"""
종목/테마 분석 전용 핸들러
투자 분석에 특화된 처리 로직
"""

from typing import Dict, List, Any, Optional
import logging
from api.services.intent_classifier import IntentResult

logger = logging.getLogger(__name__)

class StockAnalysisHandler:
    """종목/테마 분석 전용 핸들러"""

    def __init__(self, chat_service, response_formatter):
        self.chat_service = chat_service
        self.response_formatter = response_formatter

    async def handle_stock_query(self, query: str, intent_result: IntentResult, tracker=None) -> Dict[str, Any]:
        """종목/테마 분석 질의 처리"""
        logger.info(f"[종목 분석] 처리 시작: {query}")

        # 분석 타입 결정
        analysis_type = self._determine_analysis_type(query, intent_result.extracted_entities)

        if analysis_type == "specific_company":
            # 특정 기업 분석
            response = await self._analyze_specific_company(query, intent_result)
        elif analysis_type == "theme_analysis":
            # 테마 분석
            response = await self._analyze_theme(query, intent_result)
        else:
            # 일반 투자 질문
            response = await self._general_investment_analysis(query, intent_result)

        logger.info(f"[종목 분석] 완료: {analysis_type}")
        return response

    def _determine_analysis_type(self, query: str, entities: Dict[str, List[str]]) -> str:
        """분석 타입 결정"""
        if entities.get("company"):
            return "specific_company"
        elif entities.get("theme") or any(word in query for word in ["유망주", "종목", "추천"]):
            return "theme_analysis"
        else:
            return "general_investment"

    async def _analyze_specific_company(self, query: str, intent_result: IntentResult) -> Dict[str, Any]:
        """특정 기업 분석"""
        companies = intent_result.extracted_entities.get("company", [])
        target_company = companies[0] if companies else ""

        # 기업 관련 뉴스 수집 (소량)
        news_hits = await self._get_company_news(target_company)

        # 기업 관련 그래프 데이터 수집
        graph_data = await self._get_company_graph_data(target_company)

        # 종목 중심 응답 생성
        markdown_sections = []

        # 헤더
        markdown_sections.append(f"## 📈 {target_company} 투자 분석")
        markdown_sections.append("")

        # 기업 개요
        company_overview = self._get_company_overview(target_company)
        if company_overview:
            markdown_sections.append("### 🏢 기업 개요")
            markdown_sections.extend(company_overview)
            markdown_sections.append("")

        # 최근 뉴스 (5개만)
        if news_hits:
            markdown_sections.append("### 📰 최근 주요 뉴스")
            for news in news_hits[:5]:
                source = news.get("_source", {})
                title = source.get("title", "")
                date = source.get("created_datetime", "")[:10] if source.get("created_datetime") else ""
                markdown_sections.append(f"- **{title}** ({date})")
            markdown_sections.append("")

        # 투자 포인트
        investment_points = self._generate_investment_points(target_company, news_hits)
        markdown_sections.append("### 💡 투자 포인트")
        markdown_sections.extend(investment_points)

        return {
            "type": "company_analysis",
            "markdown": "\\n".join(markdown_sections),
            "target_company": target_company,
            "news_count": len(news_hits),
            "sources": news_hits[:5],
            "meta": {
                "query": query,
                "analysis_type": "specific_company"
            }
        }

    async def _analyze_theme(self, query: str, intent_result: IntentResult) -> Dict[str, Any]:
        """테마 분석"""
        # 테마 식별
        theme = self._identify_theme(query, intent_result.extracted_entities)

        # 테마 관련 뉴스 수집
        theme_news = await self._get_theme_news(theme)

        # 추천 종목 생성
        recommended_stocks = self._get_theme_stocks(theme, query)

        # 테마 중심 응답 생성
        markdown_sections = []

        # 헤더
        markdown_sections.append(f"## 🎯 {theme} 테마 투자 분석")
        markdown_sections.append("")

        # 테마 개요
        theme_overview = self._get_theme_overview(theme)
        markdown_sections.append("### 📊 테마 개요")
        markdown_sections.extend(theme_overview)
        markdown_sections.append("")

        # 추천 종목
        if recommended_stocks.get("stocks"):
            markdown_sections.append(f"### 🏢 주요 {recommended_stocks['sector']} 종목")
            for stock in recommended_stocks["stocks"]:
                markdown_sections.append(
                    f"- **{stock['name']}** ({stock['code']}): {stock['description']}"
                )
            markdown_sections.append("")

        # 관련 뉴스 요약
        if theme_news:
            markdown_sections.append("### 📰 관련 뉴스 동향")
            for news in theme_news[:3]:
                source = news.get("_source", {})
                title = source.get("title", "")
                date = source.get("created_datetime", "")[:10] if source.get("created_datetime") else ""
                markdown_sections.append(f"- {title} ({date})")
            markdown_sections.append("")

        # 투자 전망
        investment_outlook = self._generate_theme_outlook(theme, theme_news)
        markdown_sections.append("### 🔮 투자 전망")
        markdown_sections.extend(investment_outlook)

        return {
            "type": "theme_analysis",
            "markdown": "\\n".join(markdown_sections),
            "theme": theme,
            "recommended_stocks": recommended_stocks,
            "news_count": len(theme_news),
            "meta": {
                "query": query,
                "analysis_type": "theme_analysis"
            }
        }

    async def _general_investment_analysis(self, query: str, intent_result: IntentResult) -> Dict[str, Any]:
        """일반 투자 분석"""
        # 기본 투자 조언 형태로 처리
        markdown_sections = []

        markdown_sections.append("## 💡 투자 분석")
        markdown_sections.append("")
        markdown_sections.append("### 📋 분석 결과")
        markdown_sections.append("구체적인 종목이나 테마를 명시해주시면 더 정확한 분석을 제공할 수 있습니다.")
        markdown_sections.append("")
        markdown_sections.append("**예시:**")
        markdown_sections.append("- \"삼성전자 전망은?\"")
        markdown_sections.append("- \"방산 관련 유망주는?\"")
        markdown_sections.append("- \"2차전지 테마 어때?\"")

        return {
            "type": "general_investment",
            "markdown": "\\n".join(markdown_sections),
            "meta": {
                "query": query,
                "analysis_type": "general_investment"
            }
        }

    # Helper methods
    async def _get_company_news(self, company: str) -> List[Dict[str, Any]]:
        """기업 관련 뉴스 수집"""
        try:
            hits, _, _ = await self.chat_service._search_news_simple_hybrid(company, size=10)
            return hits
        except Exception as e:
            logger.error(f"기업 뉴스 검색 실패: {e}")
            return []

    async def _get_company_graph_data(self, company: str) -> List[Dict[str, Any]]:
        """기업 관련 그래프 데이터"""
        try:
            rows, _ = await self.chat_service._graph(company)
            return rows
        except Exception as e:
            logger.error(f"그래프 데이터 검색 실패: {e}")
            return []

    async def _get_theme_news(self, theme: str) -> List[Dict[str, Any]]:
        """테마 관련 뉴스 수집"""
        try:
            hits, _, _ = await self.chat_service._search_news_simple_hybrid(theme, size=8)
            return hits
        except Exception as e:
            logger.error(f"테마 뉴스 검색 실패: {e}")
            return []

    def _identify_theme(self, query: str, entities: Dict[str, List[str]]) -> str:
        """테마 식별"""
        if entities.get("theme"):
            return entities["theme"][0]

        # 키워드 기반 테마 추정
        theme_keywords = {
            "방산/국방": ["방산", "국방", "무기", "군수"],
            "2차전지": ["2차전지", "배터리", "양극재"],
            "SMR/원전": ["SMR", "원전", "원자력"],
            "금융": ["금융", "은행", "지주회사"],
            "AI/기술": ["AI", "인공지능", "기술"]
        }

        query_lower = query.lower()
        for theme, keywords in theme_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return theme

        return "종합"

    def _get_company_overview(self, company: str) -> List[str]:
        """기업 개요 생성"""
        # 간단한 기업 정보 (실제로는 데이터베이스에서 가져와야 함)
        company_info = {
            "삼성전자": ["글로벌 반도체 및 전자제품 기업", "메모리 반도체 세계 1위", "스마트폰, 가전 사업 영위"],
            "에코프로": ["2차전지 양극재 전문기업", "전기차 배터리 소재 공급", "글로벌 시장 점유율 상승 중"]
        }

        return company_info.get(company, [f"{company} 관련 정보"])

    def _get_theme_stocks(self, theme: str, query: str) -> Dict[str, Any]:
        """테마별 추천 종목"""
        return self.response_formatter._get_fallback_stock_recommendations(query)

    def _get_theme_overview(self, theme: str) -> List[str]:
        """테마 개요"""
        theme_overviews = {
            "방산/국방": [
                "국방 산업 및 방위 산업 관련 테마",
                "해외 수출 증가로 성장성 주목",
                "정부 정책 지원과 글로벌 긴장 상황으로 수혜"
            ],
            "2차전지": [
                "전기차 확산으로 급성장하는 산업",
                "양극재, 음극재, 전해질 등 소재 기업들이 핵심",
                "글로벌 공급망에서 한국 기업들의 경쟁력 강화"
            ],
            "SMR/원전": [
                "소형 모듈 원자로 기술 개발 활발",
                "탄소 중립 정책으로 원자력 재평가",
                "원전 수출 가능성으로 관련 기업 주목"
            ]
        }

        return theme_overviews.get(theme, [f"{theme} 관련 투자 테마"])

    def _generate_investment_points(self, company: str, news_hits: List) -> List[str]:
        """투자 포인트 생성"""
        points = [
            f"**긍정 요인**: {company}의 최근 뉴스 활동도가 높아 시장 관심 증가",
            f"**주의 요인**: 전체 시장 상황과 업종별 동향 함께 고려 필요",
            f"**모니터링**: 실적 발표 및 주요 공시사항 지속 확인"
        ]

        if len(news_hits) > 5:
            points.append("**뉴스 활성도**: 최근 관련 뉴스가 활발하여 관심도 상승")

        return points

    def _generate_theme_outlook(self, theme: str, news_hits: List) -> List[str]:
        """테마 전망 생성"""
        outlook = [
            f"**단기 전망**: {theme} 테마는 최근 시장 관심이 높아지고 있음",
            f"**중기 전망**: 관련 정책 및 시장 환경 변화 지속 모니터링 필요",
            f"**투자 시 고려사항**: 개별 종목의 펀더멘털과 밸류에이션 함께 검토"
        ]

        return outlook

# 전역 인스턴스는 나중에 초기화