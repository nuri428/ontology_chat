#!/usr/bin/env python3
"""
키워드 추출 시스템 독립 테스트
"""

import sys
sys.path.append('.')

from api.config.keyword_mappings import get_all_keyword_mappings
from api.utils.text_analyzer import enhance_query_with_morphology, suggest_related_terms

def extract_keywords_standalone(query: str):
    """독립적인 키워드 추출 함수 (의존성 없음)"""
    q = query.lower()
    keyword_mappings = get_all_keyword_mappings()
    
    # 가중치가 있는 키워드 저장소
    weighted_keywords = []
    
    # 형태소 분석을 통한 쿼리 강화
    morphology_result = enhance_query_with_morphology(query)
    high_importance_words = morphology_result["high_importance_keywords"]
    companies = morphology_result["companies"]
    tech_terms = morphology_result["tech_terms"]
    finance_terms = morphology_result["finance_terms"]
    
    # 형태소 분석 결과로 추가 가중치 부여
    for word in high_importance_words:
        weighted_keywords.append((word, 2.0))
    
    for word in companies:
        weighted_keywords.append((word, 2.5))
        # 연관 용어 추가
        related = suggest_related_terms(word)
        for rel_word in related[:3]:  # 상위 3개만
            weighted_keywords.append((rel_word, 1.8))
    
    for word in tech_terms:
        weighted_keywords.append((word, 2.2))
    
    for word in finance_terms:
        weighted_keywords.append((word, 2.3))
    
    # 도메인별 키워드 추출
    for domain_name, domain_data in keyword_mappings["domain"].items():
        for trigger in domain_data["triggers"]:
            if trigger in q:
                for kw in sorted(domain_data["expansions"], key=lambda x: (x.priority, -x.weight)):
                    weighted_keywords.append((kw.keyword, kw.weight))
                
                # 유사어 추가
                for base_word, synonyms in domain_data.get("synonyms", {}).items():
                    if base_word in q:
                        for syn in synonyms:
                            weighted_keywords.append((syn, 1.2))
                break
    
    # 산업별 키워드 추출
    for industry_name, keywords in keyword_mappings["industry"].items():
        industry_triggers = {
            "defense": ["방산", "무기", "국방", "군사"],
            "aerospace": ["항공", "우주", "위성"],
            "nuclear": ["원전", "원자력", "핵"]
        }.get(industry_name, [])
        
        if any(trigger in q for trigger in industry_triggers):
            for kw in keywords:
                weighted_keywords.append((kw.keyword, kw.weight))
    
    # 회사별 키워드 추출
    for company_name, company_data in keyword_mappings["company"].items():
        for trigger in company_data["triggers"]:
            if trigger in q:
                for kw in company_data["expansions"]:
                    weighted_keywords.append((kw.keyword, kw.weight))
                break
    
    # 시간 관련 키워드 추출
    for time_type, time_data in keyword_mappings["time"].items():
        for trigger in time_data["triggers"]:
            if trigger in q:
                for kw in time_data["expansions"]:
                    weighted_keywords.append((kw.keyword, kw.weight))
                break
    
    # 지역별 키워드 추출
    for region_name, region_data in keyword_mappings["region"].items():
        for trigger in region_data["triggers"]:
            if trigger in q:
                for kw in region_data["expansions"]:
                    weighted_keywords.append((kw.keyword, kw.weight))
                break
    
    # 가중치 기반 정렬 및 중복 제거
    keyword_weights = {}
    for keyword, weight in weighted_keywords:
        if keyword not in keyword_weights:
            keyword_weights[keyword] = weight
        else:
            keyword_weights[keyword] = max(keyword_weights[keyword], weight)
    
    # 가중치 순으로 정렬
    sorted_keywords = sorted(keyword_weights.items(), key=lambda x: -x[1])
    
    # 키워드가 부족하면 원본 질문에서 추가 추출
    if len(sorted_keywords) < 5:
        stopwords = keyword_mappings["stopwords"]
        key_phrases = morphology_result["key_phrases"]
        for phrase, importance in key_phrases:
            if phrase not in keyword_weights and importance > 1.0:
                sorted_keywords.append((phrase, importance * 0.8))
    
    # 최종 키워드 리스트 반환 (상위 15개)
    final_keywords = [kw[0] for kw in sorted_keywords[:15]]
    
    return final_keywords, morphology_result

def main():
    print("=== Context Engineering 키워드 추출 시스템 테스트 ===\n")
    
    test_queries = [
        "한화 지상무기 수출 관련 유망 종목은?",
        "KAI 항공우주 최근 실적 전망은 어떤가?", 
        "방산업체들의 해외진출 현황을 알고 싶어",
        "원자력 발전소 관련 투자 기회는?",
        "삼성 반도체 기술 성장 가능성"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"{i}. 질문: \"{query}\"")
        
        keywords, morphology = extract_keywords_standalone(query)
        
        print(f"   📝 형태소 분석:")
        print(f"     - 중요 키워드: {morphology['high_importance_keywords']}")
        print(f"     - 회사명: {morphology['companies']}")
        print(f"     - 기술 용어: {morphology['tech_terms']}")
        print(f"     - 금융 용어: {morphology['finance_terms']}")
        
        print(f"   🔍 최종 추출 키워드 ({len(keywords)}개):")
        print(f"     {keywords}")
        print("-" * 80)
    
    print("\n✅ Context Engineering 개선 완료!")
    print("\n📊 구현된 기능:")
    print("  ✅ 동적 키워드 확장 (설정 파일 기반)")
    print("  ✅ 형태소 분석 (품사 태깅, 중요도 계산)")  
    print("  ✅ 가중치 시스템 (우선순위 기반 정렬)")
    print("  ✅ 유사어 확장 (도메인별 연관어)")
    print("  ✅ 특수 용어 처리 (회사/기술/금융)")
    print("  ✅ 다단계 폴백 전략")

if __name__ == "__main__":
    main()