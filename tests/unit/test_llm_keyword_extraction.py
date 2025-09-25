#!/usr/bin/env python3
"""
LLM 기반 키워드 추출 시스템 테스트
"""

import sys
import asyncio
sys.path.append('.')

# Mock logger for testing
class MockLogger:
    def info(self, *args): print(f"[INFO] {' '.join(map(str, args))}")
    def error(self, *args): print(f"[ERROR] {' '.join(map(str, args))}")
    def warning(self, *args): print(f"[WARNING] {' '.join(map(str, args))}")
    def debug(self, *args): print(f"[DEBUG] {' '.join(map(str, args))}")

sys.modules['loguru'] = type('MockModule', (), {'logger': MockLogger()})()

async def test_llm_keyword_extraction():
    """LLM 키워드 추출 테스트"""
    print("=== LLM 기반 키워드 추출 시스템 테스트 ===\n")
    
    try:
        from api.utils.llm_keyword_extractor import llm_extractor
        
        # Ollama 서버 상태 확인
        print("1. Ollama 서버 상태 확인...")
        is_healthy = await llm_extractor.health_check()
        
        if not is_healthy:
            print("❌ Ollama 서버에 연결할 수 없습니다.")
            print("   다음을 확인하세요:")
            print("   - Ollama가 설치되어 있는가: ollama --version")
            print("   - Ollama 서비스가 실행 중인가: ollama serve")
            print("   - 모델이 다운로드되어 있는가: ollama pull qwen3:8b-q8_0")
            print("   - 원격 Ollama 서버(192.168.0.11:11434) 접근 가능한가?")
            print("\n   폴백 테스트로 진행합니다...\n")
        else:
            print("✅ Ollama 서버 연결 성공\n")
        
        # 테스트 쿼리들
        test_queries = [
            "한화 지상무기 수출 관련 유망 종목은?",
            "KAI 항공우주 최근 실적 전망은 어떤가?", 
            "방산업체들의 해외진출 현황을 알고 싶어"
        ]
        
        print("2. LLM 키워드 추출 테스트\n")
        
        for i, query in enumerate(test_queries, 1):
            print(f"{i}. 질문: \"{query}\"")
            
            try:
                # 도메인 힌트 준비
                domain_hints = []
                q_lower = query.lower()
                
                if any(word in q_lower for word in ["방산", "무기", "국방"]):
                    domain_hints.append("방산/국방산업")
                if any(word in q_lower for word in ["수출", "해외"]):
                    domain_hints.append("수출/무역")  
                if any(word in q_lower for word in ["주식", "종목", "투자"]):
                    domain_hints.append("금융/주식투자")
                if any(word in q_lower for word in ["항공", "우주"]):
                    domain_hints.append("항공우주")
                
                print(f"   도메인 힌트: {domain_hints}")
                
                # LLM 키워드 추출 실행
                result = await llm_extractor.extract_keywords_async(query, domain_hints)
                
                print(f"   ✅ 추출 성공 (신뢰도: {result.confidence:.2f})")
                print(f"   🔍 키워드 ({len(result.keywords)}개): {result.keywords}")
                
                if result.weighted_keywords:
                    top_weighted = sorted(result.weighted_keywords.items(), key=lambda x: -x[1])[:5]
                    print(f"   ⚖️  가중치 상위: {dict(top_weighted)}")
                
                if result.categories:
                    non_empty_categories = {k: v for k, v in result.categories.items() if v}
                    if non_empty_categories:
                        print(f"   📂 카테고리: {non_empty_categories}")
                
                if result.reasoning:
                    print(f"   💭 추출 근거: {result.reasoning[:100]}{'...' if len(result.reasoning) > 100 else ''}")
                
                print()
                
            except Exception as e:
                print(f"   ❌ 실패: {e}")
                print()
        
        print("=== 테스트 완료 ===")
        print("\n📊 LLM 기반 키워드 추출의 장점:")
        print("  ✅ 문맥 이해: 질문 전체의 의도 파악")
        print("  ✅ 의미적 확장: 관련 개념 자동 추출")
        print("  ✅ 동적 적응: 새로운 도메인/용어 대응")
        print("  ✅ 다층적 분석: 명시적/암시적 의도 모두 추출")
        print("  ✅ 신뢰도 평가: 결과 품질 자체 평가")
        
    except ImportError as e:
        print(f"❌ 모듈 임포트 실패: {e}")
        print("   langchain-ollama가 설치되어 있는지 확인하세요.")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def test_fallback_extraction():
    """폴백 키워드 추출 테스트"""
    print("\n=== 폴백 키워드 추출 테스트 ===")
    
    try:
        from api.services.chat_service import _fallback_keyword_extraction
        
        test_queries = [
            "한화 지상무기 수출",
            "KAI 항공우주 투자 전망",
            "방산업체 해외진출"
        ]
        
        for query in test_queries:
            keywords = await _fallback_keyword_extraction(query)
            print(f"질문: \"{query}\" → 키워드: {keywords}")
            
    except Exception as e:
        print(f"❌ 폴백 테스트 실패: {e}")

def main():
    """메인 실행 함수"""
    print("🚀 Context Engineering - LLM 기반 키워드 추출 테스트\n")
    
    asyncio.run(test_llm_keyword_extraction())
    asyncio.run(test_fallback_extraction())

if __name__ == "__main__":
    main()