"""
고급 검색 전략 및 품질 개선 시스템
다단계 검색, 쿼리 확장, 결과 품질 평가 포함
"""
import re
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from api.logging import setup_logging
logger = setup_logging()

@dataclass
class SearchResult:
    """검색 결과 메타데이터"""
    hits: List[Dict[str, Any]]
    query_used: str
    strategy: str
    confidence: float
    latency_ms: float
    total_found: int

@dataclass 
class SearchStrategy:
    """검색 전략 정의"""
    name: str
    query: str
    weight: float
    priority: int
    fallback_strategy: Optional[str] = None

class AdvancedSearchEngine:
    """고급 검색 엔진 - 다단계 검색 전략 및 품질 개선"""
    
    def __init__(self):
        self.search_strategies = self._build_search_strategies()
        self.domain_patterns = self._build_domain_patterns()
        
    def _build_search_strategies(self) -> Dict[str, List[SearchStrategy]]:
        """도메인별 검색 전략 구성 - 범용 주식 분석"""
        return {
            "technology": [
                SearchStrategy("tech_direct", "{keywords} 기술 개발", 1.0, 1),
                SearchStrategy("tech_trend", "{keywords} 기술 동향 전망", 0.9, 2),
                SearchStrategy("innovation", "{keywords} 혁신 R&D", 0.8, 3),
                SearchStrategy("tech_market", "기술 OR 혁신 OR 개발 OR R&D", 0.6, 4)
            ],
            "energy": [
                SearchStrategy("energy_direct", "{keywords} 에너지 신재생", 1.0, 1),
                SearchStrategy("battery_focus", "{keywords} 배터리 2차전지", 0.9, 2),
                SearchStrategy("renewable", "{keywords} 태양광 풍력 원자력", 0.8, 3),
                SearchStrategy("energy_market", "에너지 OR 배터리 OR 신재생 OR 원자력", 0.6, 4)
            ],
            "semiconductor": [
                SearchStrategy("chip_direct", "{keywords} 반도체 칩", 1.0, 1),
                SearchStrategy("memory_focus", "{keywords} 메모리 시스템반도체", 0.9, 2),
                SearchStrategy("ai_chip", "{keywords} AI칩 HBM", 0.8, 3),
                SearchStrategy("semi_market", "반도체 OR 메모리 OR 칩 OR AI", 0.7, 4)
            ],
            "finance": [
                SearchStrategy("stock_direct", "{keywords} 주식 종목", 1.0, 1),
                SearchStrategy("investment_context", "{keywords} 투자 실적", 0.8, 2),
                SearchStrategy("market_analysis", "{keywords} 시장 전망", 0.7, 3),
                SearchStrategy("financial_news", "실적 OR 주가 OR 투자 OR 종목", 0.6, 4)
            ],
            "company": [
                SearchStrategy("company_direct", "{company_names} 뉴스 최신", 1.0, 1),
                SearchStrategy("company_business", "{company_names} 사업 실적 발표", 0.9, 2),
                SearchStrategy("company_news", "{company_names} 최신 소식", 0.8, 3),
                SearchStrategy("industry_context", "{company_names} 업계 동향", 0.7, 4)
            ],
            "automotive": [
                SearchStrategy("auto_direct", "{keywords} 자동차 전기차", 1.0, 1),
                SearchStrategy("ev_focus", "{keywords} 전기차 자율주행", 0.9, 2),
                SearchStrategy("mobility", "{keywords} 모빌리티 미래차", 0.8, 3),
                SearchStrategy("auto_market", "자동차 OR 전기차 OR 모빌리티", 0.7, 4)
            ],
            "general": [
                SearchStrategy("keyword_match", "{keywords}", 1.0, 1),
                SearchStrategy("semantic_expansion", "{expanded_keywords}", 0.8, 2),
                SearchStrategy("broad_search", "{core_terms}", 0.6, 3),
                SearchStrategy("fallback_search", "{original_query}", 0.4, 4)
            ]
        }
    
    def _build_domain_patterns(self) -> Dict[str, List[str]]:
        """도메인 감지 패턴 - 범용 주식 분석"""
        return {
            "technology": ["기술", "개발", "연구", "혁신", "특허", "r&d", "AI", "IoT", "5G", "6G"],
            "energy": ["에너지", "배터리", "2차전지", "태양광", "풍력", "원자력", "SMR", "ESS", "신재생"],
            "semiconductor": ["반도체", "메모리", "시스템반도체", "칩", "AI칩", "HBM", "D램", "낸드플래시"],
            "finance": ["주식", "종목", "투자", "실적", "주가", "시장", "상장", "배당", "금융", "은행"],
            "company": ["삼성", "LG", "SK", "현대", "포스코", "네이버", "카카오", "기업", "회사", "상장사"],
            "automotive": ["자동차", "전기차", "자율주행", "모빌리티", "미래차", "부품", "완성차"],
            "biotech": ["바이오", "제약", "의료", "헬스케어", "신약", "치료제", "백신"],
            "chemical": ["화학", "정유", "석유화학", "플라스틱", "소재", "화섬"],
            "construction": ["건설", "부동산", "인프라", "토목", "스마트시티"],
            "entertainment": ["게임", "엔터", "콘텐츠", "미디어", "방송", "영화"],
            "telecom": ["통신", "5G", "6G", "네트워크", "인프라", "텔레콤"]
        }
    
    def detect_query_domain(self, query: str) -> List[str]:
        """질의에서 도메인 감지"""
        q_lower = query.lower()
        detected_domains = []
        
        for domain, patterns in self.domain_patterns.items():
            if any(pattern in q_lower for pattern in patterns):
                detected_domains.append(domain)
        
        # 기본 도메인 설정
        if not detected_domains:
            detected_domains = ["general"]
            
        return detected_domains
    
    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """질의에서 엔티티 추출"""
        entities = {
            "companies": [],
            "products": [],
            "locations": [],
            "time_expressions": []
        }
        
        # 회사명 추출 (일반적인 패턴)
        company_patterns = [
            r"[A-Z]{2,}[가-힣]*",  # 영문 약어 + 한글
            r"[가-힣]+전자", r"[가-힣]+중공업", r"[가-힣]+화학",
            r"[가-힣]+에너지", r"[가-힣]+건설", r"[가-힣]+그룹"
        ]
        for pattern in company_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities["companies"].extend(matches)
        
        # 제품/시스템 추출 (일반적인 패턴)
        product_patterns = [
            r"[A-Z]-?\d+[가-힣]*",  # 모델명 패턴
            r"[가-힣]+시스템", r"[가-힣]+솔루션",
            r"[가-힣]+플랫폼", r"[가-힣]+서비스"
        ]
        for pattern in product_patterns:
            matches = re.findall(pattern, query)
            entities["products"].extend(matches)
        
        # 시간 표현 추출
        time_patterns = [
            r"최근\s*\d*\s*[일개월년]*", r"작년|올해|내년", r"\d{4}년", 
            r"[0-9]+월", r"분기", r"반기"
        ]
        for pattern in time_patterns:
            matches = re.findall(pattern, query)
            entities["time_expressions"].extend(matches)
        
        return entities
    
    def build_enhanced_queries(
        self, 
        original_query: str, 
        keywords: List[str], 
        domains: List[str],
        entities: Dict[str, List[str]]
    ) -> List[SearchStrategy]:
        """향상된 검색 쿼리 생성"""
        strategies = []
        
        for domain in domains:
            domain_strategies = self.search_strategies.get(domain, [])
            
            for strategy in domain_strategies:
                # 템플릿 변수 치환
                query_template = strategy.query
                
                # 키워드 치환
                if "{keywords}" in query_template:
                    keywords_str = " ".join(keywords[:5])  # 상위 5개만
                    query_template = query_template.replace("{keywords}", keywords_str)
                
                # 회사명 치환
                if "{company_names}" in query_template:
                    companies = entities.get("companies", [])
                    if companies:
                        company_str = " ".join(companies)
                        query_template = query_template.replace("{company_names}", company_str)
                    else:
                        continue  # 회사명이 없으면 해당 전략 스킵
                
                # 확장 키워드 치환
                if "{expanded_keywords}" in query_template:
                    expanded = self._expand_keywords(keywords, domain)
                    expanded_str = " ".join(expanded)
                    query_template = query_template.replace("{expanded_keywords}", expanded_str)
                
                # 핵심 용어 치환
                if "{core_terms}" in query_template:
                    core = self._extract_core_terms(keywords)
                    core_str = " ".join(core)
                    query_template = query_template.replace("{core_terms}", core_str)
                
                # 원본 쿼리 치환
                if "{original_query}" in query_template:
                    query_template = query_template.replace("{original_query}", original_query)
                
                # 새로운 전략 생성
                enhanced_strategy = SearchStrategy(
                    name=f"{domain}_{strategy.name}",
                    query=query_template.strip(),
                    weight=strategy.weight,
                    priority=strategy.priority
                )
                strategies.append(enhanced_strategy)
        
        # 우선순위별 정렬
        strategies.sort(key=lambda x: x.priority)
        return strategies
    
    def _expand_keywords(self, keywords: List[str], domain: str) -> List[str]:
        """도메인별 키워드 확장"""
        expansion_map = {
            "defense": {
                "방산": ["국방", "군수", "무기", "방위산업", "군사"],
                "유망주": ["대장주", "상승", "투자", "매수", "추천주"],
                "산업": ["제조", "생산", "기술", "혁신"],
                "제품": ["장비", "시스템", "솔루션", "플랫폼"],
                "수출": ["해외진출", "글로벌", "국외판매"],
                "계약": ["수주", "공급", "납품", "딜"]
            },
            "export": {
                "수출": ["해외진출", "글로벌진출", "국외판매", "무역"],
                "해외": ["국외", "글로벌", "overseas", "international"]
            },
            "finance": {
                "종목": ["주식", "상장기업", "투자대상"],
                "투자": ["펀드", "포트폴리오", "자산운용"]
            }
        }
        
        expanded = keywords.copy()
        domain_expansions = expansion_map.get(domain, {})
        
        for keyword in keywords:
            if keyword in domain_expansions:
                expanded.extend(domain_expansions[keyword])
        
        return list(set(expanded))  # 중복 제거
    
    def _extract_core_terms(self, keywords: List[str]) -> List[str]:
        """핵심 용어만 추출"""
        high_priority_terms = [
            "기업", "산업", "제품", "수출", "종목", "투자",
            "기술", "시스템", "성장", "실적"
        ]
        
        core_terms = []
        for keyword in keywords:
            if keyword in high_priority_terms:
                core_terms.append(keyword)
        
        # 최소 2개는 보장
        if len(core_terms) < 2:
            core_terms.extend(keywords[:3-len(core_terms)])
        
        return core_terms
    
    def evaluate_search_quality(
        self, 
        results: List[Dict[str, Any]], 
        original_query: str,
        strategy_used: SearchStrategy
    ) -> float:
        """검색 결과 품질 평가"""
        if not results:
            return 0.0
        
        quality_score = 0.0
        
        # 1. 결과 개수 평가 (0.2)
        result_count_score = min(len(results) / 5.0, 1.0) * 0.2
        quality_score += result_count_score
        
        # 2. 제목 관련성 평가 (0.3)
        query_words = set(original_query.lower().split())
        title_relevance = 0.0
        
        for result in results:
            title = result.get("title", "").lower()
            title_words = set(title.split())
            
            # 단어 겹침 비율
            if query_words:
                overlap = len(query_words & title_words) / len(query_words)
                title_relevance += overlap
        
        if results:
            title_relevance = (title_relevance / len(results)) * 0.3
            quality_score += title_relevance
        
        # 3. 날짜 신선도 평가 (0.2)
        date_score = self._evaluate_date_freshness(results) * 0.2
        quality_score += date_score
        
        # 4. 전략 신뢰도 (0.3)
        strategy_score = strategy_used.weight * 0.3
        quality_score += strategy_score
        
        return min(quality_score, 1.0)
    
    def _evaluate_date_freshness(self, results: List[Dict[str, Any]]) -> float:
        """날짜 신선도 평가"""
        import datetime
        
        now = datetime.datetime.now()
        freshness_scores = []
        
        for result in results:
            date_str = result.get("date", "")
            if not date_str:
                freshness_scores.append(0.3)  # 날짜 없음
                continue
            
            try:
                # 다양한 날짜 형식 파싱 시도
                result_date = None
                for fmt in ["%Y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        result_date = datetime.datetime.strptime(date_str[:10], fmt)
                        break
                    except:
                        continue
                
                if result_date:
                    days_old = (now - result_date).days
                    # 30일 이내: 1.0, 90일 이내: 0.7, 180일 이내: 0.4, 그 이후: 0.2
                    if days_old <= 30:
                        freshness_scores.append(1.0)
                    elif days_old <= 90:
                        freshness_scores.append(0.7)
                    elif days_old <= 180:
                        freshness_scores.append(0.4)
                    else:
                        freshness_scores.append(0.2)
                else:
                    freshness_scores.append(0.3)
                    
            except Exception:
                freshness_scores.append(0.3)
        
        return sum(freshness_scores) / len(freshness_scores) if freshness_scores else 0.3

# 전역 인스턴스
advanced_search_engine = AdvancedSearchEngine()