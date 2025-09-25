"""
질의 의도 분류 시스템
사용자 질의를 분석하여 적절한 처리 파이프라인으로 라우팅
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)

class QueryIntent(Enum):
    """질의 의도 분류"""
    NEWS_INQUIRY = "news_inquiry"        # 뉴스 조회
    STOCK_ANALYSIS = "stock_analysis"    # 종목/테마 분석
    GENERAL_QA = "general_qa"           # 일반 질문
    UNKNOWN = "unknown"                 # 분류 불가

@dataclass
class IntentResult:
    """의도 분석 결과"""
    intent: QueryIntent
    confidence: float           # 신뢰도 (0.0 ~ 1.0)
    extracted_entities: Dict    # 추출된 엔티티 (종목명, 테마 등)
    keywords: List[str]         # 핵심 키워드
    reasoning: str             # 분류 근거

class IntentClassifier:
    """개선된 질의 의도 분류기"""

    def __init__(self):
        # 강화된 의도별 패턴 정의
        self.intent_patterns = {
            QueryIntent.NEWS_INQUIRY: {
                "keywords": ["뉴스", "소식", "기사", "보도", "발표", "공시", "출시", "런칭", "공개"],
                "verbs": ["보여줘", "알려줘", "말해줘", "찾아줘", "검색해줘"],
                "context_words": ["관련", "최근", "오늘", "어제", "이번주", "발표된", "나온"],
                "patterns": [
                    r".*뉴스.*보여줘",
                    r".*소식.*알려줘",
                    r".*관련.*뉴스",
                    r".*최근.*소식",
                    r".*기사.*찾아줘",
                    r".*발표.*뉴스",
                    r".*에.*대한.*뉴스",
                    r".*관련.*최근",
                    r".*영향을.*줄.*뉴스"
                ],
                "weight": 1.2
            },
            QueryIntent.STOCK_ANALYSIS: {
                "keywords": ["전망", "유망주", "추천", "투자", "분석", "예측", "주가", "수익률", "실적", "매출", "영업이익"],
                "verbs": ["어때", "좋아", "나빠", "오를까", "떨어질까", "추천해줘"],
                "context_words": ["중에서", "가장", "좋은", "나쁜", "올해", "3분기", "분기", "실적"],
                "patterns": [
                    r".*전망.*어때",
                    r".*유망주.*는",
                    r".*투자.*추천",
                    r".*관련.*종목",
                    r".*어떤.*주식",
                    r".*분석.*해줘"
                ],
                "weight": 1.0
            },
            QueryIntent.GENERAL_QA: {
                "keywords": ["뭐야", "무엇", "어떻게", "왜", "설명", "의미", "정의"],
                "verbs": ["뭐야", "무엇", "어떻게", "왜"],
                "patterns": [
                    r".*뭐야",
                    r".*무엇.*인가",
                    r".*어떻게.*하는",
                    r".*왜.*그런가",
                    r".*설명.*해줘"
                ],
                "weight": 0.8
            }
        }

        # 대폭 확장된 엔티티 추출 패턴
        self.entity_patterns = {
            "company": [
                # 주요 대형주
                r"(삼성전자|에코프로|한화시스템|LG전자|SK하이닉스|네이버|카카오|포스코|POSCO)",
                r"(현대차|기아|현대모비스|삼성SDI|LG화학|LG에너지솔루션)",
                r"(NC소프트|넷마블|크래프톤|위메이드|컴투스)",
                r"(아모레퍼시픽|LG생활건강|코스맥스|한국콜마)",
                # 패턴 매칭
                r"([가-힣]+전자|[가-힣]+시스템|[가-힣]+케미칼|[가-힣]+소프트)",
                r"([가-힣]+바이오|[가-힣]+제약|[가-힣]+머티리얼즈)",
                # 게임 관련 고유명사
                r"(아이온|아이온2|리니지|던전앤파이터|로스트아크|배틀그라운드)",
            ],
            "theme": [
                # 기존 테마
                r"(방산|국방|SMR|원전|2차전지|배터리|AI|인공지능|반도체)",
                r"(금융지주|바이오|헬스케어|전기차|신재생에너지)",
                # 새로운 테마
                r"(게임|메타버스|NFT|크립토|블록체인)",
                r"(K-뷰티|화장품|코스메틱|뷰티)",
                r"(반도체|메모리|시스템반도체|파운드리)",
                r"(자동차|전기차|수소차|자율주행)",
            ],
            "product": [
                # 제품명 패턴 추가
                r"(아이온2|아이온|리니지|갤럭시|아이폰)",
                r"([가-힣A-Za-z0-9]+\s*[1-9]+)",  # 제품명+숫자 패턴
            ],
            "stock_code": [
                r"(\d{6})"
            ],
            "financial_terms": [
                r"(실적|매출|영업이익|순이익|ROE|ROA|PER|PBR|배당)",
                r"(3분기|2분기|1분기|4분기|반기|연간)"
            ]
        }

    def classify_intent(self, query: str) -> IntentResult:
        """질의 의도 분류"""
        q_lower = query.lower()
        intent_scores = {}

        # 각 의도별 점수 계산
        for intent, patterns in self.intent_patterns.items():
            score = self._calculate_intent_score(q_lower, patterns)
            intent_scores[intent] = score

        # 최고 점수 의도 선택
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        selected_intent, confidence = best_intent

        # 신뢰도가 너무 낮으면 UNKNOWN으로 분류
        if confidence < 0.3:
            selected_intent = QueryIntent.UNKNOWN
            confidence = 0.0

        # 엔티티 추출
        entities = self._extract_entities(query)

        # 키워드 추출 (의도별 맞춤)
        keywords = self._extract_intent_keywords(query, selected_intent)

        # 분류 근거 생성
        reasoning = self._generate_reasoning(query, selected_intent, confidence, entities)

        return IntentResult(
            intent=selected_intent,
            confidence=confidence,
            extracted_entities=entities,
            keywords=keywords,
            reasoning=reasoning
        )

    def _calculate_intent_score(self, query: str, patterns: Dict) -> float:
        """의도별 점수 계산"""
        score = 0.0

        # 키워드 매칭
        keyword_matches = sum(1 for kw in patterns["keywords"] if kw in query)
        score += keyword_matches * 0.3

        # 동사 패턴 매칭
        verb_matches = sum(1 for verb in patterns["verbs"] if verb in query)
        score += verb_matches * 0.2

        # 정규식 패턴 매칭
        pattern_matches = sum(1 for pattern in patterns["patterns"]
                            if re.search(pattern, query))
        score += pattern_matches * 0.5

        return min(score, 1.0) * patterns["weight"]

    def _extract_entities(self, query: str) -> Dict:
        """엔티티 추출"""
        entities = {}

        for entity_type, patterns in self.entity_patterns.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, query, re.IGNORECASE)
                matches.extend(found)

            if matches:
                entities[entity_type] = list(set(matches))  # 중복 제거

        return entities

    def _extract_intent_keywords(self, query: str, intent: QueryIntent) -> List[str]:
        """개선된 의도별 맞춤 키워드 추출"""
        # 먼저 엔티티를 추출해서 보존
        entities = self._extract_entities(query)
        keywords = []

        # 엔티티를 최우선으로 추가
        for entity_type, entity_list in entities.items():
            keywords.extend(entity_list)

        if intent == QueryIntent.NEWS_INQUIRY:
            # 뉴스 조회: 엔티티 + 시간 표현 + 뉴스 관련 동사
            time_keywords = self._extract_time_keywords(query)
            news_context = self._extract_news_context(query)
            keywords.extend(time_keywords)
            keywords.extend(news_context)

        elif intent == QueryIntent.STOCK_ANALYSIS:
            # 종목 분석: 엔티티 + 투자 관련 키워드 + 비교 표현
            investment_keywords = self._extract_investment_keywords(query)
            comparison_keywords = self._extract_comparison_keywords(query)
            keywords.extend(investment_keywords)
            keywords.extend(comparison_keywords)

        else:
            # 기본 키워드 추출
            basic_keywords = self._extract_basic_keywords(query)
            keywords.extend(basic_keywords)

        # 중복 제거 및 정리
        keywords = list(dict.fromkeys(keywords))  # 순서 유지하며 중복 제거
        return keywords[:15]  # 최대 15개

    def _extract_time_keywords(self, query: str) -> List[str]:
        """시간 관련 키워드 추출"""
        time_patterns = [
            r"(최근|요즘|오늘|어제|이번주|이번달|올해|작년)",
            r"(\d+분기|\d+월|\d+일|\d+년)",
            r"(발표된|나온|공개된|출시된)"
        ]
        keywords = []
        for pattern in time_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            keywords.extend(matches)
        return keywords

    def _extract_news_context(self, query: str) -> List[str]:
        """뉴스 맥락 키워드 추출"""
        context_patterns = [
            r"(영향을?\s*줄\s*만한|영향)",
            r"(관련|대한|관해서)",
            r"(발표|공시|보도|기사)"
        ]
        keywords = []
        for pattern in context_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            keywords.extend(matches)
        return keywords

    def _extract_investment_keywords(self, query: str) -> List[str]:
        """투자 관련 키워드 추출"""
        investment_patterns = [
            r"(전망|예측|분석|추천)",
            r"(주가|수익률|투자|매수|매도)",
            r"(실적|매출|영업이익|순이익)"
        ]
        keywords = []
        for pattern in investment_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            keywords.extend(matches)
        return keywords

    def _extract_comparison_keywords(self, query: str) -> List[str]:
        """비교 관련 키워드 추출"""
        comparison_patterns = [
            r"(중에서|가운데|중에|가장|제일|최고|최저)",
            r"(좋은|나쁜|높은|낮은|큰|작은)",
            r"(어디|무엇|어떤|얼마)"
        ]
        keywords = []
        for pattern in comparison_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            keywords.extend(matches)
        return keywords

    def _extract_basic_keywords(self, query: str) -> List[str]:
        """기본 키워드 추출"""
        # 간단한 토큰화
        import re
        tokens = re.findall(r'[가-힣A-Za-z0-9]+', query)
        # 불용어 제거
        stopwords = {'은', '는', '이', '가', '을', '를', '의', '에', '로', '과', '와', '도', '만', '까지', '부터'}
        keywords = [token for token in tokens if token not in stopwords and len(token) > 1]
        return keywords

    def _generate_reasoning(self, query: str, intent: QueryIntent,
                          confidence: float, entities: Dict) -> str:
        """분류 근거 생성"""
        if intent == QueryIntent.NEWS_INQUIRY:
            return f"뉴스 관련 키워드 감지됨 (신뢰도: {confidence:.2f})"
        elif intent == QueryIntent.STOCK_ANALYSIS:
            return f"투자/분석 관련 키워드 감지됨 (신뢰도: {confidence:.2f})"
        elif intent == QueryIntent.GENERAL_QA:
            return f"일반 질문 패턴 감지됨 (신뢰도: {confidence:.2f})"
        else:
            return f"의도 분류 실패 (신뢰도: {confidence:.2f})"

    def _filter_news_keywords(self, keywords: List[str]) -> List[str]:
        """뉴스 키워드 전용 필터링"""
        # 뉴스 검색에 불필요한 단어들 (확장된 목록)
        news_stopwords = {
            # 액션 워드
            '뉴스', '기사', '소식', '정보', '내용', '자료', '데이터', '현황', '상황',
            '보여줘', '알려줘', '말해줘', '해줘', '찾아줘', '검색해줘', '가져와줘',

            # 조사/어미
            '관련', '대한', '관해서', '에서', '으로', '로서', '에게', '에서는', '에는',
            '는', '은', '이', '가', '을', '를', '의', '에', '로', '으로', '와', '과',

            # 수식어
            '있는', '없는', '같은', '다른', '그런', '이런', '저런', '어떤', '무슨',
            '주요', '최근', '오늘', '어제', '요즘', '지금', '현재',
            '좀', '더', '많이', '잘', '빨리', '자세히', '정확히',

            # 시간 표현
            '오늘', '어제', '내일', '이번', '지난', '다음'
        }

        filtered = []
        for keyword in keywords:
            if keyword and len(keyword) > 1:
                if keyword.lower() not in news_stopwords:
                    # 숫자만 있는 키워드나 너무 짧은 키워드 제외
                    if len(keyword) >= 2 and not keyword.isdigit():
                        filtered.append(keyword)

        return filtered

    def _filter_stock_keywords(self, keywords: List[str]) -> List[str]:
        """투자/주식 키워드 전용 필터링"""
        # 투자 분석에 불필요한 단어들
        stock_stopwords = {
            # 액션 워드
            '추천', '해줘', '알려줘', '말해줘', '보여줘', '분석해줘',

            # 일반적 표현
            '어때', '좋아', '나빠', '괜찮아', '어떨까', '할까',
            '관련', '대한', '에서', '으로', '로서',
            '는', '은', '이', '가', '을', '를', '의', '에', '로', '으로',

            # 불필요한 수식어
            '좋은', '나쁜', '괜찮은', '어떤', '무슨', '그런', '이런',
            '주식', '종목' # 너무 일반적이어서 검색에 도움이 안됨
        }

        filtered = []
        for keyword in keywords:
            if keyword and len(keyword) > 1:
                if keyword.lower() not in stock_stopwords:
                    if len(keyword) >= 2 and not keyword.isdigit():
                        filtered.append(keyword)

        return filtered

    def _filter_general_keywords(self, keywords: List[str]) -> List[str]:
        """일반 질문 키워드 필터링"""
        general_stopwords = {
            '뭐야', '무엇', '어떻게', '왜', '언제', '어디서', '누가',
            '는', '은', '이', '가', '을', '를', '의', '에', '로', '으로',
            '해줘', '알려줘', '말해줘', '설명해줘'
        }

        filtered = []
        for keyword in keywords:
            if keyword and len(keyword) > 1:
                if keyword.lower() not in general_stopwords:
                    if len(keyword) >= 2:
                        filtered.append(keyword)

        return filtered

# 전역 인스턴스
intent_classifier = IntentClassifier()

def classify_query_intent(query: str) -> IntentResult:
    """질의 의도 분류 (편의 함수)"""
    return intent_classifier.classify_intent(query)