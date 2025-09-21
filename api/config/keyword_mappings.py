"""
키워드 확장 매핑 설정
Context Engineering을 위한 도메인별 키워드 매핑과 유사어 확장
"""
from typing import Dict, List, Set
from dataclasses import dataclass

@dataclass
class KeywordWeight:
    """키워드 가중치 정보"""
    keyword: str
    weight: float = 1.0
    priority: int = 1  # 1=high, 2=medium, 3=low

# 도메인별 핵심 키워드 매핑 (범용적 비즈니스 도메인)
DOMAIN_KEYWORDS = {
    "technology": {
        "triggers": ["기술", "혁신", "디지털", "AI", "인공지능", "소프트웨어"],
        "expansions": [
            KeywordWeight("기술", 2.0, 1),
            KeywordWeight("혁신", 1.8, 1),
            KeywordWeight("디지털", 1.9, 1),
            KeywordWeight("인공지능", 1.8, 1),
            KeywordWeight("AI", 1.8, 1),
            KeywordWeight("소프트웨어", 1.7, 1),
            KeywordWeight("플랫폼", 1.6, 2),
            KeywordWeight("솔루션", 1.5, 2),
            KeywordWeight("시스템", 1.4, 2),
            KeywordWeight("서비스", 1.3, 2),
        ],
        "synonyms": {
            "기술": ["테크", "테크놀로지", "기술력"],
            "혁신": ["이노베이션", "신기술", "첨단기술"],
            "AI": ["인공지능", "머신러닝", "딥러닝"]
        }
    },
    "manufacturing": {
        "triggers": ["제조", "생산", "공장", "설비", "자동화"],
        "expansions": [
            KeywordWeight("제조", 2.0, 1),
            KeywordWeight("생산", 1.9, 1),
            KeywordWeight("공장", 1.7, 1),
            KeywordWeight("설비", 1.6, 2),
            KeywordWeight("자동화", 1.8, 1),
            KeywordWeight("품질", 1.5, 2),
            KeywordWeight("효율", 1.4, 2),
        ],
        "synonyms": {
            "제조": ["제조업", "생산", "가공"],
            "생산": ["제조", "생산성", "산출"],
            "자동화": ["스마트팩토리", "무인화", "디지털화"]
        }
    },
    "export": {
        "triggers": ["수출", "해외", "국제", "글로벌"],
        "expansions": [
            KeywordWeight("수출", 2.0, 1),
            KeywordWeight("해외", 1.8, 1),
            KeywordWeight("국제", 1.6, 2),
            KeywordWeight("외교", 1.4, 2),
            KeywordWeight("무역", 1.7, 1),
            KeywordWeight("해외진출", 1.5, 2),
            KeywordWeight("글로벌", 1.6, 2),
            KeywordWeight("해외수주", 1.8, 1),
            KeywordWeight("외화획득", 1.3, 3),
        ],
        "synonyms": {
            "수출": ["해외판매", "외국판매", "수출실적"],
            "해외": ["외국", "해외시장", "국외"],
            "글로벌": ["세계", "국제적", "전세계"]
        }
    },
    "stock": {
        "triggers": ["종목", "주식", "투자", "증권"],
        "expansions": [
            KeywordWeight("종목", 2.0, 1),
            KeywordWeight("주식", 2.0, 1),
            KeywordWeight("투자", 1.8, 1),
            KeywordWeight("증권", 1.6, 2),
            KeywordWeight("시장", 1.5, 2),
            KeywordWeight("주가", 1.7, 1),
            KeywordWeight("펀드", 1.3, 3),
            KeywordWeight("ETF", 1.2, 3),
            KeywordWeight("포트폴리오", 1.1, 3),
        ],
        "synonyms": {
            "종목": ["주식종목", "투자종목", "기업"],
            "주식": ["주식투자", "증권투자", "주식매매"],
            "투자": ["자산투자", "금융투자", "투자전략"]
        }
    },
    "outlook": {
        "triggers": ["유망", "전망", "기대", "성장"],
        "expansions": [
            KeywordWeight("유망", 1.8, 1),
            KeywordWeight("전망", 2.0, 1),
            KeywordWeight("기대", 1.6, 2),
            KeywordWeight("성장", 1.9, 1),
            KeywordWeight("잠재력", 1.5, 2),
            KeywordWeight("가능성", 1.4, 2),
            KeywordWeight("전도유망", 1.7, 1),
            KeywordWeight("미래", 1.3, 3),
        ],
        "synonyms": {
            "전망": ["미래전망", "장래성", "향후전망"],
            "성장": ["성장성", "발전", "확대"],
            "유망": ["전도유망", "장래성", "잠재력"]
        }
    }
}

