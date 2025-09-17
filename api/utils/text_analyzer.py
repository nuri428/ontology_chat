"""
텍스트 분석 유틸리티
간단한 형태소 분석 및 키워드 추출을 위한 헬퍼 함수들
"""
import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass

@dataclass
class Token:
    """토큰 정보"""
    text: str
    pos: str  # part-of-speech (품사)
    importance: float = 1.0

# 한국어 조사/어미 패턴
KOREAN_PARTICLES = {
    "은", "는", "이", "가", "을", "를", "의", "에", "에서", "로", "으로", "와", "과",
    "도", "만", "까지", "부터", "한테", "에게", "께", "께서", "라", "이라", "라고",
    "하고", "하며", "하니", "하지만", "그러나", "또한", "그리고", "그래서"
}

KOREAN_ENDINGS = {
    "다", "요", "니다", "습니다", "세요", "하세요", "해요", "된다", "한다", "있다", 
    "없다", "이다", "아니다", "같다", "다른", "새로운", "좋은", "나쁜"
}

# 의미있는 접미사들
MEANINGFUL_SUFFIXES = {
    "산업": 3.0, "기업": 2.5, "회사": 2.0, "업체": 2.0, "그룹": 2.0,
    "시스템": 2.5, "기술": 2.0, "장비": 2.0, "제품": 1.8,
    "시장": 2.5, "수출": 3.0, "무역": 2.5, "해외": 2.0,
    "투자": 2.5, "종목": 3.0, "주식": 3.0, "증권": 2.0
}

# 중요도가 높은 명사들
HIGH_IMPORTANCE_NOUNS = {
    "방산": 3.0, "국방": 3.0, "무기": 3.0, "지상무기": 3.5,
    "수출": 3.0, "해외": 2.5, "글로벌": 2.5,
    "종목": 3.0, "주식": 3.0, "투자": 2.8, "시장": 2.5,
    "한화": 3.0, "kai": 3.0, "lignex1": 3.0,
    "성장": 2.5, "전망": 2.8, "유망": 2.8
}

def simple_korean_tokenize(text: str) -> List[Token]:
    """간단한 한국어 토큰화"""
    text = text.lower().strip()
    tokens = []
    
    # 1. 공백 기준 분리
    words = text.split()
    
    for word in words:
        if len(word) < 2:
            continue
            
        # 2. 조사 분리 시도
        base_word = _remove_particles(word)
        
        # 3. 품사 추정 및 중요도 계산
        pos = _estimate_pos(base_word)
        importance = _calculate_importance(base_word, pos)
        
        if base_word and base_word not in KOREAN_PARTICLES:
            tokens.append(Token(base_word, pos, importance))
    
    return tokens

def _remove_particles(word: str) -> str:
    """조사 제거"""
    # 일반적인 조사 패턴들
    particle_patterns = [
        r'에서$', r'에게$', r'한테$', r'로부터$', r'으로$', r'로$',
        r'은$', r'는$', r'이$', r'가$', r'을$', r'를$', r'의$',
        r'와$', r'과$', r'도$', r'만$', r'까지$', r'부터$'
    ]
    
    for pattern in particle_patterns:
        result = re.sub(pattern, '', word)
        if result != word and len(result) >= 2:
            return result
    
    return word

def _estimate_pos(word: str) -> str:
    """간단한 품사 추정"""
    # 숫자 패턴
    if re.match(r'^\\d+', word):
        return 'NUM'
    
    # 영어 패턴
    if re.match(r'^[a-zA-Z]+$', word):
        return 'ENG'
    
    # 회사명 패턴
    company_patterns = ['한화', 'kai', '삼성', '현대', 'lg', '포스코']
    if any(pattern in word for pattern in company_patterns):
        return 'COMPANY'
    
    # 기술/산업 용어
    tech_patterns = ['시스템', '기술', '장비', '솔루션', '플랫폼']
    if any(pattern in word for pattern in tech_patterns):
        return 'TECH'
    
    # 경제/금융 용어
    finance_patterns = ['투자', '수익', '매출', '실적', '주가', '시장']
    if any(pattern in word for pattern in finance_patterns):
        return 'FINANCE'
    
    # 기본적으로 명사로 분류
    return 'NOUN'

