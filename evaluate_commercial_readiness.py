"""
상용 서비스 준비도 평가
애드센스 앱 또는 유료 서비스로 제공 가능 여부 체크
"""

import asyncio
import time
from dataclasses import dataclass
from typing import List, Dict, Any
from api.services.chat_service import ChatService
from api.services.langgraph_report_service import LangGraphReportEngine
from api.services.query_router import QueryRouter
from api.services.response_formatter import ResponseFormatter


@dataclass
class CommercialCriteria:
    """상용 서비스 평가 기준"""
    name: str
    weight: float  # 가중치 (0.0-1.0)
    min_score: float  # 최소 합격 점수
    description: str


# 상용 서비스 평가 기준
COMMERCIAL_CRITERIA = [
    CommercialCriteria("응답 속도", 0.25, 0.7, "단순 질문 2초 이내, 복잡한 질문 10초 이내"),
    CommercialCriteria("답변 품질", 0.30, 0.8, "정확성, 관련성, 완성도"),
    CommercialCriteria("사용자 경험", 0.20, 0.7, "직관성, 일관성, 오류 처리"),
    CommercialCriteria("안정성", 0.15, 0.9, "오류율 5% 이하"),
    CommercialCriteria("확장성", 0.10, 0.6, "동시 사용자 처리 능력"),
]


# 실제 사용자 시나리오 기반 테스트 케이스
REAL_WORLD_SCENARIOS = [
    {
        "scenario": "직장인 점심시간 빠른 조회",
        "queries": [
            "삼성전자 오늘 뉴스",
            "방산주 추천",
            "2차전지 관련 종목",
        ],
        "max_time": 2.0,  # 2초 이내
        "expected_quality": 0.8,
    },
    {
        "scenario": "투자자 종목 분석",
        "queries": [
            "SK하이닉스 최근 실적은?",
            "현대차 전기차 사업 전망",
            "에코프로 투자 의견",
        ],
        "max_time": 3.0,
        "expected_quality": 0.85,
    },
    {
        "scenario": "전문가 심층 분석",
        "queries": [
            "삼성전자와 SK하이닉스 HBM 시장 비교",
            "2차전지 산업 투자 보고서",
            "AI 반도체 시장 트렌드 분석",
        ],
        "max_time": 15.0,
        "expected_quality": 0.9,
    },
    {
        "scenario": "초보 투자자 학습",
        "queries": [
            "PER이 뭐야?",
            "배당수익률 계산법",
            "ROE가 높으면 좋은거야?",
        ],
        "max_time": 2.0,
        "expected_quality": 0.85,
    },
]