# 산업별 키워드 매핑 (다양한 산업 도메인)
INDUSTRY_KEYWORDS = {
    "technology": [
        KeywordWeight("IT", 2.0, 1),
        KeywordWeight("소프트웨어", 1.9, 1),
        KeywordWeight("하드웨어", 1.7, 2),
        KeywordWeight("클라우드", 1.8, 1),
        KeywordWeight("데이터", 1.6, 2),
        KeywordWeight("보안", 1.5, 2),
    ],
    "bio": [
        KeywordWeight("바이오", 1.9, 1),
        KeywordWeight("제약", 1.8, 1),
        KeywordWeight("의료", 1.7, 1),
        KeywordWeight("헬스케어", 1.8, 1),
        KeywordWeight("신약", 1.9, 1),
        KeywordWeight("진단", 1.6, 2),
    ],
    "energy": [
        KeywordWeight("에너지", 1.9, 1),
        KeywordWeight("신재생", 1.8, 1),
        KeywordWeight("태양광", 1.7, 1),
        KeywordWeight("풍력", 1.6, 2),
        KeywordWeight("배터리", 1.8, 1),
        KeywordWeight("전기차", 1.7, 1),
    ],
    "semiconductor": [
        KeywordWeight("반도체", 2.0, 1),
        KeywordWeight("칩", 1.8, 1),
        KeywordWeight("메모리", 1.7, 1),
        KeywordWeight("시스템반도체", 1.9, 1),
        KeywordWeight("파운드리", 1.6, 2),
    ]
}

# 회사별 키워드 확장 (일반적인 기업 패턴)
COMPANY_KEYWORDS = {
    "samsung": {
        "triggers": ["삼성"],
        "expansions": [
            KeywordWeight("삼성", 2.0, 1),
            KeywordWeight("삼성전자", 1.9, 1),
            KeywordWeight("삼성그룹", 1.8, 1),
            KeywordWeight("삼성바이오로직스", 1.7, 1),
            KeywordWeight("삼성SDI", 1.6, 2),
        ]
    },
    "lg": {
        "triggers": ["LG", "엘지"],
        "expansions": [
            KeywordWeight("LG", 2.0, 1),
            KeywordWeight("LG전자", 1.9, 1),
            KeywordWeight("LG화학", 1.8, 1),
            KeywordWeight("LG에너지솔루션", 1.9, 1),
        ]
    },
    "sk": {
        "triggers": ["SK", "에스케이"],
        "expansions": [
            KeywordWeight("SK", 2.0, 1),
            KeywordWeight("SK하이닉스", 1.9, 1),
            KeywordWeight("SK텔레콤", 1.7, 1),
            KeywordWeight("SK이노베이션", 1.8, 1),
        ]
    }
}

# 시간 관련 키워드
TIME_KEYWORDS = {
    "recent": {
        "triggers": ["최근", "최신", "요즘"],
        "expansions": [
            KeywordWeight("최근", 1.8, 1),
            KeywordWeight("최신", 1.9, 1),
            KeywordWeight("2024", 2.0, 1),
            KeywordWeight("2025", 2.0, 1),
            KeywordWeight("올해", 1.7, 1),
            KeywordWeight("금년", 1.6, 2),
            KeywordWeight("현재", 1.5, 2),
        ]
    },
    "past": {
        "triggers": ["과거", "이전", "지난"],
        "expansions": [
            KeywordWeight("과거", 1.6, 2),
            KeywordWeight("이전", 1.5, 2),
            KeywordWeight("지난", 1.7, 1),
            KeywordWeight("작년", 1.8, 1),
            KeywordWeight("2023", 1.7, 1),
        ]
    }
}

# 지역별 키워드
REGION_KEYWORDS = {
    "korea": {
        "triggers": ["한국", "대한민국"],
        "expansions": [
            KeywordWeight("한국", 1.9, 1),
            KeywordWeight("대한민국", 1.8, 1),
            KeywordWeight("KOREA", 1.6, 2),
            KeywordWeight("K-", 1.7, 1),
            KeywordWeight("국내", 1.5, 2),
        ]
    },
    "usa": {
        "triggers": ["미국", "usa", "america"],
        "expansions": [
            KeywordWeight("미국", 1.8, 1),
            KeywordWeight("USA", 1.7, 1),
            KeywordWeight("US", 1.6, 2),
            KeywordWeight("아메리카", 1.4, 3),
        ]
    },
    "europe": {
        "triggers": ["유럽", "eu"],
        "expansions": [
            KeywordWeight("유럽", 1.7, 1),
            KeywordWeight("EU", 1.6, 2),
            KeywordWeight("독일", 1.5, 2),
            KeywordWeight("프랑스", 1.4, 2),
            KeywordWeight("영국", 1.4, 2),
        ]
    }
}

# 불용어 (검색에서 제외할 단어들)
STOPWORDS = {
    "은", "는", "이", "가", "을", "를", "의", "에", "에서", "로", "으로", 
    "관련", "대한", "있는", "없는", "같은", "다른", "그런", "이런", "저런",
    "하는", "되는", "있다", "없다", "이다", "아니다", "그것", "이것", "저것"
}

def get_all_keyword_mappings() -> Dict:
    """모든 키워드 매핑 정보를 반환"""
    return {
        "domain": DOMAIN_KEYWORDS,
        "industry": INDUSTRY_KEYWORDS,
        "company": COMPANY_KEYWORDS,
        "time": TIME_KEYWORDS,
        "region": REGION_KEYWORDS,
        "stopwords": STOPWORDS
    }