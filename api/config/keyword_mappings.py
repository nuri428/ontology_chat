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

# 도메인별 핵심 키워드 매핑
DOMAIN_KEYWORDS = {
    "defense": {
        "triggers": ["지상무기", "방산", "무기", "국방", "군사", "전투"],
        "expansions": [
            KeywordWeight("지상무기", 2.0, 1),
            KeywordWeight("무기", 1.8, 1),
            KeywordWeight("방산", 2.0, 1),
            KeywordWeight("방위", 1.5, 2),
            KeywordWeight("군사", 1.6, 2),
            KeywordWeight("국방", 1.7, 1),
            KeywordWeight("전투", 1.4, 2),
            KeywordWeight("장비", 1.3, 2),
            KeywordWeight("시스템", 1.2, 3),
            KeywordWeight("기술", 1.1, 3),
        ],
        "synonyms": {
            "지상무기": ["육상무기", "땅무기", "지상장비"],
            "방산": ["국방산업", "방위산업", "군사산업"],
            "무기": ["병기", "무기체계", "무기시스템"]
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

# 산업별 키워드 매핑
INDUSTRY_KEYWORDS = {
    "defense": [
        KeywordWeight("방산", 2.0, 1),
        KeywordWeight("국방", 1.9, 1),
        KeywordWeight("군사", 1.7, 2),
        KeywordWeight("무기", 1.8, 1),
        KeywordWeight("장비", 1.5, 2),
        KeywordWeight("시스템", 1.3, 3),
    ],
    "aerospace": [
        KeywordWeight("항공", 1.8, 1),
        KeywordWeight("우주", 1.9, 1),
        KeywordWeight("위성", 1.7, 2),
        KeywordWeight("로켓", 1.6, 2),
        KeywordWeight("발사체", 1.5, 2),
        KeywordWeight("항공우주", 2.0, 1),
    ],
    "nuclear": [
        KeywordWeight("원전", 1.9, 1),
        KeywordWeight("원자력", 2.0, 1),
        KeywordWeight("핵", 1.6, 2),
        KeywordWeight("에너지", 1.4, 3),
        KeywordWeight("발전", 1.3, 3),
        KeywordWeight("플랜트", 1.5, 2),
    ]
}

# 회사별 키워드 확장
COMPANY_KEYWORDS = {
    "hanwha": {
        "triggers": ["한화"],
        "expansions": [
            KeywordWeight("한화", 2.0, 1),
            KeywordWeight("한화그룹", 1.8, 1),
            KeywordWeight("한화시스템", 1.9, 1),
            KeywordWeight("한화에어로스페이스", 1.8, 1),
            KeywordWeight("한화디펜스", 1.9, 1),
            KeywordWeight("한화정밀기계", 1.6, 2),
            KeywordWeight("한화테크윈", 1.5, 2),
        ]
    },
    "kai": {
        "triggers": ["kai", "카이", "한국항공우주"],
        "expansions": [
            KeywordWeight("KAI", 2.0, 1),
            KeywordWeight("카이", 2.0, 1),
            KeywordWeight("한국항공우주", 2.0, 1),
            KeywordWeight("한국항공우주산업", 1.9, 1),
        ]
    },
    "lignex1": {
        "triggers": ["lignex1", "엘아이지넥스원", "엘아이지"],
        "expansions": [
            KeywordWeight("LIG넥스원", 2.0, 1),
            KeywordWeight("엘아이지넥스원", 2.0, 1),
            KeywordWeight("엘아이지", 1.8, 1),
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