def _calculate_importance(word: str, pos: str) -> float:
    """단어 중요도 계산"""
    base_importance = 1.0
    
    # 1. 미리 정의된 중요 단어 체크
    if word in HIGH_IMPORTANCE_NOUNS:
        base_importance = HIGH_IMPORTANCE_NOUNS[word]
    
    # 2. 품사별 가중치
    pos_weights = {
        'COMPANY': 2.5,
        'TECH': 2.0,
        'FINANCE': 2.2,
        'NUM': 1.5,
        'ENG': 1.8,
        'NOUN': 1.0
    }
    
    pos_weight = pos_weights.get(pos, 1.0)
    
    # 3. 길이별 가중치 (너무 짧거나 긴 단어는 낮은 중요도)
    length = len(word)
    if length <= 1:
        length_weight = 0.3
    elif length == 2:
        length_weight = 0.8
    elif 3 <= length <= 5:
        length_weight = 1.2
    elif 6 <= length <= 8:
        length_weight = 1.0
    else:
        length_weight = 0.7
    
    # 4. 접미사 보너스
    suffix_bonus = 1.0
    for suffix, bonus in MEANINGFUL_SUFFIXES.items():
        if word.endswith(suffix):
            suffix_bonus = max(suffix_bonus, bonus)
    
    final_importance = base_importance * pos_weight * length_weight * suffix_bonus
    return min(final_importance, 5.0)  # 최대값 제한

def extract_key_phrases(text: str, max_phrases: int = 10) -> List[Tuple[str, float]]:
    """핵심 구문 추출"""
    tokens = simple_korean_tokenize(text)
    
    # 중요도 기준 정렬
    sorted_tokens = sorted(tokens, key=lambda x: -x.importance)
    
    # 상위 토큰들을 구문으로 변환
    key_phrases = []
    for token in sorted_tokens[:max_phrases]:
        if token.importance > 1.0:  # 임계값 이상만 선택
            key_phrases.append((token.text, token.importance))
    
    return key_phrases

def enhance_query_with_morphology(query: str) -> Dict[str, any]:
    """형태소 분석을 통한 쿼리 강화"""
    tokens = simple_korean_tokenize(query)
    key_phrases = extract_key_phrases(query)
    
    # 품사별 분류
    companies = [t.text for t in tokens if t.pos == 'COMPANY']
    tech_terms = [t.text for t in tokens if t.pos == 'TECH']
    finance_terms = [t.text for t in tokens if t.pos == 'FINANCE']
    
    # 고중요도 키워드만 추출
    high_importance_keywords = [t.text for t in tokens if t.importance >= 2.0]
    
    return {
        "tokens": [(t.text, t.pos, t.importance) for t in tokens],
        "key_phrases": key_phrases,
        "companies": companies,
        "tech_terms": tech_terms,
        "finance_terms": finance_terms,
        "high_importance_keywords": high_importance_keywords,
        "query_complexity": len([t for t in tokens if t.importance >= 1.5])
    }

def suggest_related_terms(word: str) -> List[str]:
    """연관 용어 제안"""
    word = word.lower()
    suggestions = []
    
    # 도메인별 연관어 사전
    related_terms = {
        "방산": ["국방", "군사", "무기", "장비", "시스템", "기술"],
        "무기": ["방산", "지상무기", "장비", "시스템", "국방"],
        "수출": ["해외", "국제", "무역", "글로벌", "해외진출"],
        "투자": ["주식", "종목", "증권", "시장", "포트폴리오"],
        "한화": ["한화시스템", "한화디펜스", "한화에어로스페이스"],
        "성장": ["전망", "기대", "잠재력", "발전", "확장"]
    }
    
    for key, terms in related_terms.items():
        if key in word or word in key:
            suggestions.extend(terms)
    
    return list(set(suggestions))  # 중복 제거