#!/usr/bin/env python3
"""
새로운 LLM 기반 컨텍스트 인사이트 시스템 테스트
"""

import sys
import asyncio
sys.path.append('.')

# Mock logger
class MockLogger:
    def info(self, *args): print(f'[INFO] {" ".join(map(str, args))}')
    def error(self, *args): print(f'[ERROR] {" ".join(map(str, args))}')
    def warning(self, *args): print(f'[WARNING] {" ".join(map(str, args))}')
    def debug(self, *args): pass

sys.modules['loguru'] = type('MockModule', (), {'logger': MockLogger()})()

async def test_context_insight_generator():
    """컨텍스트 인사이트 생성기 테스트"""
    print("=== LLM 기반 컨텍스트 인사이트 시스템 테스트 ===\n")
    
    try:
        from api.services.context_insight_generator import insight_generator
        
        # 테스트 데이터 준비
        test_cases = [
            {
                "query": "한화 지상무기 수출 관련 유망 종목은?",
                "news_hits": [
                    {"title": "한화시스템, K9 자주포 수출 확대", "url": "test1.com"},
                    {"title": "방산업체 해외진출 가속화", "url": "test2.com"},
                    {"title": "정부, 방산수출 지원정책 발표", "url": "test3.com"}
                ],
                "graph_summary": {"Company": ["한화", "한화시스템"], "Weapon": ["K9자주포", "지상무기"]},
                "stock_info": {"symbol": "272210.KS", "price": "45000"}
            },
            {
                "query": "KAI 항공우주 최근 실적 전망은?",
                "news_hits": [
                    {"title": "KAI, KF-21 양산 계약 체결", "url": "test4.com"},
                    {"title": "한국형 전투기 수출 기대감 확산", "url": "test5.com"}
                ],
                "graph_summary": {"Company": ["KAI"], "Program": ["KF-21"]},
                "stock_info": None
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}. 테스트 케이스: \"{test_case['query']}\"")
            print(f"   뉴스: {len(test_case['news_hits'])}건")
            print(f"   그래프: {test_case['graph_summary']}")
            print(f"   주식: {test_case['stock_info']}")
            
            # 인사이트 생성
            result = await insight_generator.generate_insights(
                query=test_case['query'],
                news_hits=test_case['news_hits'],
                graph_summary=test_case['graph_summary'],
                stock_info=test_case['stock_info']
            )
            
            print(f"   ✅ 인사이트 생성 완료")
            print(f"   📊 생성된 인사이트: {len(result.insights)}개")
            print(f"   🎯 신뢰도: {result.confidence:.2f}")
            
            if result.insights:
                print("   📋 인사이트 목록:")
                for insight in result.insights:
                    print(f"     - {insight.icon} {insight.title}: {insight.content[:50]}...")
            
            if result.overall_context:
                print(f"   💡 종합 분석: {result.overall_context[:80]}...")
            
            # 디스플레이 포맷 테스트
            display_text = insight_generator.format_insights_for_display(result)
            if display_text:
                print(f"   📝 마크다운 포맷 생성: {len(display_text.split())}단어")
            
            print()
        
        print("🎉 컨텍스트 인사이트 시스템 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def test_chat_service_integration():
    """ChatService 통합 테스트"""
    print("\n=== ChatService 통합 테스트 ===\n")
    
    try:
        # Mock 설정
        import os
        import importlib.util
        
        # config 모듈 로드 - 직접 import 사용
        # config_path = os.path.join(os.path.dirname(__file__), 'api', 'config.py')
        # spec = importlib.util.spec_from_file_location("config", config_path)
        # config_module = importlib.util.module_from_spec(spec)
        # spec.loader.exec_module(config_module)
        
        # ChatService에서 _compose_answer 메서드만 테스트
        from api.services.chat_service import ChatService
        
        chat_service = ChatService()
        
        test_query = "한화 지상무기 수출 투자"
        test_news = [{"title": "한화 방산 수출 증가", "url": "test.com", "date": "2024-01-01"}]
        test_graph = [{"n": {"name": "한화"}, "labels": ["Company"]}]
        test_stock = {"symbol": "272210.KS", "price": 45000}
        
        print(f"통합 테스트 쿼리: \"{test_query}\"")
        
        # _compose_answer 호출 (비동기)
        answer = await chat_service._compose_answer(
            query=test_query,
            news_hits=test_news,
            graph_rows=test_graph,
            stock=test_stock
        )
        
        print("✅ ChatService 통합 성공")
        print(f"📄 생성된 답변 길이: {len(answer)}자")
        
        # 답변에 컨텍스트 인사이트가 포함되었는지 확인
        if "컨텍스트 인사이트" in answer or "🔍" in answer:
            print("✅ 동적 컨텍스트 인사이트가 답변에 포함됨")
        else:
            print("⚠️  기본 인사이트 또는 폴백 사용됨")
        
        # 답변 일부 출력
        print(f"📄 답변 미리보기:\n{answer[:300]}...")
        
    except Exception as e:
        print(f"❌ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 실행 함수"""
    print("🚀 Context Engineering - 컨텍스트 인사이트 확장 테스트\n")
    
    asyncio.run(test_context_insight_generator())
    asyncio.run(test_chat_service_integration())

if __name__ == "__main__":
    main()