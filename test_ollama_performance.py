"""Ollama LLM 성능 직접 테스트"""

import time
import asyncio
from langchain_ollama import OllamaLLM
from api.config import settings

async def test_ollama_direct():
    """Ollama 직접 호출 성능 테스트"""

    print("=" * 80)
    print("Ollama LLM 성능 테스트")
    print("=" * 80)
    print()

    # 설정 확인
    ollama_url = f"http://{settings.ollama_host}:11434"
    print(f"Ollama 설정:")
    print(f"  Host: {settings.ollama_host}")
    print(f"  Model: {settings.ollama_model}")
    print(f"  URL: {ollama_url}")
    print()

    # LLM 초기화
    llm = OllamaLLM(
        model=settings.ollama_model,
        base_url=ollama_url,
        temperature=0.1,
    )

    # 테스트 케이스들
    test_prompts = [
        ("짧은 프롬프트", "키워드 3개를 추출하세요: 삼성전자와 SK하이닉스 HBM 경쟁력 비교"),
        ("중간 프롬프트", "다음 질의를 분석하여 키워드를 추출하고 복잡도를 판단하세요. 질의: 삼성전자와 SK하이닉스의 HBM 메모리 반도체 경쟁력을 비교 분석해주세요."),
        ("긴 프롬프트", """다음 데이터를 분석하여 인사이트를 생성하세요:

컨텍스트 1: 삼성전자가 HBM3E 메모리 반도체 양산을 시작했다는 뉴스
컨텍스트 2: SK하이닉스가 HBM3 시장 점유율 50%를 달성했다는 보도
컨텍스트 3: AI 반도체 시장이 연평균 30% 성장하고 있다는 시장 분석
컨텍스트 4: 엔비디아가 차세대 GPU에 HBM3E를 탑재할 예정이라는 발표

위 정보를 종합하여 두 회사의 경쟁력을 비교 분석하세요."""),
    ]

    print("=" * 80)
    print("프롬프트 길이별 성능 테스트")
    print("=" * 80)
    print()

    for name, prompt in test_prompts:
        prompt_len = len(prompt)

        # 단일 호출 테스트
        start = time.time()
        try:
            response = await llm.ainvoke(prompt)
            elapsed = time.time() - start

            response_len = len(response)

            print(f"✓ {name}:")
            print(f"  프롬프트 길이: {prompt_len}자")
            print(f"  응답 시간: {elapsed:.3f}초")
            print(f"  응답 길이: {response_len}자")
            print(f"  초당 처리: {response_len/elapsed:.1f}자/초")

            if elapsed > 2.0:
                print(f"  ⚠️  2초 초과 - 느림!")
            elif elapsed > 1.0:
                print(f"  ⚠️  1초 초과")
            else:
                print(f"  ✅ 빠름")

            print()

        except Exception as e:
            print(f"✗ {name}: 실패 - {e}")
            print()

    # 연속 호출 테스트 (LangGraph와 유사)
    print("=" * 80)
    print("연속 호출 테스트 (LangGraph 시뮬레이션)")
    print("=" * 80)
    print()

    simple_prompt = "다음을 분석하세요: 삼성전자 실적"

    print(f"동일한 짧은 프롬프트를 10회 연속 호출...")
    print()

    total_start = time.time()
    times = []

    for i in range(10):
        start = time.time()
        response = await llm.ainvoke(simple_prompt)
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  호출 {i+1}: {elapsed:.3f}초")

    total_elapsed = time.time() - total_start
    avg_time = sum(times) / len(times)

    print()
    print(f"총 시간: {total_elapsed:.3f}초")
    print(f"평균 시간: {avg_time:.3f}초/호출")
    print(f"예상 LangGraph (10회): {avg_time * 10:.1f}초")

    if avg_time > 2.0:
        print(f"⚠️  평균 2초 초과 - 심각한 성능 문제!")
    elif avg_time > 1.0:
        print(f"⚠️  평균 1초 초과 - 최적화 필요")
    else:
        print(f"✅ 평균 1초 이내 - 양호")

    print()

async def test_network_latency():
    """네트워크 레이턴시 테스트"""
    print("=" * 80)
    print("네트워크 레이턴시 테스트")
    print("=" * 80)
    print()

    import httpx

    ollama_url = f"http://{settings.ollama_host}:11434"

    # 단순 ping (health check)
    try:
        start = time.time()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ollama_url}/api/tags")
        elapsed = (time.time() - start) * 1000

        print(f"✓ Ollama 서버 응답: {elapsed:.1f}ms")

        if elapsed > 100:
            print(f"  ⚠️  네트워크 레이턴시 높음 (>100ms)")
        elif elapsed > 50:
            print(f"  ⚠️  네트워크 레이턴시 보통 (>50ms)")
        else:
            print(f"  ✅ 네트워크 레이턴시 양호 (<50ms)")

    except Exception as e:
        print(f"✗ 연결 실패: {e}")

    print()

async def diagnose_slowness():
    """느린 원인 진단"""
    print("=" * 80)
    print("성능 저하 원인 진단")
    print("=" * 80)
    print()

    print("가능한 원인:")
    print()

    print("1. GPU 미사용 또는 설정 오류")
    print("   - Ollama가 실제로 GPU를 사용하는지 확인 필요")
    print("   - nvidia-smi로 GPU 사용률 확인")
    print()

    print("2. 모델 크기")
    print(f"   - 현재 모델: {settings.ollama_model}")
    print("   - llama3.1:8b는 8B 파라미터 → GPU에서도 어느 정도 시간 소요")
    print()

    print("3. 컨텍스트 길이")
    print("   - 프롬프트가 길수록 처리 시간 증가")
    print("   - LangGraph는 많은 컨텍스트를 LLM에 전달")
    print()

    print("4. 동시성 문제")
    print("   - 여러 요청이 동시에 GPU를 사용하면 대기 발생")
    print()

    print("권장 조치:")
    print("  1. GPU 사용 확인: nvidia-smi로 Ollama 프로세스 확인")
    print("  2. 프롬프트 최적화: 불필요한 컨텍스트 제거")
    print("  3. 더 작은 모델 사용: llama3.1:8b → llama3:7b 또는 3b")
    print("  4. 배치 처리 구현: 여러 LLM 호출을 하나로 통합")
    print()

async def main():
    await test_network_latency()
    await test_ollama_direct()
    await diagnose_slowness()

if __name__ == "__main__":
    asyncio.run(main())
