"""
컨텍스트 기반 답변 생성 시스템
검색된 실제 데이터를 활용한 의미 있는 답변 생성
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class ContextAnswerGenerator:
    """컨텍스트 기반 답변 생성기"""

    def __init__(self):
        pass

    def generate_context_based_answer(
        self,
        query: str,
        intent: str,
        search_results: Dict[str, Any],
        entities: Dict[str, List[str]] = None
    ) -> str:
        """검색 결과를 활용한 컨텍스트 기반 답변 생성"""

        logger.info(f"[답변생성] 의도: {intent}, 검색결과: {len(search_results.get('sources', []))}건")

        if intent == "news_inquiry":
            return self._generate_news_answer(query, search_results, entities)
        elif intent == "stock_analysis":
            return self._generate_stock_analysis_answer(query, search_results, entities)
        else:
            return self._generate_general_answer(query, search_results, entities)

    def _generate_news_answer(
        self,
        query: str,
        search_results: Dict[str, Any],
        entities: Dict[str, List[str]] = None
    ) -> str:
        """뉴스 조회 답변 생성"""

        sources = search_results.get("sources", [])
        if not sources:
            return self._generate_no_results_answer(query, "뉴스")

        # 뉴스 답변 구조 생성
        answer_sections = []

        # 헤더 - 엔티티 기반
        entity_str = ""
        if entities:
            if entities.get("company"):
                entity_str = f" - {', '.join(entities['company'][:3])}"
            elif entities.get("product"):
                entity_str = f" - {', '.join(entities['product'][:3])}"

        answer_sections.append(f"## 📰 뉴스 조회 결과{entity_str}")
        answer_sections.append("")

        # 핵심 요약
        answer_sections.append("### 🔍 핵심 요약")
        summary = self._extract_key_summary(query, sources)
        answer_sections.append(summary)
        answer_sections.append("")

        # 주요 뉴스 목록
        answer_sections.append("### 📋 주요 뉴스")
        for i, source in enumerate(sources[:5], 1):
            title = source.get("title", "제목 없음")
            url = source.get("url", "")
            date = source.get("date", "")[:10] if source.get("date") else ""
            media = source.get("media", "")

            answer_sections.append(f"{i}. **{title}**")

            # 메타 정보
            meta_parts = []
            if media:
                meta_parts.append(media)
            if date:
                meta_parts.append(date)
            if meta_parts:
                answer_sections.append(f"   *{' | '.join(meta_parts)}*")

            if url:
                answer_sections.append(f"   🔗 [기사 보기]({url})")

            answer_sections.append("")

        # 관련 정보
        if entities:
            answer_sections.append("### 📊 관련 정보")
            if entities.get("company"):
                answer_sections.append("**관련 종목:**")
                for company in entities["company"][:3]:
                    answer_sections.append(f"- {company}")
                answer_sections.append("")

        return "\n".join(answer_sections)

    def _generate_stock_analysis_answer(
        self,
        query: str,
        search_results: Dict[str, Any],
        entities: Dict[str, List[str]] = None
    ) -> str:
        """종목 분석 답변 생성"""

        sources = search_results.get("sources", [])
        if not sources:
            return self._generate_no_results_answer(query, "분석 정보")

        answer_sections = []

        # 헤더
        answer_sections.append("## 📊 투자 분석 결과")
        answer_sections.append("")

        # 질의 분석
        answer_sections.append("### 🔍 질의 분석")
        analysis_summary = self._extract_investment_context(query, sources)
        answer_sections.append(analysis_summary)
        answer_sections.append("")

        # 관련 뉴스/정보
        answer_sections.append("### 📰 관련 정보")
        for i, source in enumerate(sources[:3], 1):
            title = source.get("title", "정보 없음")
            url = source.get("url", "")

            answer_sections.append(f"{i}. {title}")
            if url:
                answer_sections.append(f"   🔗 [자세히 보기]({url})")
            answer_sections.append("")

        # 투자 관련 엔티티 정보
        if entities:
            if entities.get("company"):
                answer_sections.append("### 🏢 관련 종목")
                for company in entities["company"][:5]:
                    answer_sections.append(f"- **{company}**")
                answer_sections.append("")

            if entities.get("theme"):
                answer_sections.append("### 🎯 관련 테마")
                for theme in entities["theme"][:3]:
                    answer_sections.append(f"- {theme}")
                answer_sections.append("")

        return "\n".join(answer_sections)

    def _generate_general_answer(
        self,
        query: str,
        search_results: Dict[str, Any],
        entities: Dict[str, List[str]] = None
    ) -> str:
        """일반 답변 생성"""

        sources = search_results.get("sources", [])

        answer_sections = []
        answer_sections.append("## 💡 조회 결과")
        answer_sections.append("")

        if sources:
            answer_sections.append("### 📋 관련 정보")
            for i, source in enumerate(sources[:3], 1):
                title = source.get("title", "정보 없음")
                url = source.get("url", "")

                answer_sections.append(f"{i}. {title}")
                if url:
                    answer_sections.append(f"   🔗 [자세히 보기]({url})")
                answer_sections.append("")
        else:
            answer_sections.append("요청하신 정보를 찾지 못했습니다.")
            answer_sections.append("다른 키워드로 다시 검색해보세요.")

        return "\n".join(answer_sections)

    def _extract_key_summary(self, query: str, sources: List[Dict]) -> str:
        """핵심 요약 추출"""
        if not sources:
            return "관련 뉴스를 찾을 수 없습니다."

        # 간단한 요약 로직
        titles = [source.get("title", "") for source in sources[:3] if source.get("title")]

        if not titles:
            return "뉴스 제목을 추출할 수 없습니다."

        # 공통 키워드 추출
        common_keywords = self._extract_common_keywords(titles)

        if len(sources) == 1:
            return f"**{titles[0]}** 관련 뉴스 1건을 찾았습니다."
        else:
            if common_keywords:
                keyword_str = ", ".join(common_keywords[:3])
                return f"**{keyword_str}** 관련하여 {len(sources)}건의 뉴스를 찾았습니다."
            else:
                return f"관련 뉴스 {len(sources)}건을 찾았습니다."

    def _extract_investment_context(self, query: str, sources: List[Dict]) -> str:
        """투자 관련 컨텍스트 추출"""
        if not sources:
            return "관련 투자 정보를 찾을 수 없습니다."

        # 실적, 전망 관련 키워드 찾기
        investment_keywords = ["실적", "전망", "매출", "영업이익", "주가", "투자", "분석"]

        titles = [source.get("title", "") for source in sources[:3]]
        relevant_titles = []

        for title in titles:
            if any(keyword in title for keyword in investment_keywords):
                relevant_titles.append(title)

        if relevant_titles:
            return f"**{relevant_titles[0][:50]}...** 등 {len(sources)}건의 관련 정보를 찾았습니다."
        else:
            return f"관련 투자 정보 {len(sources)}건을 찾았습니다."

    def _extract_common_keywords(self, titles: List[str]) -> List[str]:
        """제목에서 공통 키워드 추출"""
        if not titles:
            return []

        # 간단한 공통 키워드 추출
        all_words = []
        for title in titles:
            words = re.findall(r'[가-힣A-Za-z0-9]+', title)
            all_words.extend(words)

        # 빈도 계산
        word_count = {}
        for word in all_words:
            if len(word) > 1:  # 2글자 이상만
                word_count[word] = word_count.get(word, 0) + 1

        # 2번 이상 나온 단어들만 추출
        common_words = [word for word, count in word_count.items() if count >= 2]

        return common_words[:5]  # 상위 5개

    def _generate_no_results_answer(self, query: str, result_type: str) -> str:
        """검색 결과가 없을 때 답변"""
        return f"""## ⚠️ {result_type} 검색 결과

요청하신 **"{query}"**에 대한 {result_type}를 찾을 수 없습니다.

### 💡 검색 팁
- 더 구체적인 키워드로 검색해보세요
- 회사명이나 종목명을 정확히 입력해보세요
- 다른 표현으로 질문해보세요

### 📞 문의
추가 도움이 필요하시면 시스템 관리자에게 문의해주세요."""

# 전역 인스턴스
context_answer_generator = ContextAnswerGenerator()

def generate_context_answer(
    query: str,
    intent: str,
    search_results: Dict[str, Any],
    entities: Dict[str, List[str]] = None
) -> str:
    """컨텍스트 기반 답변 생성 (편의 함수)"""
    return context_answer_generator.generate_context_based_answer(
        query, intent, search_results, entities
    )