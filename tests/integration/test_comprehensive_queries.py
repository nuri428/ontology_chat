#!/usr/bin/env python3
"""
포괄적 질의응답 시스템 종합 테스트
- 다양한 유형의 새로운 질문 테스트
- 응답 타당성 검증
- 프로세스 오버헤드 및 오작동 점검
- 롱텀 메모리 동작 확인
"""

import asyncio
import json
import time
from typing import Dict, Any, List
from datetime import datetime

# 테스트 질문 세트 (다양한 카테고리)
TEST_QUERIES = [
    {
        "id": 1,
        "query": "2차전지 관련 최근 3개월간 주요 기업들의 수주 현황은?",
        "category": "에너지/배터리",
        "expected_keywords": ["2차전지", "배터리", "수주", "LG", "삼성SDI"],
        "expected_sources": ["opensearch", "neo4j"],
    },
    {
        "id": 2,
        "query": "AI 반도체 시장에서 HBM 기술 경쟁력을 가진 기업은 어디인가?",
        "category": "반도체/기술",
        "expected_keywords": ["AI", "HBM", "반도체", "SK하이닉스", "삼성전자"],
        "expected_sources": ["opensearch", "neo4j"],
    },
    {
        "id": 3,
        "query": "최근 원자력 발전 관련 정책 변화가 주식 시장에 미친 영향은?",
        "category": "에너지/정책",
        "expected_keywords": ["원자력", "SMR", "정책", "한국수력원자력", "두산에너빌리티"],
        "expected_sources": ["opensearch", "neo4j"],
    },
    {
        "id": 4,
        "query": "전기차 배터리 화재 이슈로 영향받은 기업들의 대응 전략은?",
        "category": "자동차/리스크",
        "expected_keywords": ["전기차", "배터리", "화재", "안전", "대응"],
        "expected_sources": ["opensearch", "neo4j"],
    },
    {
        "id": 5,
        "query": "K-방산 수출 확대가 국내 방위산업체 실적에 미친 영향은?",
        "category": "방산/실적",
        "expected_keywords": ["방산", "수출", "한화", "LIG넥스원", "현대로템"],
        "expected_sources": ["opensearch", "neo4j"],
    },
    {
        "id": 6,
        "query": "반도체 장비 국산화 추진 현황과 관련 수혜 기업은?",
        "category": "반도체/공급망",
        "expected_keywords": ["반도체", "장비", "국산화", "원익IPS", "테스"],
        "expected_sources": ["opensearch", "neo4j"],
    },
    {
        "id": 7,
        "query": "최근 메모리 반도체 가격 변동이 주요 기업 실적에 미친 영향 분석",
        "category": "반도체/실적",
        "expected_keywords": ["메모리", "D램", "낸드", "가격", "실적"],
        "expected_sources": ["opensearch", "neo4j"],
    },
    {
        "id": 8,
        "query": "바이오 신약 개발 관련 임상 성공 사례와 투자 유망 기업은?",
        "category": "바이오/R&D",
        "expected_keywords": ["바이오", "신약", "임상", "셀트리온", "삼성바이오로직스"],
        "expected_sources": ["opensearch", "neo4j"],
    },
]


