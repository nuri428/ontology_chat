"""
사용자 맞춤형 응답 생성 시스템
질의 유형 분석, 개인화된 추천, 적응형 응답 스타일 포함
"""
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from api.logging import setup_logging
logger = setup_logging()

class QueryType(Enum):
    """질의 유형"""
    INVESTMENT = "investment"      # 투자 관련
    MARKET_ANALYSIS = "market"     # 시장 분석
    COMPANY_INFO = "company"       # 기업 정보
    NEWS_SUMMARY = "news"          # 뉴스 요약
    TECHNICAL_SPEC = "technical"   # 기술/제품 사양
    POLICY_REGULATION = "policy"   # 정책/규제
    COMPARISON = "comparison"      # 비교 분석
    FORECAST = "forecast"          # 전망/예측
    GENERAL_INFO = "general"       # 일반 정보

class UserIntent(Enum):
    """사용자 의도"""
    QUICK_INFO = "quick"           # 빠른 정보
    DETAILED_ANALYSIS = "detailed" # 상세 분석
    ACTIONABLE_ADVICE = "actionable" # 실행 가능한 조언
    EDUCATIONAL = "educational"    # 학습/이해
    VERIFICATION = "verification"  # 확인/검증

@dataclass
class QueryProfile:
    """질의 프로필"""
    query_type: QueryType
    user_intent: UserIntent
    expertise_level: str           # beginner, intermediate, expert
    urgency: str                   # low, medium, high
    context_hints: List[str]
    confidence: float

