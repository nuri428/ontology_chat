"""
사용자 친화적 응답 포맷터
정보 계층화, 시각적 개선, 읽기 쉬운 구조 제공
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

try:
    from api.services.personalization import analyze_user_query, get_response_style
    PERSONALIZATION_AVAILABLE = True
except ImportError:
    PERSONALIZATION_AVAILABLE = False

try:
    from api.services.stock_data_service import stock_data_service
    STOCK_DATA_AVAILABLE = True
except ImportError:
    STOCK_DATA_AVAILABLE = False

@dataclass
class FormattedSection:
    """포맷된 섹션 정보"""
    title: str
    content: str
    icon: str
    priority: int
    metadata: Dict[str, Any] = None

class ResponseFormatter:
    """사용자 친화적 응답 포맷터"""
    
    def __init__(self):
        self.section_icons = {
            "query_analysis": "🔍",
            "insights": "💡",
            "stock": "📊",
            "news": "📰",
            "entities": "🏢",
            "recommendations": "🎯", 
            "market_analysis": "📈",
            "risk_warning": "⚠️",
            "additional_info": "ℹ️"
        }
        
    def format_comprehensive_answer(
        self,
        query: str,
        news_hits: List[Dict[str, Any]],
        graph_rows: List[Dict[str, Any]],
        stock: Optional[Dict[str, Any]],
        insights: Optional[str] = None,
        search_meta: Optional[Dict[str, Any]] = None
    ) -> str:
        """종합적인 답변 포맷팅 - 개인화 적용"""
        
        # 개인화 분석 비활성화 (성능 및 안정성 우선)
        response_style = None
        # if PERSONALIZATION_AVAILABLE:
        #     try:
        #         query_profile = analyze_user_query(query)
        #         response_style = get_response_style(query_profile)
        #         print(f"[DEBUG] 개인화 적용: {query_profile.query_type.value}, {query_profile.user_intent.value}")
        #     except Exception as e:
        #         print(f"[WARNING] 개인화 분석 실패: {e}")
        
        sections = []
        
        # 1. 쿼리 분석 헤더
        sections.append(self._format_query_header(query, search_meta))
        
        # 2. 컨텍스트 인사이트 (우선 표시)
        if insights:
            sections.append(FormattedSection(
                title="컨텍스트 인사이트",
                content=insights,
                icon=self.section_icons["insights"],
                priority=1
            ))
        
        # 3. 주가 정보
        if stock and stock.get("price") is not None:
            sections.append(self._format_stock_info(stock))
        
        # 4. 뉴스 요약
        if news_hits:
            sections.append(self._format_news_summary(news_hits))
            
        # 5. 관련 엔티티
        if graph_rows:
            sections.append(self._format_entities(graph_rows))
            
        # 6. 투자 관련 권장사항
        if self._is_investment_query(query):
            sections.append(self._format_investment_recommendations(query, news_hits, graph_rows))
            
        # 7. 시장 분석
        if news_hits or graph_rows:
            sections.append(self._format_market_analysis(query, news_hits, graph_rows))
            
        # 8. 추가 정보 및 주의사항
        sections.append(self._format_additional_info(query))
        
        # 9. 결과 없음 처리
        if not (news_hits or graph_rows or stock):
            sections.append(self._format_no_results_guidance(query))
        
        # 개인화에 따른 우선순위 조정
        if response_style and response_style.get("adjustments"):
            sections = self._apply_personalization(sections, response_style)
        
        # 우선순위별 정렬 및 조합
        sections.sort(key=lambda x: x.priority)
        return self._combine_sections(sections, response_style)
    
    def _format_query_header(self, query: str, search_meta: Optional[Dict] = None) -> FormattedSection:
        """쿼리 분석 헤더 포맷팅"""
        content_lines = [f"**원본 질의**: {query}"]
        
        if search_meta:
            strategy = search_meta.get("search_strategy", "")
            confidence = search_meta.get("search_confidence", 0)
            if strategy:
                content_lines.append(f"**검색 전략**: {strategy} (신뢰도: {confidence:.1%})")
        
        # 질의 타입 분석
        query_type = self._analyze_query_type(query)
        if query_type:
            content_lines.append(f"**분석 유형**: {query_type}")
        
        content = "\n".join(content_lines)
        
        return FormattedSection(
            title="질의 분석",
            content=content,
            icon=self.section_icons["query_analysis"],
            priority=0
        )
    
    def _format_stock_info(self, stock: Dict[str, Any]) -> FormattedSection:
        """주식 정보 포맷팅"""
        symbol = stock.get("symbol", "")
        price = stock.get("price", 0)
        
        # 주식 정보 테이블 형식
        content = f"""