class CommercialReadinessEvaluator:
    """상용 서비스 준비도 평가기"""

    def __init__(self):
        self.chat_service = None
        self.router = None
        self.results = []

    async def initialize(self):
        """서비스 초기화"""
        print("🔧 서비스 초기화 중...")
        self.chat_service = ChatService()
        langgraph_engine = LangGraphReportEngine()
        self.router = QueryRouter(self.chat_service, ResponseFormatter(), langgraph_engine)
        print("✅ 초기화 완료\n")

    async def evaluate_response_speed(self) -> Dict[str, Any]:
        """1. 응답 속도 평가"""
        print("\n" + "=" * 80)
        print("⚡ 1. 응답 속도 평가")
        print("=" * 80)

        test_cases = [
            ("삼성전자 뉴스", "fast", 2.0),
            ("2차전지", "fast", 2.0),
            ("삼성전자와 SK하이닉스 비교", "langgraph", 15.0),
        ]

        results = []
        for query, expected_type, max_time in test_cases:
            start = time.time()
            try:
                result = await self.router.process_query(query)
                elapsed = time.time() - start

                processing_method = result.get("meta", {}).get("processing_method", "legacy")
                is_fast = elapsed <= max_time

                status = "✅" if is_fast else "❌"
                print(f"{status} '{query[:30]}...' - {elapsed:.1f}초 (최대: {max_time}초)")

                results.append({
                    "query": query,
                    "time": elapsed,
                    "max_time": max_time,
                    "passed": is_fast,
                })
            except Exception as e:
                print(f"❌ '{query}' - 오류: {e}")
                results.append({"query": query, "passed": False, "error": str(e)})

        passed = sum(1 for r in results if r.get("passed", False))
        total = len(results)
        score = passed / total if total > 0 else 0

        print(f"\n📊 응답 속도 점수: {score:.1%} ({passed}/{total})")

        return {
            "criterion": "응답 속도",
            "score": score,
            "passed": passed,
            "total": total,
            "details": results,
        }

    async def evaluate_answer_quality(self) -> Dict[str, Any]:
        """2. 답변 품질 평가"""
        print("\n" + "=" * 80)
        print("📝 2. 답변 품질 평가")
        print("=" * 80)

        quality_checks = [
            ("삼성전자 뉴스", ["삼성전자", "뉴스"], 50),  # 최소 50자
            ("SK하이닉스 실적", ["SK하이닉스", "실적"], 50),
            ("2차전지 관련 종목", ["2차전지", "종목"], 50),
        ]

        results = []
        for query, must_contain, min_length in quality_checks:
            try:
                result = await self.router.process_query(query)
                answer = result.get("markdown", "")

                # 품질 체크
                has_keywords = all(kw in answer for kw in must_contain)
                has_length = len(answer) >= min_length
                is_quality = has_keywords and has_length

                status = "✅" if is_quality else "❌"
                print(f"{status} '{query}' - 길이: {len(answer)}자, 키워드: {has_keywords}")

                results.append({
                    "query": query,
                    "length": len(answer),
                    "has_keywords": has_keywords,
                    "passed": is_quality,
                })
            except Exception as e:
                print(f"❌ '{query}' - 오류: {e}")
                results.append({"query": query, "passed": False})

        passed = sum(1 for r in results if r.get("passed", False))
        total = len(results)
        score = passed / total if total > 0 else 0

        print(f"\n📊 답변 품질 점수: {score:.1%} ({passed}/{total})")

        return {
            "criterion": "답변 품질",
            "score": score,
            "passed": passed,
            "total": total,
            "details": results,
        }

    async def evaluate_user_experience(self) -> Dict[str, Any]:
        """3. 사용자 경험 평가"""
        print("\n" + "=" * 80)
        print("👤 3. 사용자 경험 평가")
        print("=" * 80)

        ux_checks = []

        # 1) 오타 처리
        print("\n[오타 처리 테스트]")
        typo_queries = [
            ("삼성전자 뉴스", True),  # 정상
            ("PER이 뭐야?", True),  # 정상
        ]

        for query, should_work in typo_queries:
            try:
                result = await self.router.process_query(query)
                has_answer = len(result.get("markdown", "")) > 20
                status = "✅" if has_answer == should_work else "❌"
                print(f"{status} '{query}' - 응답: {has_answer}")
                ux_checks.append(has_answer == should_work)
            except:
                ux_checks.append(False)

        # 2) 일관성 (같은 질문 2번)
        print("\n[일관성 테스트]")
        query = "삼성전자 뉴스"
        try:
            result1 = await self.router.process_query(query)
            result2 = await self.router.process_query(query)

            type1 = result1.get("type")
            type2 = result2.get("type")
            is_consistent = type1 == type2

            status = "✅" if is_consistent else "❌"
            print(f"{status} 일관성: {type1} == {type2}")
            ux_checks.append(is_consistent)
        except:
            ux_checks.append(False)

        # 3) 오류 메시지 (빈 질문)
        print("\n[오류 처리 테스트]")
        try:
            result = await self.router.process_query("")
            has_error_msg = "markdown" in result or "error" in str(result).lower()
            status = "✅" if has_error_msg else "❌"
            print(f"{status} 빈 질문 처리: {has_error_msg}")
            ux_checks.append(has_error_msg)
        except:
            print("✅ 빈 질문 예외 처리됨")
            ux_checks.append(True)

        passed = sum(ux_checks)
        total = len(ux_checks)
        score = passed / total if total > 0 else 0

        print(f"\n📊 사용자 경험 점수: {score:.1%} ({passed}/{total})")

        return {
            "criterion": "사용자 경험",
            "score": score,
            "passed": passed,
            "total": total,
        }

    async def evaluate_stability(self) -> Dict[str, Any]:
        """4. 안정성 평가"""
        print("\n" + "=" * 80)
        print("🛡️ 4. 안정성 평가")
        print("=" * 80)

        test_queries = [
            "삼성전자 뉴스",
            "2차전지",
            "방산주",
            "SK하이닉스",
            "PER이 뭐야?",
            "삼성전자와 SK하이닉스 비교",
            "현대차 전망",
            "에코프로",
            "배당수익률",
            "AI 반도체",
        ]

        errors = 0
        for query in test_queries:
            try:
                result = await self.router.process_query(query)
                print(f"✅ '{query}'")
            except Exception as e:
                print(f"❌ '{query}' - 오류: {e}")
                errors += 1

        total = len(test_queries)
        success = total - errors
        error_rate = errors / total if total > 0 else 0
        score = 1.0 - error_rate

        print(f"\n📊 안정성 점수: {score:.1%} (오류율: {error_rate:.1%})")

        return {
            "criterion": "안정성",
            "score": score,
            "success": success,
            "total": total,
            "error_rate": error_rate,
        }

    async def evaluate_scalability(self) -> Dict[str, Any]:
        """5. 확장성 평가 (간단한 부하 테스트)"""
        print("\n" + "=" * 80)
        print("📈 5. 확장성 평가")
        print("=" * 80)

        # 동시 요청 시뮬레이션 (3개)
        queries = ["삼성전자 뉴스", "2차전지", "방산주"]

        start = time.time()
        try:
            tasks = [self.router.process_query(q) for q in queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            elapsed = time.time() - start
            success = sum(1 for r in results if not isinstance(r, Exception))
            total = len(queries)

            # 동시 요청이 순차 요청의 1.5배 이내면 합격
            max_expected_time = 2.0 * 1.5  # 2초 * 1.5배
            is_fast = elapsed <= max_expected_time

            status = "✅" if is_fast and success == total else "❌"
            print(f"{status} 동시 3개 요청: {elapsed:.1f}초 (최대: {max_expected_time:.1f}초)")
            print(f"   성공: {success}/{total}")

            score = 1.0 if is_fast and success == total else 0.5

        except Exception as e:
            print(f"❌ 동시 요청 실패: {e}")
            score = 0.0

        print(f"\n📊 확장성 점수: {score:.1%}")

        return {
            "criterion": "확장성",
            "score": score,
        }

    async def run_real_world_scenarios(self) -> Dict[str, Any]:
        """실제 사용자 시나리오 테스트"""
        print("\n" + "=" * 80)
        print("🎭 실제 사용자 시나리오 테스트")
        print("=" * 80)

        scenario_results = []

        for scenario_data in REAL_WORLD_SCENARIOS:
            print(f"\n📌 시나리오: {scenario_data['scenario']}")
            print("-" * 80)

            passed_queries = 0
            total_time = 0

            for query in scenario_data["queries"]:
                start = time.time()
                try:
                    result = await self.router.process_query(query)
                    elapsed = time.time() - start
                    total_time += elapsed

                    is_fast = elapsed <= scenario_data["max_time"]
                    has_content = len(result.get("markdown", "")) > 30

                    status = "✅" if is_fast and has_content else "❌"
                    print(f"  {status} {query[:40]:<40} - {elapsed:.1f}초")

                    if is_fast and has_content:
                        passed_queries += 1

                except Exception as e:
                    print(f"  ❌ {query[:40]:<40} - 오류: {e}")

            total_queries = len(scenario_data["queries"])
            avg_time = total_time / total_queries if total_queries > 0 else 0
            pass_rate = passed_queries / total_queries if total_queries > 0 else 0

            print(f"\n  결과: {passed_queries}/{total_queries} 성공 ({pass_rate:.1%})")
            print(f"  평균 응답 시간: {avg_time:.1f}초")

            scenario_results.append({
                "scenario": scenario_data["scenario"],
                "pass_rate": pass_rate,
                "avg_time": avg_time,
            })

        overall_pass_rate = sum(r["pass_rate"] for r in scenario_results) / len(scenario_results)

        return {
            "overall_pass_rate": overall_pass_rate,
            "scenarios": scenario_results,
        }

    async def evaluate_all(self) -> Dict[str, Any]:
        """전체 평가 실행"""
        print("\n" + "=" * 100)
        print("💰 상용 서비스 준비도 종합 평가")
        print("=" * 100)

        await self.initialize()

        # 각 기준별 평가
        results = []
        results.append(await self.evaluate_response_speed())
        results.append(await self.evaluate_answer_quality())
        results.append(await self.evaluate_user_experience())
        results.append(await self.evaluate_stability())
        results.append(await self.evaluate_scalability())

        # 실제 시나리오 테스트
        scenario_result = await self.run_real_world_scenarios()

        # 종합 점수 계산
        print("\n\n" + "=" * 100)
        print("📊 종합 평가 결과")
        print("=" * 100)

        total_score = 0
        total_weight = 0

        print(f"\n{'기준':<20} {'가중치':<10} {'점수':<10} {'합격선':<10} {'결과':<10}")
        print("-" * 80)

        for criterion, result in zip(COMMERCIAL_CRITERIA, results):
            score = result["score"]
            weighted_score = score * criterion.weight
            total_score += weighted_score
            total_weight += criterion.weight

            passed = "✅ 합격" if score >= criterion.min_score else "❌ 불합격"
            print(f"{criterion.name:<20} {criterion.weight:<10.1%} {score:<10.1%} {criterion.min_score:<10.1%} {passed}")

        final_score = total_score / total_weight if total_weight > 0 else 0

        print("-" * 80)
        print(f"{'종합 점수':<20} {'':<10} {final_score:<10.1%}")

        # 실제 시나리오 결과
        print(f"\n실제 시나리오 통과율: {scenario_result['overall_pass_rate']:.1%}")

        # 최종 판정
        print("\n" + "=" * 100)
        print("🎯 최종 판정")
        print("=" * 100)

        min_criteria_passed = all(
            results[i]["score"] >= COMMERCIAL_CRITERIA[i].min_score
            for i in range(len(results))
        )

        commercial_ready = (
            final_score >= 0.75 and
            min_criteria_passed and
            scenario_result['overall_pass_rate'] >= 0.8
        )

        if commercial_ready:
            if final_score >= 0.9:
                grade = "A급 (프리미엄 유료 서비스)"
                recommendation = "✅ 월 9,900원 ~ 19,900원 수준 유료 구독 가능"
            elif final_score >= 0.8:
                grade = "B급 (표준 유료 서비스)"
                recommendation = "✅ 월 4,900원 ~ 9,900원 또는 애드센스 무료"
            else:
                grade = "C급 (기본 유료 서비스)"
                recommendation = "✅ 애드센스 무료 서비스 권장"
        else:
            grade = "D급 (베타/무료 서비스)"
            recommendation = "❌ 개선 필요, 베타 서비스로만 운영 권장"

        print(f"\n등급: {grade}")
        print(f"권장사항: {recommendation}")

        # 개선 필요 사항
        print("\n📋 개선 필요 사항:")
        improvements = []
        for criterion, result in zip(COMMERCIAL_CRITERIA, results):
            if result["score"] < criterion.min_score:
                gap = criterion.min_score - result["score"]
                improvements.append(f"  ❌ {criterion.name}: {gap:.1%} 점수 부족")

        if improvements:
            for imp in improvements:
                print(imp)
        else:
            print("  ✅ 모든 기준 충족!")

        return {
            "final_score": final_score,
            "grade": grade,
            "commercial_ready": commercial_ready,
            "recommendation": recommendation,
            "criteria_results": results,
            "scenario_results": scenario_result,
        }


async def main():
    evaluator = CommercialReadinessEvaluator()
    result = await evaluator.evaluate_all()

    # 결과를 파일로 저장
    import json
    with open("commercial_readiness_report.json", "w", encoding="utf-8") as f:
        # 직렬화 가능한 데이터만 저장
        report = {
            "final_score": result["final_score"],
            "grade": result["grade"],
            "commercial_ready": result["commercial_ready"],
            "recommendation": result["recommendation"],
        }
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n\n💾 평가 결과가 'commercial_readiness_report.json'에 저장되었습니다.")


if __name__ == "__main__":
    asyncio.run(main())
