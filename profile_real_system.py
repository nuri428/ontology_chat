"""
실제 시스템 엔드포인트 기반 성능 프로파일링 및 품질 테스트
서버가 이미 실행 중이어야 함
"""

import asyncio
import time
import httpx
import json
from datetime import datetime
from typing import Dict, Any

class SystemProfiler:
    """시스템 프로파일러"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []

    async def test_query(self, query: str, force_deep: bool = False, timeout: float = 60.0):
        """단일 질의 테스트"""
        print(f"\n{'='*80}")
        print(f"{'🔴' if force_deep else '🔵'} 테스트: '{query}'")
        print(f"   강제 심층 분석: {force_deep}")
        print(f"{'='*80}")

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat",
                    json={
                        "query": query,
                        "user_id": "profiler",
                        "session_id": "profile_session",
                        "force_deep_analysis": force_deep
                    }
                )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                result = response.json()

                # 결과 분석
                markdown = result.get("markdown", "")
                meta = result.get("meta", {})

                processing_time = meta.get("processing_time_ms", 0)
                intent = meta.get("intent", "unknown")
                confidence = meta.get("confidence", 0)

                # 출력
                print(f"\n✅ 성공 ({elapsed:.3f}초)")
                print(f"\n📊 메타데이터:")
                print(f"   - 처리 시간: {processing_time:.1f}ms")
                print(f"   - 의도: {intent}")
                print(f"   - 신뢰도: {confidence:.2f}")
                print(f"   - 응답 길이: {len(markdown)}자")

                # 실제 답변 미리보기
                print(f"\n📄 생성된 응답 (처음 500자):")
                print("-" * 80)
                print(markdown[:500])
                if len(markdown) > 500:
                    print(f"... (총 {len(markdown)}자, {len(markdown)-500}자 생략)")

                # 성능 평가
                print(f"\n⏱️  성능 평가:")
                if elapsed < 2.0:
                    print(f"   ✅ 매우 빠름 ({elapsed:.3f}초)")
                elif elapsed < 5.0:
                    print(f"   ✅ 빠름 ({elapsed:.3f}초)")
                elif elapsed < 10.0:
                    print(f"   ⚠️  보통 ({elapsed:.3f}초)")
                else:
                    print(f"   ❌ 느림 ({elapsed:.3f}초) - 최적화 필요!")

                # 품질 평가
                print(f"\n✨ 품질 평가:")
                if len(markdown) < 100:
                    print(f"   ⚠️  답변이 너무 짧음 ({len(markdown)}자)")
                elif len(markdown) > 3000:
                    print(f"   ⚠️  답변이 너무 길 수 있음 ({len(markdown)}자)")
                else:
                    print(f"   ✅ 적절한 길이 ({len(markdown)}자)")

                if confidence < 0.5:
                    print(f"   ⚠️  낮은 신뢰도 ({confidence:.2f})")
                elif confidence < 0.8:
                    print(f"   ✅ 보통 신뢰도 ({confidence:.2f})")
                else:
                    print(f"   ✅ 높은 신뢰도 ({confidence:.2f})")

                return {
                    "success": True,
                    "query": query,
                    "force_deep": force_deep,
                    "elapsed": elapsed,
                    "processing_time_ms": processing_time,
                    "intent": intent,
                    "confidence": confidence,
                    "response_length": len(markdown),
                    "response_preview": markdown[:500],
                    "full_response": markdown
                }

            else:
                print(f"\n❌ HTTP 오류: {response.status_code}")
                print(f"   {response.text[:200]}")
                return {
                    "success": False,
                    "query": query,
                    "error": f"HTTP {response.status_code}",
                    "elapsed": elapsed
                }

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            print(f"\n❌ 타임아웃: {elapsed:.1f}초 초과")
            return {
                "success": False,
                "query": query,
                "error": "timeout",
                "elapsed": elapsed
            }
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ 오류: {e}")
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "elapsed": elapsed
            }

    async def run_tests(self):
        """테스트 실행"""
        print(f"\n{'='*80}")
        print("🚀 시스템 성능 프로파일링 시작")
        print(f"{'='*80}")
        print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"대상 서버: {self.base_url}")

        # 서버 연결 확인
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
            print("✅ 서버 연결 확인 완료")
        except Exception as e:
            print(f"❌ 서버 연결 실패: {e}")
            print("   → 서버를 먼저 시작하세요: uvicorn api.main:app")
            return

        # 테스트 케이스
        test_cases = [
            # 단순 질의들
            {"query": "삼성전자 뉴스", "force_deep": False},
            {"query": "현대차 주가", "force_deep": False},

            # 복잡한 질의들
            {"query": "삼성전자와 SK하이닉스 HBM 경쟁력 비교", "force_deep": False},
            {"query": "AI 반도체 시장 트렌드 분석", "force_deep": False},

            # 강제 심층 분석
            {"query": "삼성전자 최근 실적", "force_deep": True}
        ]

        # 테스트 실행
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n\n{'#'*80}")
            print(f"테스트 {i}/{len(test_cases)}")
            print(f"{'#'*80}")

            result = await self.test_query(**test_case)
            self.results.append(result)

            # 다음 테스트 전에 잠시 대기
            if i < len(test_cases):
                print(f"\n⏸️  다음 테스트 전 2초 대기...")
                await asyncio.sleep(2)

        # 최종 요약
        self._print_summary()

        # 결과 저장
        self._save_results()

    def _print_summary(self):
        """결과 요약 출력"""
        print(f"\n\n{'='*80}")
        print("📊 최종 요약")
        print(f"{'='*80}")

        successful = [r for r in self.results if r.get("success")]
        failed = [r for r in self.results if not r.get("success")]

        print(f"\n✅ 성공: {len(successful)}/{len(self.results)}")
        print(f"❌ 실패: {len(failed)}/{len(self.results)}")

        if successful:
            avg_time = sum(r["elapsed"] for r in successful) / len(successful)
            min_time = min(r["elapsed"] for r in successful)
            max_time = max(r["elapsed"] for r in successful)

            print(f"\n⏱️  응답 시간:")
            print(f"   - 평균: {avg_time:.3f}초")
            print(f"   - 최소: {min_time:.3f}초")
            print(f"   - 최대: {max_time:.3f}초")

            # 단순 vs 복잡 비교
            simple_queries = [r for r in successful if not r.get("force_deep") and r["elapsed"] < 5.0]
            complex_queries = [r for r in successful if r.get("force_deep") or r["elapsed"] >= 5.0]

            if simple_queries:
                avg_simple = sum(r["elapsed"] for r in simple_queries) / len(simple_queries)
                print(f"\n   📘 단순 질의 평균: {avg_simple:.3f}초 ({len(simple_queries)}건)")

            if complex_queries:
                avg_complex = sum(r["elapsed"] for r in complex_queries) / len(complex_queries)
                print(f"   📕 복잡한 질의 평균: {avg_complex:.3f}초 ({len(complex_queries)}건)")

            # 품질 지표
            avg_length = sum(r["response_length"] for r in successful) / len(successful)
            avg_confidence = sum(r.get("confidence", 0) for r in successful) / len(successful)

            print(f"\n✨ 품질 지표:")
            print(f"   - 평균 응답 길이: {avg_length:.0f}자")
            print(f"   - 평균 신뢰도: {avg_confidence:.2f}")

        if failed:
            print(f"\n❌ 실패한 테스트:")
            for r in failed:
                print(f"   - {r['query']}: {r.get('error', 'unknown error')}")

        # 병목 지점 분석
        print(f"\n🔍 병목 지점 분석:")
        if successful:
            slow_queries = [r for r in successful if r["elapsed"] > 10.0]
            if slow_queries:
                print(f"\n   ⚠️  10초 초과 질의 ({len(slow_queries)}건):")
                for r in slow_queries:
                    print(f"      - {r['query']}: {r['elapsed']:.3f}초")
                    print(f"        → 심층 분석: {r.get('force_deep', False)}")
            else:
                print(f"   ✅ 모든 질의가 10초 이내 처리됨")

            very_slow = [r for r in successful if r["elapsed"] > 30.0]
            if very_slow:
                print(f"\n   🚨 30초 초과 질의 ({len(very_slow)}건) - 심각한 성능 문제!")
                for r in very_slow:
                    print(f"      - {r['query']}: {r['elapsed']:.3f}초")

        # 상업적 가치 평가
        print(f"\n💰 상업적 가치 평가:")
        if successful:
            if avg_time < 3.0 and avg_confidence > 0.7:
                print(f"   ✅ A급: 빠른 응답 + 높은 품질 → 유료 서비스 가능")
            elif avg_time < 5.0 and avg_confidence > 0.6:
                print(f"   ✅ B급: 적절한 응답 + 보통 품질 → 프리미엄 기능 추가 필요")
            elif avg_time < 10.0:
                print(f"   ⚠️  C급: 느린 응답 → 최적화 필수")
            else:
                print(f"   ❌ D급: 매우 느림 → 상업화 불가, 대폭 개선 필요")

    def _save_results(self):
        """결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"profile_results_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": timestamp,
                "base_url": self.base_url,
                "results": self.results
            }, f, indent=2, ensure_ascii=False)

        print(f"\n📁 상세 결과 저장: {filename}")


async def main():
    """메인 실행"""
    profiler = SystemProfiler()
    await profiler.run_tests()

    print(f"\n{'='*80}")
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
