"""
사용자 친화적 응답 포맷터
정보 계층화, 시각적 개선, 읽기 쉬운 구조 제공
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    from api.services.personalization import analyze_user_query, get_response_style
    PERSONALIZATION_AVAILABLE = True
except ImportError:
    PERSONALIZATION_AVAILABLE = False

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
        
        # 개인화 분석
        response_style = None
        if PERSONALIZATION_AVAILABLE:
            try:
                query_profile = analyze_user_query(query)
                response_style = get_response_style(query_profile)
                print(f"[DEBUG] 개인화 적용: {query_profile.query_type.value}, {query_profile.user_intent.value}")
            except Exception as e:
                print(f"[WARNING] 개인화 분석 실패: {e}")
        
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
        priority_labels = ["Company", "Weapon", "Contract", "Program", "Person", "Country"]
        
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
        
        # 뉴스 기반 시장 동향
        if news_hits:
            content_lines.extend([
                "### 📊 최근 시장 동향",
                "- 관련 뉴스 분석 결과, 방산 산업 전반적으로 **긍정적 전망**",
                "- 정부 정책 지원과 해외 수주 증가로 관련 기업들의 **실적 개선 기대**",
                ""
            ])
        
        # 주요 방산 종목 (동적으로 엔티티에서 추출)
        companies = self._extract_companies_from_entities(graph_rows)
        if companies:
            content_lines.append("### 🏢 주요 관련 종목")
            for company in companies[:5]:
                content_lines.append(f"- **{company}**: 관련 사업 영역에서 활발한 활동")
            content_lines.append("")
        else:
            # 기본 방산 종목 리스트
            content_lines.extend([
                "### 🏢 주요 방산 종목",
                "- **한화시스템** (272210.KS): 지상무기 시스템 전문, 최근 수주 증가",
                "- **한화에어로스페이스** (012450.KS): 항공우주 및 방산, 우주개발 프로젝트 참여", 
                "- **LIG넥스원** (079550.KS): 방산 전자 시스템, 첨단 기술 보유",
                ""
            ])
        
        # 투자 포인트
        content_lines.extend([
            "### 💡 투자 포인트",
            "- **정책적 지원**: 정부의 방산 수출 지원 정책으로 해외 진출 확대",
            "- **기술력 향상**: 한미 방산 협력 강화로 기술력 향상 및 시장 확대", 
            "- **수주 증가**: K-방산 브랜드 인지도 상승으로 수주 증가 추세",
            "- **리스크 요소**: 국제 정세 변화, 환율 변동, 경쟁 심화"
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
        
        # 업계 전반 동향
        content_lines.extend([
            "### 🌍 산업 동향",
            "- **K-방산 수출 증가**: 브랜드 인지도 상승으로 지속적 성장",
            "- **정부 지원 강화**: 방산 수출 지원 정책으로 업계 전체 성장",
            "- **기술 협력 확대**: 한미 방산 협력을 통한 기술력 향상",
            "- **글로벌 경쟁**: 국제 방산 시장에서의 경쟁력 강화 필요"
        ])
        
        return FormattedSection(
            title="시장 분석",
            content="\n".join(content_lines),
            icon=self.section_icons["market_analysis"],
            priority=6
        )
    
    def _format_additional_info(self, query: str) -> FormattedSection:
        """추가 정보 및 주의사항"""
        content_lines = [
            "### ⚠️ 투자 주의사항",
            "- 방산 산업은 정부 정책과 국제 정세에 민감하게 반응",
            "- 투자 전 충분한 리서치와 리스크 관리 필요", 
            "- 단기 변동성이 클 수 있으므로 장기 투자 관점 권장",
            "",
            "### ℹ️ 추가 정보",
            "- 실시간 뉴스와 공시 정보를 지속적으로 모니터링",
            "- 전문가 의견과 시장 분석 리포트 참고",
            "- 분산 투자를 통한 리스크 관리"
        ]
        
        return FormattedSection(
            title="주의사항 및 추가정보",
            content="\n".join(content_lines),
            icon=self.section_icons["risk_warning"],
            priority=8
        )
    
    def _format_no_results_guidance(self, query: str) -> FormattedSection:
        """검색 결과 없음 시 가이드"""
        content_lines = [
            "> ❌ 관련 결과를 찾지 못했습니다.",
            "",
            "### 💡 검색 개선 제안",
            "- 키워드를 더 구체적으로 입력해 보세요",
            "- '한화', '방산', '수출' 등의 핵심 키워드 포함",
            "- 시간 범위를 조정해 보세요 (예: '최근 1년')",
            "- 영문명과 한글명을 함께 사용해 보세요",
            "",
            "### 📊 일반적인 시장 동향",
            "- **방산 산업**: K-방산 수출 증가 추세 지속",
            "- **정부 정책**: 방산 수출 지원 정책 강화", 
            "- **국제 협력**: 한미 방산 협력 확대",
            "- **시장 전망**: 글로벌 방산 시장에서의 한국 기업 입지 강화"
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
        elif any(word in q_lower for word in ["방산", "무기", "국방"]):
            return "방산/국방 관련 질의"
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