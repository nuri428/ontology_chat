"""
뉴스 조회 전용 핸들러
뉴스 검색에 특화된 처리 로직
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from api.services.intent_classifier import IntentResult

logger = logging.getLogger(__name__)

class NewsQueryHandler:
    """뉴스 조회 전용 핸들러"""

    def __init__(self, chat_service):
        self.chat_service = chat_service
        self._last_graph_rows = []  # 마지막 검색의 그래프 결과 저장

    async def handle_news_query(self, query: str, intent_result: IntentResult, tracker=None) -> Dict[str, Any]:
        """뉴스 질의 처리"""
        logger.info(f"[뉴스 조회] 처리 시작: {query}")

        # 키워드 기반 뉴스 검색
        keywords = intent_result.keywords
        if not keywords:
            keywords = [query]

        # 뉴스 검색 수행 (graph_rows도 함께 가져옴)
        news_hits = await self._search_news(keywords)
        graph_rows = self._last_graph_rows  # _search_news에서 저장한 그래프 결과

        print(f"[뉴스 조회] 그래프 결과: {len(graph_rows)}건")
        logger.info(f"[뉴스 조회] 그래프 결과 사용: {len(graph_rows)}건")

        # 개선된 컨텍스트 기반 응답 생성
        from api.services.context_answer_generator import generate_context_answer

        # 검색 결과를 통합 형태로 변환
        search_results = {
            "sources": [],
            "graph_samples": graph_rows[:5]  # 상위 5개 그래프 샘플 포함
        }

        # 뉴스 검색 결과를 sources 형태로 변환 (디버깅 강화)
        logger.info(f"[뉴스 변환] 입력 검색 결과 수: {len(news_hits)}")

        for i, hit in enumerate(news_hits):
            logger.debug(f"[뉴스 변환] {i+1}번째 hit 키: {list(hit.keys())}")

            source_data = hit.get("_source", {})
            logger.debug(f"[뉴스 변환] {i+1}번째 _source 키: {list(source_data.keys()) if source_data else 'Empty'}")

            metadata = source_data.get("metadata", {})
            logger.debug(f"[뉴스 변환] {i+1}번째 metadata 키: {list(metadata.keys()) if metadata else 'Empty'}")

            # 제목 추출 시도 (여러 경로)
            title_from_source = source_data.get("title")
            title_from_metadata = metadata.get("title") if metadata else None
            title_from_hit_direct = hit.get("title")  # hit에서 직접 추출 시도

            logger.debug(f"[뉴스 변환] 제목 추출 시도:")
            logger.debug(f"  - source.title: {title_from_source}")
            logger.debug(f"  - metadata.title: {title_from_metadata}")
            logger.debug(f"  - hit.title: {title_from_hit_direct}")

            # 제목 추출 (다양한 구조 지원)
            title = (
                title_from_source or
                title_from_metadata or
                title_from_hit_direct or
                "뉴스 기사"
            )

            # URL 추출 (여러 경로 시도)
            url = (
                source_data.get("url") or
                metadata.get("url") or
                hit.get("url") or
                ""
            )

            # 날짜 추출 (여러 경로 시도)
            date = (
                metadata.get("created_date") or
                metadata.get("date") or
                source_data.get("created_date") or
                source_data.get("date") or
                hit.get("date") or
                ""
            )

            # 미디어 추출 (여러 경로 시도)
            media = (
                source_data.get("media") or
                metadata.get("media") or
                hit.get("media") or
                ""
            )

            logger.debug(f"[뉴스 변환] 최종 추출 결과:")
            logger.debug(f"  - title: {title[:50] if title else None}...")
            logger.debug(f"  - url: {url[:50] if url else None}...")
            logger.debug(f"  - media: {media}")
            logger.debug(f"  - date: {date}")

            search_results["sources"].append({
                "title": title,
                "url": url,
                "date": date,
                "media": media,
                "score": hit.get("_score", 0)
            })

        # 컨텍스트 기반 답변 생성
        context_answer = generate_context_answer(
            query=query,
            intent="news_inquiry",
            search_results=search_results,
            entities=intent_result.extracted_entities
        )

        response = {
            "type": "news_inquiry",
            "markdown": context_answer,
            "news_count": len(news_hits),
            "sources": search_results["sources"],
            "entities": intent_result.extracted_entities,
            "meta": {
                "query": query,
                "search_type": "context_enhanced",
                "total_hits": len(news_hits),
                "graph_samples_shown": len(graph_rows)  # 그래프 샘플 수 포함
            }
        }

        logger.info(f"[뉴스 조회] 컨텍스트 기반 응답 생성 완료: {len(news_hits)}건")
        return response

    async def _search_news(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """뉴스 검색 (중복 제거 및 최신순)"""
        try:
            # 키워드 정제: 뉴스 검색에 특화된 필터링
            print(f"[뉴스 검색] 입력 키워드: {keywords}")
            refined_keywords = self._refine_news_keywords(keywords)
            print(f"[뉴스 검색] 정제된 키워드: {refined_keywords}")

            if not refined_keywords:
                logger.warning("뉴스 검색용 키워드가 없습니다")
                return []

            # 뉴스 전용 최적화된 검색 수행
            # 핵심 키워드 우선 + 부가 키워드는 선택적으로
            # 예: "2차전지 수주 기업" 보다는 "2차전지" 위주로 검색하되 "수주"를 포함한 결과 우선
            primary_keywords = [kw for kw in refined_keywords if len(kw) > 2][:2]  # 핵심 키워드 최대 2개
            search_query = " ".join(primary_keywords) if primary_keywords else " ".join(refined_keywords[:2])
            print(f"[뉴스 검색] 검색어: '{search_query}' (원본: {refined_keywords})")
            logger.info(f"[뉴스 검색] 검색어: '{search_query}'")

            # Neo4j 그래프 검색 포함 (search_parallel 사용)
            print(f"[뉴스 검색] search_parallel 호출 시작")
            logger.info(f"[뉴스 검색] search_parallel 호출 (Neo4j 그래프 + OpenSearch)")
            news_hits, graph_rows, _, search_time, graph_time, news_time = await self.chat_service.search_parallel(
                search_query,
                size=25
            )

            print(f"[뉴스 검색] search_parallel 완료: 뉴스 {len(news_hits)}건, 그래프 {len(graph_rows)}건")
            logger.info(f"[뉴스 검색] 결과: 뉴스 {len(news_hits)}건, 그래프 {len(graph_rows)}건")
            logger.info(f"[뉴스 검색] 시간: 검색 {search_time:.0f}ms, 그래프 {graph_time:.0f}ms, 뉴스 {news_time:.0f}ms")

            # search_parallel 결과를 기존 형식으로 변환
            hits = news_hits

            # graph_rows를 저장하여 반환 (중요!)
            self._last_graph_rows = graph_rows

            # 중복 제거 (URL 기준) - 직접 필드 사용
            seen_urls = set()
            unique_hits = []
            for hit in hits:
                url = hit.get("url", "")
                title = hit.get("title", "").lower()

                # URL 중복 제거 + 제목 관련성 체크
                if url and url not in seen_urls:
                    # 검색어와 제목 관련성 검증 (간단한 필터링)
                    if self._is_relevant_news(title, refined_keywords):
                        seen_urls.add(url)
                        unique_hits.append(hit)

            logger.info(f"[뉴스 검색] 결과: {len(unique_hits)}건")
            return unique_hits

        except Exception as e:
            logger.error(f"뉴스 검색 실패: {e}")
            return []

    async def _format_news_response(self, query: str, news_hits: List[Dict[str, Any]],
                                  entities: Dict[str, List[str]]) -> Dict[str, Any]:
        """뉴스 중심 응답 포맷팅"""

        # 뉴스 목록 정리 (개선된 로직)
        formatted_news = []

        logger.info(f"[뉴스 포맷팅] 입력된 뉴스 건수: {len(news_hits)}")

        for i, hit in enumerate(news_hits[:10]):  # 최대 10개
            logger.debug(f"[뉴스 포맷팅] {i+1}번째 뉴스 처리: {hit.get('title', 'no title')[:50]}...")

            # 검색 결과는 이미 직접 필드 형태로 제공됨 (_source 래핑 없음)
            title = hit.get("title", "제목 없음")
            url = hit.get("url", "")
            date = hit.get("date", "")  # date 필드 직접 사용
            media = hit.get("media", "")

            # 완화된 유효성 검사: 제목이 있거나 URL이 있으면 포함
            if (title and title.strip() and len(title.strip()) > 3) or url:
                # 제목이 없으면 기본 제목 생성
                if not title or title == "제목 없음" or len(title.strip()) <= 3:
                    title = f"뉴스 기사 #{len(formatted_news) + 1}"

                formatted_news.append({
                    "title": title,
                    "url": url,
                    "date": date,
                    "media": media,
                    "score": hit.get("_score", 0)
                })
                logger.info(f"[뉴스 포맷팅] 추가된 뉴스: {title[:50]}...")
            else:
                logger.warning(f"[뉴스 포맷팅] 유효하지 않은 뉴스: title='{title}', url='{url}'")

        # 주요 테마/종목 정보
        theme_info = self._extract_theme_info(entities)

        # 마크다운 응답 생성
        markdown_sections = []

        # 헤더
        entity_str = ""
        if entities.get("company"):
            entity_str = f" - {', '.join(entities['company'])}"
        elif entities.get("theme"):
            entity_str = f" - {', '.join(entities['theme'])}"

        markdown_sections.append(f"## 📰 뉴스 검색 결과{entity_str}")
        markdown_sections.append("")

        # 뉴스 목록 (개선된 로직)
        logger.info(f"[뉴스 응답] formatted_news 개수: {len(formatted_news)}")

        if formatted_news:
            markdown_sections.append("### 📰 주요 뉴스")
            for i, news in enumerate(formatted_news, 1):
                date_str = news['date'][:10] if news['date'] else ""

                # 제목 처리
                title = news['title'] or "제목 정보 없음"
                markdown_sections.append(f"{i}. **{title}**")

                # 메타 정보
                meta_parts = []
                if news.get('media'):
                    meta_parts.append(news['media'])
                if date_str:
                    meta_parts.append(date_str)
                if meta_parts:
                    markdown_sections.append(f"   *{' | '.join(meta_parts)}*")

                # URL 링크
                if news.get('url'):
                    markdown_sections.append(f"   🔗 [기사 보기]({news['url']})")

                # 관련도 점수 (디버깅용)
                score = news.get('score', 0)
                if score > 0:
                    markdown_sections.append(f"   📊 관련도: {score:.2f}")

                markdown_sections.append("")

            logger.info(f"[뉴스 응답] {len(formatted_news)}개 뉴스 포맷팅 완료")
        else:
            # 원본 검색 결과가 있었는지 확인
            logger.warning(f"[뉴스 응답] 포맷팅된 뉴스 없음. 원본 검색 결과: {len(news_hits)}건")

            if len(news_hits) > 0:
                markdown_sections.append("### ⚠️ 뉴스 처리 중 오류가 발생했습니다")
                markdown_sections.append(f"검색된 뉴스 {len(news_hits)}건이 있지만 표시 형식 변환에 실패했습니다.")
                markdown_sections.append("시스템 관리자에게 문의해주세요.")
            else:
                markdown_sections.append("### ⚠️ 관련 뉴스를 찾을 수 없습니다")
                markdown_sections.append("다른 키워드로 다시 검색해보세요.")

        # 관련 정보 (테마/종목이 있는 경우)
        if theme_info:
            markdown_sections.append("### 📊 관련 정보")
            markdown_sections.extend(theme_info)

        return {
            "type": "news_inquiry",
            "markdown": "\\n".join(markdown_sections),
            "news_count": len(formatted_news),
            "sources": formatted_news,
            "entities": entities,
            "meta": {
                "query": query,
                "search_type": "news_focused",
                "total_hits": len(news_hits)
            }
        }

    def _extract_theme_info(self, entities: Dict[str, List[str]]) -> List[str]:
        """테마/종목 관련 정보 추출"""
        info_lines = []

        # 종목 정보
        if entities.get("company"):
            companies = entities["company"][:3]  # 최대 3개
            info_lines.append("**관련 종목:**")
            for company in companies:
                info_lines.append(f"- {company}")
            info_lines.append("")

        # 테마 정보
        if entities.get("theme"):
            themes = entities["theme"][:3]  # 최대 3개
            info_lines.append("**관련 테마:**")
            for theme in themes:
                info_lines.append(f"- {theme}")
            info_lines.append("")

        return info_lines

    def _refine_news_keywords(self, keywords: List[str]) -> List[str]:
        """뉴스 검색에 특화된 키워드 정제"""
        from api.config.keyword_mappings import STOPWORDS

        # 확장된 stopwords (뉴스 검색 특화)
        # 주의: '현황', '수주', '실적' 같은 비즈니스 용어는 제거하지 않음!
        news_stopwords = STOPWORDS | {
            '뉴스', '기사', '소식', '정보', '내용', '자료',
            '보여줘', '알려줘', '말해줘', '해줘', '찾아줘', '검색해줘',
            '관련', '대한', '관해서', '에서', '으로', '로서', '에게',
            '는', '은', '이', '가', '을', '를', '의', '에', '로', '으로',
            '있는', '없는', '같은', '다른', '그런', '이런',
            '주요', '최근', '오늘', '어제', '요즘',
            '좀', '더', '많이', '잘', '빨리',
            '개월', '개월간', '들의', '인가', '어디'
        }

        refined = []
        for keyword in keywords:
            # 튜플이나 리스트가 들어온 경우 처리 (방어 코드)
            if isinstance(keyword, (tuple, list)):
                # 튜플/리스트 내부의 문자열만 추출
                keyword = ''.join([k for k in keyword if isinstance(k, str) and k])

            # 문자열이 아니면 건너뛰기
            if not isinstance(keyword, str):
                continue

            if keyword and len(keyword) > 1:
                # stopwords 필터링
                if keyword.lower() not in news_stopwords:
                    # 숫자만 있는 키워드 제외 (1자리든 2자리든 모두)
                    if not keyword.isdigit():
                        # 너무 짧은 키워드 제외 (단, 2글자 이상 한글/영문은 허용)
                        if len(keyword) >= 2 or (len(keyword) == 1 and keyword.isalpha()):
                            refined.append(keyword)

        return refined[:5]  # 최대 5개 키워드만 사용

    def _is_relevant_news(self, title: str, keywords: List[str]) -> bool:
        """뉴스 제목과 키워드의 관련성 체크"""
        if not title or not keywords:
            return True  # 기본적으로 통과

        title_lower = title.lower()

        # 주요 키워드 중 하나라도 제목에 포함되어야 함
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in title_lower:
                return True

            # 부분 매칭도 체크 (2글자 이상)
            if len(keyword_lower) >= 2:
                if keyword_lower[:2] in title_lower or keyword_lower[-2:] in title_lower:
                    return True

        # 키워드가 전혀 매칭되지 않으면 관련성 낮음으로 판단
        logger.debug(f"[관련성 체크] 낮은 관련성: '{title}' vs {keywords}")
        return False

    async def _fast_news_search(self, query: str, size: int = 10) -> Tuple[List[Dict[str, Any]], float, Optional[str]]:
        """뉴스 전용 고속 검색 (온톨로지 확장 없이 직접 검색)"""
        import time
        t0 = time.perf_counter()

        try:
            from api.config import settings

            # 직접 OpenSearch 검색 (온톨로지 처리 생략)
            os_index = settings.news_embedding_index

            # 최적화된 쿼리 구조 (metadata 구조에 맞춰 수정)
            body = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["metadata.title^4", "metadata.content^2", "text^2"],
                                    "type": "best_fields",
                                    "operator": "or"
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                },
                "sort": [
                    {"_score": {"order": "desc"}}
                ],
                "_source": {
                    "includes": ["metadata.title", "metadata.url", "metadata.media", "metadata.portal", "metadata.date", "metadata.content", "text"]
                },
                "size": size
            }

            result = await self.chat_service.os.search(
                index=os_index,
                query=body,
                size=size
            )

            if result and result.get("hits"):
                hits = result["hits"].get("hits", [])

                # 간단한 포맷팅
                formatted_hits = []
                for hit in hits:
                    source = hit.get("_source", {})
                    if source.get("title") and source.get("url"):  # 필수 필드가 있는 것만
                        formatted_hits.append(hit)

                search_time_ms = (time.perf_counter() - t0) * 1000
                logger.info(f"[고속 뉴스 검색] 완료: {len(formatted_hits)}건, {search_time_ms:.1f}ms")
                return formatted_hits, search_time_ms, None
            else:
                return [], (time.perf_counter() - t0) * 1000, "No results found"

        except Exception as e:
            logger.error(f"고속 뉴스 검색 실패: {e}")
            search_time_ms = (time.perf_counter() - t0) * 1000
            return [], search_time_ms, str(e)

# 전역 인스턴스는 chat_service가 필요하므로 나중에 초기화