| 항목 | 정보 |
|------|------|
| **종목코드** | `{symbol}` |
| **현재가** | **{price:,}원** |
| **업데이트** | 실시간 근사치 |

> 💡 **참고**: 실제 투자 시 최신 시세를 별도 확인하시기 바랍니다.
        """.strip()
        
        return FormattedSection(
            title="주가 스냅샷",
            content=content,
            icon=self.section_icons["stock"],
            priority=2
        )
    
    def _format_news_summary(self, news_hits: List[Dict[str, Any]]) -> FormattedSection:
        """뉴스 요약 포맷팅"""
        content_lines = []
        
        # 뉴스 개수에 따른 다른 포맷
        if len(news_hits) > 3:
            content_lines.append(f"**📊 검색 결과**: {len(news_hits)}건의 관련 뉴스")
            content_lines.append("")
            
        for i, hit in enumerate(news_hits[:5], 1):
            title = hit.get("title", "(제목 없음)")
            url = hit.get("url", "")
            date = hit.get("date", "")
            
            # 날짜 포맷팅
            formatted_date = self._format_date(date)
            
            # 뉴스 항목 포맷
            if url:
                news_line = f"**{i}.** [{title}]({url})"
            else:
                news_line = f"**{i}.** {title}"
                
            if formatted_date:
                news_line += f" `{formatted_date}`"
                
            content_lines.append(news_line)
        
        # 뉴스 트렌드 분석
        trend_analysis = self._analyze_news_trends(news_hits)
        if trend_analysis:
            content_lines.append("")
            content_lines.append("### 📊 뉴스 트렌드")
            content_lines.append(trend_analysis)
        
        return FormattedSection(
            title="관련 뉴스",
            content="\n".join(content_lines),
            icon=self.section_icons["news"],
            priority=3
        )
    
    def _format_entities(self, graph_rows: List[Dict[str, Any]]) -> FormattedSection:
        """엔티티 정보 포맷팅"""
        # 엔티티 타입별 분류
        entity_types = {}
        for r in graph_rows[:15]:  # 상위 15개만
            n = r.get("n", {})
            labels = r.get("labels", [])
            name = n.get("name") or n.get("title") or n.get("id") or n.get("contractId") or "(알 수 없음)"
            
            for label in labels:
                if label not in entity_types:
                    entity_types[label] = []
                if name not in entity_types[label]:  # 중복 방지
                    entity_types[label].append(name)
        
        content_lines = []
        
        # 타입별 우선순위
        priority_labels = ["Company", "Product", "Contract", "Program", "Person", "Country"]
        
        for label in priority_labels:
            if label in entity_types:
                entities = entity_types[label][:5]  # 상위 5개만
                remaining = len(entity_types[label]) - 5
                
                entities_text = ", ".join(f"**{entity}**" for entity in entities)
                if remaining > 0:
                    entities_text += f" _{remaining}개 더_"
                    
                content_lines.append(f"🔹 **{label}**: {entities_text}")
        
        # 나머지 라벨들
        for label, entities in entity_types.items():
            if label not in priority_labels:
                entities_limited = entities[:3]
                remaining = len(entities) - 3
                
                entities_text = ", ".join(f"**{entity}**" for entity in entities_limited)
                if remaining > 0:
                    entities_text += f" _{remaining}개 더_"
                    
                content_lines.append(f"🔹 **{label}**: {entities_text}")
        
        if not content_lines:
            content_lines.append("_관련 엔티티 정보를 찾을 수 없습니다._")
        
        return FormattedSection(
            title="관련 엔티티",
            content="\n".join(content_lines),
            icon=self.section_icons["entities"],
            priority=4
        )
    
    def _format_investment_recommendations(
        self, 
        query: str, 
        news_hits: List[Dict[str, Any]], 
        graph_rows: List[Dict[str, Any]]
    ) -> FormattedSection:
        """투자 관련 권장사항 포맷팅"""
        content_lines = []
        
        # 뉴스 기반 시장 동향 (동적 분석)
        if news_hits:
            market_trend = self._analyze_market_trend_from_news(news_hits, query)
            content_lines.extend([
                "### 📊 최근 시장 동향",
                f"- 관련 뉴스 분석 결과, {market_trend['industry']} 분야에서 **{market_trend['outlook']}**",
                f"- {market_trend['key_factor']}로 관련 기업들의 **{market_trend['expectation']}**",
                ""
            ])
        
        # 주요 관련 종목 (동적으로 엔티티에서 추출)
        companies = self._extract_companies_from_entities(graph_rows)
        if companies:
            content_lines.append("### 🏢 주요 관련 종목")
            for company in companies[:5]:
                content_lines.append(f"- **{company}**: 관련 사업 영역에서 활발한 활동")
            content_lines.append("")
        else:
            # 단순화된 종목 추천 (동적 추천 비활성화)
            recommended_stocks = self._get_fallback_stock_recommendations(query)
            content_lines.extend([
                f"### 🏢 주요 {recommended_stocks['sector']} 종목",
                *[f"- **{stock['name']}** ({stock['code']}): {stock['description']}" for stock in recommended_stocks['stocks'][:3]],
                ""
            ])
        
        # 투자 포인트 (동적 생성)
        investment_points = self._generate_investment_points_from_query(query, news_hits)
        content_lines.extend([
            "### 💡 투자 포인트",
            *[f"- **{point['title']}**: {point['description']}" for point in investment_points['positive']],
            f"- **리스크 요소**: {', '.join(investment_points['risks'])}"
        ])
        
        return FormattedSection(
            title="투자 분석 및 추천",
            content="\n".join(content_lines),
            icon=self.section_icons["recommendations"],
            priority=5
        )
    
    def _format_market_analysis(
        self, 
        query: str, 
        news_hits: List[Dict[str, Any]], 
        graph_rows: List[Dict[str, Any]]
    ) -> FormattedSection:
        """시장 분석 포맷팅"""
        content_lines = []
        
        # 뉴스 기반 영향 분석
        if news_hits:
            content_lines.extend([
                "### 📈 시장 영향 분석",
                "- 관련 뉴스가 시장에 미치는 영향을 분석하여 투자 참고자료로 활용",
                "- 긍정적 뉴스는 주가 상승 요인, 부정적 뉴스는 하락 요인으로 작용", 
                "- 뉴스의 지속성과 중요도를 고려한 투자 판단 필요",
                ""
            ])
        
        # 업계 전반 동향 (동적 분석)
        industry_trends = self._analyze_industry_trends_from_query(query, news_hits, graph_rows)
        content_lines.extend([
            f"### 🌍 {industry_trends['sector']} 산업 동향",
            *[f"- **{trend['title']}**: {trend['description']}" for trend in industry_trends['trends']]
        ])
        
        return FormattedSection(
            title="시장 분석",
            content="\n".join(content_lines),
            icon=self.section_icons["market_analysis"],
            priority=6
        )
    
    def _format_additional_info(self, query: str) -> FormattedSection:
        """추가 정보 및 주의사항"""
        # 범용 주의사항 (동적 생성)
        warning_info = self._generate_warning_info_from_query(query)
        content_lines = [
            "### ⚠️ 투자 주의사항",
            *[f"- {warning}" for warning in warning_info['warnings']],
            "",
            "### ℹ️ 추가 정보",
            *[f"- {info}" for info in warning_info['additional_info']]
        ]
        
        return FormattedSection(
            title="주의사항 및 추가정보",
            content="\n".join(content_lines),
            icon=self.section_icons["risk_warning"],
            priority=8
        )
    
    def _format_no_results_guidance(self, query: str) -> FormattedSection:
        """검색 결과 없음 시 가이드"""
        # 동적 검색 가이드 생성
        search_guide = self._generate_search_guide_from_query(query)
        content_lines = [
            "> ❌ 관련 결과를 찾지 못했습니다.",
            "",
            "### 💡 검색 개선 제안",
            *[f"- {suggestion}" for suggestion in search_guide['suggestions']],
            "",
            f"### 📊 {search_guide['sector']} 일반 동향",
            *[f"- **{trend['title']}**: {trend['description']}" for trend in search_guide['general_trends']]
        ]
        
        return FormattedSection(
            title="검색 가이드",
            content="\n".join(content_lines),
            icon="🔍",
            priority=9
        )
    
    def _apply_personalization(
        self, 
        sections: List[FormattedSection], 
        response_style: Dict[str, Any]
    ) -> List[FormattedSection]:
        """개인화 스타일 적용"""
        adjustments = response_style.get("adjustments", {})
        format_preferences = response_style.get("format_preferences", {})
        
        # 응답 길이 조정
        if adjustments.get("response_length") == "short":
            # 우선순위 높은 섹션만 유지
            sections = [s for s in sections if s.priority <= 4]
        elif adjustments.get("response_length") == "long":
            # 모든 섹션 포함하되 우선순위 조정
            for section in sections:
                if section.title in ["시장 분석", "투자 분석 및 추천"]:
                    section.priority -= 1  # 우선순위 높임
        
        # 빠른 정보 요구 시 요약 강화
        if adjustments.get("include_summary"):
            for section in sections:
                if "인사이트" in section.title or "분석" in section.title:
                    section.priority -= 1
        
        # 실행 가능한 조언 강조
        if adjustments.get("include_recommendations"):
            for section in sections:
                if "추천" in section.title or "투자" in section.title:
                    section.priority -= 2  # 높은 우선순위
        
        # 긴급도 높은 경우 핵심 포인트 강조
        if adjustments.get("prioritize_key_points"):
            for section in sections:
                if section.title in ["컨텍스트 인사이트", "주가 스냅샷"]:
                    section.priority -= 1
        
        return sections
    
    def _combine_sections(self, sections: List[FormattedSection], response_style: Optional[Dict[str, Any]] = None) -> str:
        """섹션들을 조합하여 최종 응답 생성 - 개인화 스타일 적용"""
        lines = []
        
        # 개인화 스타일 적용 여부 확인
        use_bullet_points = False
        detail_level = "medium"
        
        if response_style:
            format_prefs = response_style.get("format_preferences", {})
            use_bullet_points = format_prefs.get("use_bullet_points", False)
            detail_level = response_style.get("detail_level", "medium")
        
        for i, section in enumerate(sections):
            # 섹션 헤더
            if use_bullet_points and i > 0:  # 첫 번째 섹션 제외
                lines.append(f"### {section.icon} {section.title}")
            else:
                lines.append(f"## {section.icon} {section.title}")
            lines.append("")
            
            # 섹션 내용 (세부 수준에 따라 조정)
            content = section.content
            if detail_level == "low" and len(content) > 500:
                # 간략 모드: 내용 축약
                paragraphs = content.split("\n\n")
                content = "\n\n".join(paragraphs[:2])  # 상위 2개 문단만
                if len(paragraphs) > 2:
                    content += "\n\n_[추가 정보 생략]_"
            
            lines.append(content)
            lines.append("")
        
        # 개인화된 마무리 문구 추가
        if response_style:
            closing = self._get_personalized_closing(response_style)
            if closing:
                lines.append(closing)
        
        return "\n".join(lines)
    
    # Helper methods
    def _analyze_query_type(self, query: str) -> str:
        """질의 유형 분석"""
        q_lower = query.lower()
        
        if any(word in q_lower for word in ["종목", "주식", "투자"]):
            return "투자 관련 질의"
        elif any(word in q_lower for word in ["수출", "해외"]):
            return "수출/무역 관련 질의" 
        elif any(word in q_lower for word in ["AI", "인공지능", "기술", "개발"]):
            return "AI/기술 관련 질의"
        elif any(word in q_lower for word in ["실적", "전망"]):
            return "기업 분석 질의"
        else:
            return "일반 정보 질의"
    
    def _format_date(self, date_str: str) -> str:
        """날짜 포맷팅"""
        if not date_str:
            return ""
        
        try:
            # 다양한 날짜 형식 파싱 시도
            for fmt in ["%Y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(date_str[:10], fmt)
                    return dt.strftime("%m월 %d일")
                except:
                    continue
            return date_str[:10]  # 파싱 실패 시 원본 반환
        except:
            return ""
    
    def _analyze_news_trends(self, news_hits: List[Dict[str, Any]]) -> str:
        """뉴스 트렌드 분석"""
        if len(news_hits) < 2:
            return ""
        
        # 키워드 빈도 분석
        all_titles = " ".join([hit.get("title", "") for hit in news_hits])
        
        trend_keywords = []
        for keyword in ["수출", "증가", "성장", "확대", "계약", "협력"]:
            if keyword in all_titles:
                trend_keywords.append(keyword)
        
        if trend_keywords:
            return f"주요 트렌드: **{', '.join(trend_keywords)}** 관련 뉴스 증가"
        
        return f"총 {len(news_hits)}건의 관련 뉴스에서 일관된 관심 확인"
    
    def _extract_companies_from_entities(self, graph_rows: List[Dict[str, Any]]) -> List[str]:
        """엔티티에서 회사명 추출"""
        companies = []
        for r in graph_rows:
            labels = r.get("labels", [])
            if "Company" in labels:
                n = r.get("n", {})
                name = n.get("name") or n.get("title")
                if name and name not in companies:
                    companies.append(name)
        return companies
    
    def _is_investment_query(self, query: str) -> bool:
        """투자 관련 질의인지 판단"""
        investment_keywords = ["종목", "주식", "투자", "유망", "추천", "전망", "실적"]
        return any(keyword in query.lower() for keyword in investment_keywords)
    
    def _analyze_market_trend_from_news(self, news_hits: List[Dict[str, Any]], query: str) -> Dict[str, str]:
        """뉴스에서 시장 동향 분석"""
        # 쿼리 기반 산업 감지
        industry_map = {
            ("AI", "인공지능", "기계학습"): ("AI/인공지능", "기술 혁신 가속화", "AI 관련 투자 확대", "성장성 개선 전망"),
            ("반도체", "메모리", "칩"): ("반도체", "글로벌 수요 증가", "기술 경쟁 심화", "시장 점유율 확대 기대"),
            ("에너지", "배터리", "2차전지"): ("에너지/배터리", "친환경 전환 가속", "정부 정책 지원", "신규 투자 증가"),
            ("자동차", "전기차", "모빌리티"): ("모빌리티", "전동화 트렌드", "완성차 업체 협력", "부품 수요 증가"),
            ("바이오", "제약", "의료"): ("바이오/헬스케어", "고령화 사회 진입", "신약 개발 투자", "의료 혁신 확산")
        }

        for keywords, (industry, outlook, key_factor, expectation) in industry_map.items():
            if any(kw in query for kw in keywords):
                return {
                    "industry": industry,
                    "outlook": outlook,
                    "key_factor": key_factor,
                    "expectation": expectation
                }

        # 기본값
        return {
            "industry": "전체 시장",
            "outlook": "변동성 확대",
            "key_factor": "경제 환경 변화",
            "expectation": "선별적 투자 기회"
        }

    def _get_query_based_stock_recommendations(self, query: str) -> Dict[str, Any]:
        """쿼리 기반 동적 종목 추천 - 실시간 데이터 활용"""
        if not STOCK_DATA_AVAILABLE:
            return self._get_fallback_stock_recommendations(query)

        try:
            # 현재 실행 중인 이벤트 루프가 있는지 확인
            try:
                loop = asyncio.get_running_loop()
                # 이미 루프가 실행 중이면 폴백 사용
                print("실시간 종목 추천 실패: Cannot run the event loop while another loop is running")
                return self._get_fallback_stock_recommendations(query)
            except RuntimeError:
                # 실행 중인 루프가 없으면 새로운 루프 생성
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    stocks = loop.run_until_complete(
                        stock_data_service.search_stocks_by_query(query, limit=3)
                    )
                finally:
                    loop.close()

            if stocks:
                # 첫 번째 종목의 섹터를 기준으로 섹터명 결정
                sector = stocks[0].sector if stocks else "종합"

                stock_list = []
                for stock in stocks:
                    description = f"{stock.industry}"
                    if stock.change_percent is not None:
                        direction = "상승" if stock.change_percent > 0 else "하락"
                        description += f", 전일대비 {stock.change_percent:.1f}% {direction}"

                    stock_list.append({
                        "name": stock.name,
                        "code": stock.symbol.replace('.KS', ''),
                        "description": description
                    })

                return {
                    "sector": sector,
                    "stocks": stock_list
                }
            else:
                return self._get_fallback_stock_recommendations(query)

        except Exception as e:
            print(f"실시간 종목 추천 실패: {e}")
            return self._get_fallback_stock_recommendations(query)

    def _get_fallback_stock_recommendations(self, query: str) -> Dict[str, Any]:
        """실시간 데이터 실패 시 폴백 추천"""
        # 기존 하드코딩 로직을 폴백으로 유지
        basic_recommendations = {
            ("AI", "인공지능"): ("AI/인공지능", [
                {"name": "네이버", "code": "035420", "description": "AI 검색, 클라우드 플랫폼"},
                {"name": "카카오", "code": "035720", "description": "AI 서비스, 디지털 플랫폼"}
            ]),
            ("반도체", "메모리"): ("반도체", [
                {"name": "삼성전자", "code": "005930", "description": "메모리 반도체 글로벌 1위"},
                {"name": "SK하이닉스", "code": "000660", "description": "메모리 반도체 2위"}
            ]),
            ("방산", "국방", "무기", "군수", "방위산업"): ("방산/국방", [
                {"name": "한화시스템", "code": "272210", "description": "방산 전자장비, 해외수주 증가"},
                {"name": "한화에어로스페이스", "code": "012450", "description": "항공엔진, 방산부품 전문"},
                {"name": "LIG넥스원", "code": "079550", "description": "방산 전자 시스템, 레이더"}
            ]),
            ("SMR", "원전", "원자력"): ("원전/SMR", [
                {"name": "한국전력", "code": "015760", "description": "전력 공급, 원전 운영"},
                {"name": "한전KPS", "code": "051600", "description": "발전설비 유지보수, 원전 기술"},
                {"name": "한국원자력연료", "code": "007340", "description": "핵연료 제조, SMR 기술 보유"}
            ]),
            ("2차전지", "이차전지", "배터리", "양극재"): ("2차전지/배터리", [
                {"name": "에코프로", "code": "086520", "description": "양극재 선도업체, 전기차 배터리"},
                {"name": "에코프로비엠", "code": "247540", "description": "배터리 양극재 전문, 글로벌 점유율"},
                {"name": "포스코퓨처엠", "code": "003670", "description": "양극재, 음극재 통합 생산"}
            ]),
            ("금융", "지주회사", "은행"): ("금융지주", [
                {"name": "KB금융", "code": "105560", "description": "국내 최대 금융지주, 디지털 혁신"},
                {"name": "신한지주", "code": "055550", "description": "종합금융 서비스, 아시아 진출"},
                {"name": "하나금융지주", "code": "086790", "description": "중소기업 금융 강점, 핀테크"}
            ])
        }

        for keywords, (sector, stocks) in basic_recommendations.items():
            if any(kw in query for kw in keywords):
                return {"sector": sector, "stocks": stocks}

        return {
            "sector": "종합",
            "stocks": [
                {"name": "삼성전자", "code": "005930", "description": "한국 대표 기술주"},
                {"name": "LG전자", "code": "066570", "description": "가전 및 전자 부품"}
            ]
        }

    def _generate_investment_points_from_query(self, query: str, news_hits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """쿼리 기반 투자 포인트 생성"""
        investment_points = {
            ("AI", "인공지능"): {
                "positive": [
                    {"title": "기술 혁신", "description": "AI 기술 발전으로 새로운 시장 창출 및 비즈니스 모델 혁신"},
                    {"title": "정부 지원", "description": "K-디지털 뉴딜 정책으로 AI 분야 투자 및 지원 확대"},
                    {"title": "글로벌 확장", "description": "AI 기술력 기반 해외 시장 진출 기회 증가"}
                ],
                "risks": ["기술 변화 속도", "규제 리스크", "인재 확보 경쟁"]
            },
            ("반도체", "메모리"): {
                "positive": [
                    {"title": "수요 증가", "description": "AI, 데이터센터 확산으로 고성능 메모리 수요 급증"},
                    {"title": "기술 우위", "description": "첨단 공정 기술력으로 글로벌 경쟁 우위 유지"},
                    {"title": "가격 회복", "description": "메모리 가격 사이클 상승 구간 진입 기대"}
                ],
                "risks": ["경기 민감도", "중국 경쟁", "설비투자 부담"]
            }
        }

        for keywords, points in investment_points.items():
            if any(kw in query for kw in keywords):
                return points

        # 기본값
        return {
            "positive": [
                {"title": "시장 성장", "description": "관련 산업의 지속적인 성장 전망"},
                {"title": "기업 경쟁력", "description": "국내 대표 기업들의 글로벌 경쟁력 보유"},
                {"title": "정책 지원", "description": "정부의 산업 육성 정책 및 지원 정책"}
            ],
            "risks": ["시장 변동성", "경기 민감도", "환율 리스크", "경쟁 심화"]
        }

    def _analyze_industry_trends_from_query(self, query: str, news_hits: List[Dict[str, Any]], graph_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """쿼리 기반 산업 동향 분석"""
        industry_trends = {
            ("AI", "인공지능"): {
                "sector": "AI/인공지능",
                "trends": [
                    {"title": "생성형 AI 확산", "description": "ChatGPT 등 생성형 AI 서비스의 급속한 확산"},
                    {"title": "AI 반도체 경쟁", "description": "AI 가속 칩 시장에서의 기술 경쟁 심화"},
                    {"title": "산업 적용 확대", "description": "제조, 금융, 의료 등 전 산업 AI 도입 가속"}
                ]
            },
            ("반도체", "메모리"): {
                "sector": "반도체",
                "trends": [
                    {"title": "AI 메모리 수요", "description": "AI 연산용 고대역폭 메모리(HBM) 수요 급증"},
                    {"title": "지정학적 리스크", "description": "미중 기술패권 경쟁으로 공급망 재편"},
                    {"title": "차세대 기술", "description": "3나노 이하 초미세 공정 기술 경쟁"}
                ]
            }
        }

        for keywords, trends in industry_trends.items():
            if any(kw in query for kw in keywords):
                return trends

        # 기본값
        return {
            "sector": "전체 산업",
            "trends": [
                {"title": "디지털 전환", "description": "전 산업의 디지털 전환 가속화"},
                {"title": "ESG 경영", "description": "지속가능경영 및 친환경 기술 중요성 증대"},
                {"title": "글로벌 공급망", "description": "공급망 다변화 및 리쇼어링 트렌드"}
            ]
        }

    def _generate_warning_info_from_query(self, query: str) -> Dict[str, List[str]]:
        """쿼리 기반 주의사항 생성"""
        return {
            "warnings": [
                "투자 결정 전 충분한 리서치와 리스크 관리 필요",
                "단기 변동성이 클 수 있으므로 장기 투자 관점 권장",
                "시장 상황과 기업 실적을 지속적으로 모니터링",
                "전문가 상담 후 신중한 투자 결정 권장"
            ],
            "additional_info": [
                "실시간 뉴스와 공시 정보를 지속적으로 모니터링",
                "전문가 의견과 시장 분석 리포트 참고",
                "분산 투자를 통한 리스크 관리",
                "개별 기업의 펀더멘털 분석 중요"
            ]
        }

    def _generate_search_guide_from_query(self, query: str) -> Dict[str, Any]:
        """쿼리 기반 검색 가이드 생성"""
        # 쿼리 분석하여 관련 산업 감지
        if any(kw in query for kw in ["AI", "인공지능"]):
            sector = "AI/인공지능"
            suggestions = [
                "'인공지능', 'AI', '기계학습' 등의 구체적 키워드 사용",
                "특정 기업명과 함께 검색 (예: '네이버 AI', '카카오 인공지능')",
                "'생성형 AI', 'ChatGPT', 'LLM' 등 세부 기술 키워드 활용"
            ]
            general_trends = [
                {"title": "생성형 AI 시장 확대", "description": "ChatGPT 성공으로 생성형 AI 서비스 경쟁 치열"},
                {"title": "AI 반도체 투자", "description": "AI 연산 전용 반도체 개발 투자 증가"},
                {"title": "AI 규제 논의", "description": "AI 윤리 및 규제 프레임워크 구축 논의"}
            ]
        else:
            sector = "전체 시장"
            suggestions = [
                "키워드를 더 구체적으로 입력해 보세요",
                "시간 범위를 조정해 보세요 (예: '최근 1년')",
                "영문명과 한글명을 함께 사용해 보세요"
            ]
            general_trends = [
                {"title": "글로벌 경제 불확실성", "description": "인플레이션 및 금리 정책 변화 영향"},
                {"title": "기술주 선호", "description": "AI, 반도체 등 기술 관련 종목 선호 지속"},
                {"title": "ESG 투자 확산", "description": "지속가능투자 및 ESG 경영 중요성 증대"}
            ]

        return {
            "sector": sector,
            "suggestions": suggestions,
            "general_trends": general_trends
        }

    def _get_personalized_closing(self, response_style: Dict[str, Any]) -> str:
        """개인화된 마무리 문구 생성"""
        adjustments = response_style.get("adjustments", {})
        tone = response_style.get("tone", "중립적")

        # 기본 마무리 문구들
        closings = {
            "quick": "💡 **더 궁금한 점이 있으시면 구체적인 키워드로 다시 문의해 주세요.**",
            "detailed": "📚 **추가적인 분석이나 특정 영역에 대한 심화 정보가 필요하시면 언제든 문의하세요.**",
            "actionable": "🎯 **투자 결정 전 반드시 최신 정보를 확인하시고, 전문가와 상담 후 신중히 결정하시기 바랍니다.**",
            "educational": "📖 **학습에 도움이 되셨기를 바라며, 궁금한 개념이나 용어가 있으시면 추가 질문 주세요.**",
            "urgent": "⚡ **실시간 정보와 최신 상황을 별도로 확인하시어 신속한 판단에 참고하시기 바랍니다.**"
        }

        # 조정사항에 따른 마무리 선택
        if adjustments.get("response_length") == "short":
            return closings["quick"]
        elif adjustments.get("include_recommendations"):
            return closings["actionable"]
        elif adjustments.get("explain_concepts"):
            return closings["educational"]
        elif adjustments.get("prioritize_key_points"):
            return closings["urgent"]
        elif adjustments.get("comprehensive_coverage"):
            return closings["detailed"]

        return closings["quick"]  # 기본값

# 전역 인스턴스
response_formatter = ResponseFormatter()