class PersonalizationEngine:
    """개인화 엔진"""
    
    def __init__(self):
        self.query_patterns = self._build_query_patterns()
        self.intent_indicators = self._build_intent_indicators()
        self.expertise_patterns = self._build_expertise_patterns()
        self.response_templates = self._build_response_templates()
    
    def _build_query_patterns(self) -> Dict[QueryType, List[str]]:
        """질의 유형별 패턴"""
        return {
            QueryType.INVESTMENT: [
                r"투자|종목|주식|추천|매수|매도|포트폴리오",
                r"수익률|배당|가치평가|펀드",
                r"유망|전망|기대|상승|하락"
            ],
            QueryType.MARKET_ANALYSIS: [
                r"시장|업계|산업|동향|트렌드",
                r"경쟁|점유율|성장률",
                r"분석|현황|상황|전체적"
            ],
            QueryType.COMPANY_INFO: [
                r"한화|kai|lg|삼성|현대",
                r"기업|회사|사업|실적|매출",
                r"ceo|경영진|조직|전략"
            ],
            QueryType.NEWS_SUMMARY: [
                r"뉴스|기사|보도|발표|공시",
                r"최근|어제|오늘|이번주",
                r"요약|정리|핵심|주요"
            ],
            QueryType.TECHNICAL_SPEC: [
                r"기술|스펙|사양|성능|기능",
                r"개발|연구|특허|혁신",
                r"k-?\d+|무기체계|플랫폼"
            ],
            QueryType.POLICY_REGULATION: [
                r"정책|규제|법률|제도",
                r"정부|국가|부처|법안",
                r"지원|보조금|세제|혜택"
            ],
            QueryType.COMPARISON: [
                r"비교|vs|대비|차이|우위",
                r"장단점|pros|cons",
                r"선택|결정|판단"
            ],
            QueryType.FORECAST: [
                r"전망|예측|예상|미래",
                r"계획|목표|vision",
                r"\d+년|장기|단기|중기"
            ]
        }
    
    def _build_intent_indicators(self) -> Dict[UserIntent, List[str]]:
        """사용자 의도별 지표"""
        return {
            UserIntent.QUICK_INFO: [
                r"간단히|빠르게|요약|핵심만",
                r"뭐야|무엇|어떤|얼마",
                r"?\s*$"  # 질문으로 끝남
            ],
            UserIntent.DETAILED_ANALYSIS: [
                r"자세히|상세히|깊이|분석",
                r"이유|원인|배경|근거",
                r"어떻게|왜|how|why"
            ],
            UserIntent.ACTIONABLE_ADVICE: [
                r"추천|조언|제안|권장",
                r"해야|하면|방법|how to",
                r"투자|매수|전략|계획"
            ],
            UserIntent.EDUCATIONAL: [
                r"이해|학습|공부|설명",
                r"원리|구조|시스템|과정",
                r"처음|초보|beginner"
            ],
            UserIntent.VERIFICATION: [
                r"확인|검증|사실|진실",
                r"맞나|정말|실제로",
                r"true|false|correct"
            ]
        }
    
    def _build_expertise_patterns(self) -> Dict[str, List[str]]:
        """전문성 수준별 패턴"""
        return {
            "beginner": [
                r"처음|초보|모르|잘 모름",
                r"쉽게|간단히|기초",
                r"뭐야|어떤 거|무엇"
            ],
            "intermediate": [
                r"어느 정도|보통|일반적",
                r"좀 더|추가로|세부적",
                r"비교|차이점"
            ],
            "expert": [
                r"전문적|고급|심화",
                r"기술적|분석적|상세한",
                r"dcf|pe|roe|기술지표"
            ]
        }
    
    def _build_response_templates(self) -> Dict[str, Dict[str, str]]:
        """응답 템플릿"""
        return {
            "investment_beginner": {
                "tone": "친근하고 설명적",
                "structure": "기본 개념 설명 → 핵심 포인트 → 주의사항",
                "details": "high"
            },
            "investment_expert": {
                "tone": "간결하고 데이터 중심",
                "structure": "핵심 데이터 → 분석 결과 → 투자 의견",
                "details": "medium"
            },
            "market_quick": {
                "tone": "요약적",
                "structure": "핵심 요약 → 주요 동향",
                "details": "low"
            },
            "technical_detailed": {
                "tone": "전문적",
                "structure": "기술 개요 → 상세 사양 → 비교 분석",
                "details": "high"
            }
        }
    
    def analyze_query(self, query: str) -> QueryProfile:
        """질의 분석 및 프로필 생성"""
        query_lower = query.lower()
        
        # 1. 질의 유형 감지
        query_type = self._detect_query_type(query_lower)
        
        # 2. 사용자 의도 파악
        user_intent = self._detect_user_intent(query_lower)
        
        # 3. 전문성 수준 추정
        expertise_level = self._estimate_expertise_level(query_lower)
        
        # 4. 긴급도 판단
        urgency = self._assess_urgency(query_lower)
        
        # 5. 컨텍스트 힌트 추출
        context_hints = self._extract_context_hints(query_lower)
        
        # 6. 신뢰도 계산
        confidence = self._calculate_confidence(query_type, user_intent)
        
        return QueryProfile(
            query_type=query_type,
            user_intent=user_intent,
            expertise_level=expertise_level,
            urgency=urgency,
            context_hints=context_hints,
            confidence=confidence
        )
    
    def _detect_query_type(self, query: str) -> QueryType:
        """질의 유형 감지"""
        type_scores = {}
        
        for query_type, patterns in self.query_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, query))
                score += matches
            type_scores[query_type] = score
        
        # 가장 높은 점수의 타입 반환
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            if type_scores[best_type] > 0:
                return best_type
        
        return QueryType.GENERAL_INFO
    
    def _detect_user_intent(self, query: str) -> UserIntent:
        """사용자 의도 감지"""
        intent_scores = {}
        
        for intent, indicators in self.intent_indicators.items():
            score = 0
            for indicator in indicators:
                matches = len(re.findall(indicator, query))
                score += matches
            intent_scores[intent] = score
        
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            if intent_scores[best_intent] > 0:
                return best_intent
        
        # 기본값: 질문 길이로 판단
        if len(query.split()) < 5:
            return UserIntent.QUICK_INFO
        else:
            return UserIntent.DETAILED_ANALYSIS
    
    def _estimate_expertise_level(self, query: str) -> str:
        """전문성 수준 추정"""
        for level, patterns in self.expertise_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    return level
        
        # 기본값: 전문 용어 밀도로 판단
        technical_terms = [
            "dcf", "pe", "roe", "ebitda", "cagr", "밸류에이션", 
            "펀더멘털", "기술적 분석", "rsi", "macd"
        ]
        
        term_count = sum(1 for term in technical_terms if term in query)
        if term_count >= 2:
            return "expert"
        elif term_count >= 1:
            return "intermediate"
        else:
            return "beginner"
    
    def _assess_urgency(self, query: str) -> str:
        """긴급도 평가"""
        urgent_patterns = [
            r"긴급|급함|빨리|즉시|당장",
            r"오늘|지금|현재|실시간"
        ]
        
        medium_patterns = [
            r"이번주|최근|곧|soon",
            r"계획|준비|검토"
        ]
        
        for pattern in urgent_patterns:
            if re.search(pattern, query):
                return "high"
        
        for pattern in medium_patterns:
            if re.search(pattern, query):
                return "medium"
        
        return "low"
    
    def _extract_context_hints(self, query: str) -> List[str]:
        """컨텍스트 힌트 추출"""
        hints = []
        
        # 시간 힌트
        time_patterns = [
            r"최근\s*\d*\s*[일개월년]*",
            r"\d{4}년",
            r"작년|올해|내년"
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, query)
            if match:
                hints.append(f"time:{match.group()}")
        
        # 지역 힌트
        region_patterns = [
            r"한국|미국|중국|일본|유럽",
            r"국내|해외|글로벌|아시아"
        ]
        
        for pattern in region_patterns:
            match = re.search(pattern, query)
            if match:
                hints.append(f"region:{match.group()}")
        
        # 산업 힌트
        industry_patterns = [
            r"방산|국방|항공|우주",
            r"반도체|it|바이오|에너지"
        ]
        
        for pattern in industry_patterns:
            match = re.search(pattern, query)
            if match:
                hints.append(f"industry:{match.group()}")
        
        return hints
    
    def _calculate_confidence(self, query_type: QueryType, user_intent: UserIntent) -> float:
        """분석 신뢰도 계산"""
        # 기본 신뢰도
        base_confidence = 0.7
        
        # 일반적인 조합의 신뢰도 보정
        common_combinations = {
            (QueryType.INVESTMENT, UserIntent.ACTIONABLE_ADVICE): 0.9,
            (QueryType.NEWS_SUMMARY, UserIntent.QUICK_INFO): 0.9,
            (QueryType.MARKET_ANALYSIS, UserIntent.DETAILED_ANALYSIS): 0.85,
            (QueryType.COMPANY_INFO, UserIntent.EDUCATIONAL): 0.8
        }
        
        return common_combinations.get((query_type, user_intent), base_confidence)
    
    def customize_response_style(self, profile: QueryProfile) -> Dict[str, Any]:
        """응답 스타일 커스터마이징"""
        template_key = f"{profile.query_type.value}_{profile.expertise_level}"
        
        # 기본 템플릿
        if template_key in self.response_templates:
            base_template = self.response_templates[template_key]
        else:
            # 폴백 템플릿
            base_template = {
                "tone": "중립적이고 정보 제공적",
                "structure": "질의 응답 → 관련 정보 → 추가 참고사항",
                "details": "medium"
            }
        
        # 의도별 조정
        adjustments = self._get_intent_adjustments(profile.user_intent)
        
        # 긴급도별 조정
        urgency_adjustments = self._get_urgency_adjustments(profile.urgency)
        
        return {
            "tone": base_template["tone"],
            "structure": base_template["structure"],
            "detail_level": self._adjust_detail_level(
                base_template["details"], 
                profile.user_intent, 
                profile.expertise_level
            ),
            "format_preferences": self._get_format_preferences(profile),
            "emphasis_areas": self._get_emphasis_areas(profile),
            "adjustments": {**adjustments, **urgency_adjustments}
        }
    
    def _get_intent_adjustments(self, intent: UserIntent) -> Dict[str, Any]:
        """의도별 조정사항"""
        return {
            UserIntent.QUICK_INFO: {
                "response_length": "short",
                "include_summary": True,
                "bullet_points": True
            },
            UserIntent.DETAILED_ANALYSIS: {
                "response_length": "long",
                "include_analysis": True,
                "show_methodology": True
            },
            UserIntent.ACTIONABLE_ADVICE: {
                "include_recommendations": True,
                "highlight_actions": True,
                "include_risks": True
            },
            UserIntent.EDUCATIONAL: {
                "explain_concepts": True,
                "include_examples": True,
                "progressive_difficulty": True
            },
            UserIntent.VERIFICATION: {
                "show_sources": True,
                "include_confidence": True,
                "fact_check": True
            }
        }.get(intent, {})
    
    def _get_urgency_adjustments(self, urgency: str) -> Dict[str, Any]:
        """긴급도별 조정사항"""
        return {
            "high": {
                "prioritize_key_points": True,
                "minimize_background": True,
                "highlight_immediacy": True
            },
            "medium": {
                "balanced_detail": True,
                "include_context": True
            },
            "low": {
                "comprehensive_coverage": True,
                "include_background": True,
                "educational_value": True
            }
        }.get(urgency, {})
    
    def _adjust_detail_level(self, base_level: str, intent: UserIntent, expertise: str) -> str:
        """세부 수준 조정"""
        level_map = {"low": 1, "medium": 2, "high": 3}
        base_score = level_map.get(base_level, 2)
        
        # 의도별 조정
        if intent == UserIntent.QUICK_INFO:
            base_score -= 1
        elif intent == UserIntent.DETAILED_ANALYSIS:
            base_score += 1
        
        # 전문성별 조정
        if expertise == "beginner":
            base_score += 1  # 더 자세한 설명 필요
        elif expertise == "expert":
            base_score -= 1  # 간결한 설명 선호
        
        # 범위 제한
        final_score = max(1, min(3, base_score))
        
        return {1: "low", 2: "medium", 3: "high"}[final_score]
    
    def _get_format_preferences(self, profile: QueryProfile) -> Dict[str, bool]:
        """포맷 선호도"""
        preferences = {
            "use_tables": False,
            "use_charts": False,
            "use_bullet_points": False,
            "use_numbered_lists": False,
            "highlight_key_metrics": False
        }
        
        if profile.query_type == QueryType.INVESTMENT:
            preferences.update({
                "use_tables": True,
                "highlight_key_metrics": True
            })
        
        if profile.user_intent == UserIntent.QUICK_INFO:
            preferences["use_bullet_points"] = True
        
        if profile.expertise_level == "expert":
            preferences.update({
                "use_tables": True,
                "use_charts": True
            })
        
        return preferences
    
    def _get_emphasis_areas(self, profile: QueryProfile) -> List[str]:
        """강조 영역 결정"""
        emphasis = []
        
        if profile.query_type == QueryType.INVESTMENT:
            emphasis.extend(["financial_metrics", "risk_factors", "recommendations"])
        
        if profile.query_type == QueryType.MARKET_ANALYSIS:
            emphasis.extend(["trends", "competitive_landscape", "growth_projections"])
        
        if profile.user_intent == UserIntent.ACTIONABLE_ADVICE:
            emphasis.extend(["action_items", "implementation_steps"])
        
        if profile.urgency == "high":
            emphasis.extend(["immediate_implications", "urgent_actions"])
        
        return emphasis

# 전역 개인화 엔진
personalization_engine = PersonalizationEngine()

def analyze_user_query(query: str) -> QueryProfile:
    """사용자 질의 분석"""
    return personalization_engine.analyze_query(query)

def get_response_style(profile: QueryProfile) -> Dict[str, Any]:
    """응답 스타일 조회"""
    return personalization_engine.customize_response_style(profile)