class ComprehensiveQueryTester:
    """포괄적 질의 테스트 클래스"""

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.results = []
        self.cache_stats = []

    async def test_single_query(
        self, test_case: Dict[str, Any], run_number: int = 1
    ) -> Dict[str, Any]:
        """단일 질문 테스트"""
        import aiohttp

        query_id = test_case["id"]
        query = test_case["query"]
        category = test_case["category"]

        print(f"\n{'='*80}")
        print(f"[테스트 {query_id}.{run_number}] {category}")
        print(f"질문: {query}")
        print(f"{'='*80}")

        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                # API 호출
                async with session.post(
                    f"{self.api_base_url}/chat",
                    json={"query": query},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return {
                            "query_id": query_id,
                            "run_number": run_number,
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "latency_ms": (time.time() - start_time) * 1000,
                        }

                    result = await response.json()

            latency_ms = (time.time() - start_time) * 1000

            # 응답 분석
            analysis = self._analyze_response(result, test_case, latency_ms, run_number)

            # 결과 출력
            self._print_result(analysis)

            return analysis

        except asyncio.TimeoutError:
            return {
                "query_id": query_id,
                "run_number": run_number,
                "success": False,
                "error": "Timeout (30s)",
                "latency_ms": 30000,
            }
        except Exception as e:
            return {
                "query_id": query_id,
                "run_number": run_number,
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000,
            }

    def _analyze_response(
        self,
        result: Dict[str, Any],
        test_case: Dict[str, Any],
        latency_ms: float,
        run_number: int,
    ) -> Dict[str, Any]:
        """응답 분석"""
        query_id = test_case["id"]
        query = test_case["query"]
        expected_keywords = test_case.get("expected_keywords", [])
        expected_sources = test_case.get("expected_sources", [])

        # 기본 정보 (answer 또는 markdown 필드 확인)
        answer = result.get("answer") or result.get("markdown", "")
        sources = result.get("sources", [])
        meta = result.get("meta", {})

        # 디버깅: meta 내용 확인
        if "graph_samples_shown" in meta:
            print(f"[DEBUG 테스트] graph_samples_shown found: {meta['graph_samples_shown']}")
        else:
            print(f"[DEBUG 테스트] graph_samples_shown NOT found, meta keys: {list(meta.keys())}")

        # graph_samples는 meta.graph_samples_shown에서 가져옴
        graph_samples_count = meta.get("graph_samples_shown", 0)
        graph_samples = [] if graph_samples_count == 0 else [{"count": graph_samples_count}]  # 호환성

        # 1. 키워드 매칭 검증
        keyword_matches = []
        for keyword in expected_keywords:
            if keyword.lower() in answer.lower():
                keyword_matches.append(keyword)

        keyword_match_rate = (
            len(keyword_matches) / len(expected_keywords) if expected_keywords else 0
        )

        # 2. 데이터 소스 검증
        sources_used = []
        if sources:
            sources_used.append("opensearch")
        if graph_samples:
            sources_used.append("neo4j")

        source_coverage = len(set(sources_used) & set(expected_sources)) / len(
            expected_sources
        ) if expected_sources else 0

        # 3. 응답 품질 평가
        quality_score = 0.0

        # 답변 길이 (너무 짧거나 길지 않은지)
        answer_length = len(answer)
        if 100 <= answer_length <= 5000:
            quality_score += 0.2
        elif answer_length > 50:
            quality_score += 0.1

        # 출처 개수 (적절한 출처가 있는지)
        if 1 <= len(sources) <= 10:
            quality_score += 0.2
        elif len(sources) > 0:
            quality_score += 0.1

        # 그래프 데이터 활용
        if len(graph_samples) > 0:
            quality_score += 0.2

        # 키워드 매칭
        quality_score += keyword_match_rate * 0.2

        # 소스 커버리지
        quality_score += source_coverage * 0.2

        # 4. 성능 평가
        performance_grade = "A" if latency_ms < 1500 else "B" if latency_ms < 3000 else "C"

        # 5. 캐시 정보 추출
        cache_hit = meta.get("cache_hit", False)
        cache_info = meta.get("cache_info", {})

        # 6. 오류 검증
        errors = []
        if not answer or answer == "":
            errors.append("빈 응답")
        if latency_ms > 5000:
            errors.append(f"높은 지연시간 ({latency_ms:.0f}ms)")
        if quality_score < 0.3:
            errors.append(f"낮은 품질 점수 ({quality_score:.2f})")

        return {
            "query_id": query_id,
            "run_number": run_number,
            "query": query,
            "category": test_case["category"],
            "success": True,
            "latency_ms": latency_ms,
            "performance_grade": performance_grade,
            "quality_score": quality_score,
            "keyword_match_rate": keyword_match_rate,
            "keywords_matched": keyword_matches,
            "source_coverage": source_coverage,
            "sources_used": sources_used,
            "answer_length": answer_length,
            "num_sources": len(sources),
            "num_graph_samples": len(graph_samples),
            "cache_hit": cache_hit,
            "cache_info": cache_info,
            "errors": errors,
            "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer,
            "raw_meta": meta,
        }

    def _print_result(self, analysis: Dict[str, Any]):
        """결과 출력"""
        print(f"\n[결과 분석]")
        print(f"  성공: {'✓' if analysis['success'] else '✗'}")
        print(f"  지연시간: {analysis['latency_ms']:.0f}ms ({analysis['performance_grade']})")
        print(f"  품질 점수: {analysis['quality_score']:.2f}/1.0")
        print(f"  키워드 매칭: {analysis['keyword_match_rate']:.1%} ({len(analysis['keywords_matched'])}/{len(analysis.get('expected_keywords', []))})")
        print(f"  소스 커버리지: {analysis['source_coverage']:.1%}")
        print(f"  사용된 소스: {', '.join(analysis['sources_used'])}")
        print(f"  출처 개수: {analysis['num_sources']}")
        print(f"  그래프 샘플: {analysis['num_graph_samples']}")
        print(f"  캐시 히트: {'✓' if analysis['cache_hit'] else '✗'}")

        if analysis.get("cache_info"):
            cache_info = analysis["cache_info"]
            print(f"    - 히트율: {cache_info.get('hit_rate', 0):.1%}")
            print(f"    - 캐시 크기: {cache_info.get('cache_size', 0)}")

        if analysis["errors"]:
            print(f"  ⚠️  경고: {', '.join(analysis['errors'])}")

        print(f"\n[답변 미리보기]")
        print(f"  {analysis['answer_preview']}")

    async def test_long_term_memory(self):
        """롱텀 메모리 테스트 - 같은 질문 반복"""
        print(f"\n{'='*80}")
        print(f"[롱텀 메모리 테스트]")
        print(f"{'='*80}")

        # 첫 번째 질문 (캐시 없음)
        test_case = TEST_QUERIES[0]
        result_1 = await self.test_single_query(test_case, run_number=1)

        # 잠시 대기
        await asyncio.sleep(1)

        # 같은 질문 재시도 (캐시 히트 예상)
        result_2 = await self.test_single_query(test_case, run_number=2)

        # 분석
        print(f"\n[롱텀 메모리 분석]")
        print(f"  1차 시도:")
        print(f"    - 지연시간: {result_1.get('latency_ms', 0):.0f}ms")
        print(f"    - 캐시 히트: {result_1.get('cache_hit', False)}")

        print(f"  2차 시도 (같은 질문):")
        print(f"    - 지연시간: {result_2.get('latency_ms', 0):.0f}ms")
        print(f"    - 캐시 히트: {result_2.get('cache_hit', False)}")

        if result_2.get("cache_hit"):
            speedup = result_1.get("latency_ms", 1) / result_2.get("latency_ms", 1)
            print(f"  ✓ 캐시 동작: 속도 {speedup:.1f}x 향상")
        else:
            print(f"  ✗ 캐시 미동작: 롱텀 메모리 이슈 가능")

        return {
            "first_run": result_1,
            "second_run": result_2,
            "cache_working": result_2.get("cache_hit", False),
        }

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print(f"\n{'#'*80}")
        print(f"# 포괄적 질의응답 시스템 종합 테스트")
        print(f"# 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"# 총 테스트: {len(TEST_QUERIES)}개")
        print(f"{'#'*80}")

        # 1. 개별 질문 테스트
        for test_case in TEST_QUERIES:
            result = await self.test_single_query(test_case)
            self.results.append(result)
            await asyncio.sleep(0.5)  # API 부하 방지

        # 2. 롱텀 메모리 테스트
        memory_test = await self.test_long_term_memory()

        # 3. 종합 분석
        self._print_summary(memory_test)

        # 4. JSON 보고서 저장
        self._save_report(memory_test)

    def _print_summary(self, memory_test: Dict[str, Any]):
        """종합 분석 출력"""
        print(f"\n{'='*80}")
        print(f"[종합 분석 리포트]")
        print(f"{'='*80}")

        # 성공률
        successful = [r for r in self.results if r.get("success", False)]
        success_rate = len(successful) / len(self.results) if self.results else 0

        # 평균 성능
        avg_latency = (
            sum(r.get("latency_ms", 0) for r in successful) / len(successful)
            if successful
            else 0
        )
        avg_quality = (
            sum(r.get("quality_score", 0) for r in successful) / len(successful)
            if successful
            else 0
        )

        # 성능 등급 분포
        grade_dist = {}
        for r in successful:
            grade = r.get("performance_grade", "F")
            grade_dist[grade] = grade_dist.get(grade, 0) + 1

        # 카테고리별 품질
        category_quality = {}
        for r in successful:
            cat = r.get("category", "Unknown")
            if cat not in category_quality:
                category_quality[cat] = []
            category_quality[cat].append(r.get("quality_score", 0))

        print(f"\n1. 전체 성능")
        print(f"  - 성공률: {success_rate:.1%} ({len(successful)}/{len(self.results)})")
        print(f"  - 평균 지연시간: {avg_latency:.0f}ms")
        print(f"  - 평균 품질 점수: {avg_quality:.2f}/1.0")
        print(f"  - 성능 등급 분포:")
        for grade in ["A", "B", "C"]:
            count = grade_dist.get(grade, 0)
            print(f"    • {grade}등급: {count}개 ({count/len(successful)*100:.0f}%)")

        print(f"\n2. 카테고리별 품질")
        for cat, scores in sorted(category_quality.items()):
            avg_score = sum(scores) / len(scores)
            print(f"  - {cat}: {avg_score:.2f}/1.0")

        print(f"\n3. 데이터 소스 활용")
        opensearch_used = len(
            [r for r in successful if "opensearch" in r.get("sources_used", [])]
        )
        neo4j_used = len(
            [r for r in successful if "neo4j" in r.get("sources_used", [])]
        )
        print(f"  - OpenSearch 활용: {opensearch_used}/{len(successful)}")
        print(f"  - Neo4j 활용: {neo4j_used}/{len(successful)}")

        print(f"\n4. 롱텀 메모리")
        print(f"  - 캐시 동작: {'✓' if memory_test.get('cache_working') else '✗'}")

        print(f"\n5. 문제점 및 개선사항")
        errors_found = [r for r in self.results if r.get("errors")]
        if errors_found:
            print(f"  ⚠️  {len(errors_found)}개 질문에서 문제 발견:")
            for r in errors_found[:3]:  # 상위 3개만 출력
                print(f"    - Q{r['query_id']}: {', '.join(r['errors'])}")
        else:
            print(f"  ✓ 심각한 문제 없음")

        # 권장사항
        print(f"\n6. 권장사항")
        if avg_latency > 2000:
            print(f"  • 평균 지연시간이 높음 → 캐싱 강화 또는 인덱스 최적화 필요")
        if avg_quality < 0.6:
            print(f"  • 품질 점수가 낮음 → 검색 전략 개선 필요")
        if not memory_test.get("cache_working"):
            print(f"  • 캐시가 동작하지 않음 → 캐시 설정 점검 필요")

        # 최종 평가
        print(f"\n{'='*80}")
        if success_rate >= 0.9 and avg_quality >= 0.7 and avg_latency < 2000:
            print(f"✓ 시스템 상태: 우수 (모든 지표 양호)")
        elif success_rate >= 0.8 and avg_quality >= 0.5:
            print(f"△ 시스템 상태: 양호 (일부 개선 필요)")
        else:
            print(f"✗ 시스템 상태: 개선 필요 (주요 지표 미달)")
        print(f"{'='*80}\n")

    def _save_report(self, memory_test: Dict[str, Any]):
        """JSON 보고서 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_report_{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(self.results),
                "successful": len([r for r in self.results if r.get("success")]),
                "avg_latency_ms": sum(
                    r.get("latency_ms", 0) for r in self.results if r.get("success")
                )
                / len([r for r in self.results if r.get("success")])
                if self.results
                else 0,
                "avg_quality": sum(
                    r.get("quality_score", 0)
                    for r in self.results
                    if r.get("success")
                )
                / len([r for r in self.results if r.get("success")])
                if self.results
                else 0,
            },
            "tests": self.results,
            "memory_test": memory_test,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"📄 상세 보고서 저장: {filename}")


async def main():
    """메인 함수"""
    tester = ComprehensiveQueryTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())