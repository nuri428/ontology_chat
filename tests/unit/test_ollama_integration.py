#!/usr/bin/env python3
"""Ollama 통합 테스트"""
import asyncio
import sys
import time
sys.path.append('.')

async def test_ollama_adapter():
    """Ollama 어댑터 테스트"""
    print("🦙 Ollama LLM 어댑터 테스트")
    print("=" * 60)

    try:
        from langchain_ollama import OllamaLLM
        from api.config import settings

        # 설정 확인
        print(f"📋 Ollama 설정:")
        print(f"   모델: {settings.ollama_model}")
        print(f"   서버: {settings.get_ollama_base_url()}")

        # langchain_ollama 직접 사용
        print(f"\n⚙️  Ollama LLM 초기화 중...")
        llm = OllamaLLM(
            model=settings.ollama_model,
            base_url=settings.get_ollama_base_url(),
            temperature=0.1,
            timeout=30
        )

        # 간단한 키워드 추출 테스트
        test_queries = [
            "SMR 관련 유망 종목 찾기",
            "반도체 산업 투자 전망"
        ]

        for i, query in enumerate(test_queries, 1):
            print(f"\n{i}️⃣  테스트 쿼리: '{query}'")
            print("-" * 50)

            # 직접 키워드 추출 테스트
            print("🔍 간단한 키워드 추출:")
            start_time = time.perf_counter()

            try:
                prompt = f"다음 질문의 핵심 키워드 5개를 추출하세요: '{query}'\n키워드:"
                response = await llm.ainvoke(prompt)
                elapsed = (time.perf_counter() - start_time) * 1000

                print(f"   ⏱️  실행 시간: {elapsed:.1f}ms")
                print(f"   📝 응답: {response.strip()}")

            except Exception as e:
                print(f"   ❌ 키워드 추출 실패: {e}")

    except ImportError as e:
        print(f"❌ 의존성 누락: {e}")
        print("💡 langchain-ollama를 설치하세요:")
        print("   pip install langchain-ollama")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def test_chat_service_integration():
    """ChatService와의 통합 테스트"""
    print(f"\n" + "=" * 60)
    print("🔗 ChatService 통합 테스트")
    print("=" * 60)

    try:
        from api.services.chat_service import ChatService

        service = ChatService()

        # Ollama LLM이 초기화되었는지 확인
        if service.ollama_llm:
            print("✅ ChatService에 Ollama LLM이 성공적으로 통합됨")
            print(f"📋 모델 정보: {service.ollama_llm.model} @ {service.ollama_llm.base_url}")

            # 키워드 추출 테스트
            test_query = "SMR 원자력 에너지 투자"
            print(f"\n🔍 통합 키워드 추출 테스트: '{test_query}'")

            start_time = time.perf_counter()
            keywords = await service._get_context_keywords(test_query)
            elapsed = (time.perf_counter() - start_time) * 1000

            print(f"   ⏱️  실행 시간: {elapsed:.1f}ms")
            print(f"   📝 추출된 키워드: '{keywords}'")

        else:
            print("⚠️  ChatService에서 Ollama LLM 초기화 실패")

        # 정리
        await service.neo.close()

    except Exception as e:
        print(f"❌ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def test_model_availability():
    """모델 사용 가능성 테스트"""
    print(f"\n" + "=" * 60)
    print("📡 모델 사용 가능성 테스트")
    print("=" * 60)

    from api.config import settings

    # 기본 연결 테스트
    print(f"🔗 Ollama 서버 연결 테스트:")
    print(f"   서버: {settings.get_ollama_base_url()}")
    print(f"   모델: {settings.ollama_model}")

    try:
        import requests

        # Ollama 서버 상태 확인
        response = requests.get(f"{settings.get_ollama_base_url()}/api/tags", timeout=5)

        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"   ✅ 서버 연결 성공")
            print(f"   📦 설치된 모델 수: {len(models)}개")

            # 설치된 모델 목록
            if models:
                print(f"   📋 설치된 모델:")
                for model in models[:5]:  # 상위 5개만 표시
                    name = model.get("name", "unknown")
                    size = model.get("size", 0)
                    size_gb = size / (1024**3) if size else 0
                    print(f"      - {name} ({size_gb:.1f}GB)")

            # 설정된 모델이 있는지 확인
            model_names = [m.get("name", "") for m in models]
            if settings.ollama_model in model_names:
                print(f"   ✅ 설정된 모델 '{settings.ollama_model}' 사용 가능")
            else:
                print(f"   ⚠️  설정된 모델 '{settings.ollama_model}' 찾을 수 없음")
                print(f"   💡 다음 명령으로 모델을 설치하세요:")
                print(f"      ollama pull {settings.ollama_model}")
        else:
            print(f"   ❌ 서버 응답 오류: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print(f"   ❌ 서버 연결 실패 - Ollama가 실행 중인지 확인하세요")
    except Exception as e:
        print(f"   ❌ 연결 테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_model_availability())
    asyncio.run(test_ollama_adapter())
    asyncio.run(test_chat_service_integration())