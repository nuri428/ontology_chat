#!/usr/bin/env python3
"""LLM 기반 답변 생성 테스트"""
import asyncio
import sys
sys.path.append('.')

async def test_llm_answer_generation():
    """LLM 답변 생성 기능 테스트"""
    print("🔬 LLM 기반 답변 생성 테스트")
    print("=" * 70)

    try:
        from api.services.chat_service import ChatService
        import time

        service = ChatService()

        # 테스트 쿼리들
        test_queries = [
            "SMR 관련 유망 투자 종목은?",
            "반도체 시장 전망이 어떻게 되나요?",
            "최근 전기차 배터리 관련 이슈는?",
            "삼성전자 주가 전망은?"
        ]

        for query in test_queries:
            print(f"\n📝 질문: {query}")
            print("-" * 50)

            start_time = time.time()

            try:
                # 답변 생성
                result = await service.generate_answer(query)

                # 결과 확인
                answer = result.get("answer", "")
                sources_count = len(result.get("sources", []))
                processing_time = (time.time() - start_time) * 1000

                print(f"⏱️ 처리 시간: {processing_time:.2f}ms")
                print(f"📚 소스 개수: {sources_count}개")

                # LLM 인사이트가 포함되었는지 확인
                if "💡" in answer or "인사이트" in answer:
                    print("✅ LLM 인사이트 생성 성공")
                else:
                    print("⚠️ LLM 인사이트 미포함")

                # 답변 일부 출력 (처음 500자)
                print(f"\n답변 미리보기:")
                print("-" * 40)
                print(answer[:500] + "..." if len(answer) > 500 else answer)

            except Exception as e:
                print(f"❌ 오류 발생: {e}")

        # LLM 상태 확인
        print("\n" + "=" * 70)
        print("📊 LLM 상태 확인:")
        if service.ollama_llm:
            print("✅ Ollama LLM 활성화")
            print(f"   - 모델: {service.ollama_llm.model}")
            print(f"   - 온도: {service.ollama_llm.temperature}")
        else:
            print("❌ Ollama LLM 비활성화")

    except ImportError as e:
        print(f"❌ 모듈 임포트 실패: {e}")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_answer_generation())