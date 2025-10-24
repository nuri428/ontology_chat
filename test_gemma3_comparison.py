#!/usr/bin/env python3
"""
Gemma3 vs 기존 최적 모델 비교 테스트

비교 대상:
1. llama3.1:8b (현재 사용 중, 베이스라인)
2. qwen2:7b-instruct-q4_K_M (한국어 후보)
3. gemma3 (새로 다운로드, TBD)
"""

import asyncio
import time
import httpx
import json
from datetime import datetime


# 최종 후보 모델들
CANDIDATE_MODELS = [
    {"name": "llama3.1:8b", "status": "baseline", "note": "현재 사용 중"},
    {"name": "qwen2:7b-instruct-q4_K_M", "status": "candidate", "note": "한국어 후보"},
    {"name": "gemma3:4b", "status": "new", "note": "Google 경량 모델"},
    {"name": "gemma3:12b", "status": "new", "note": "Google 고성능 모델"},
]

# 실제 프로젝트 사용 케이스 테스트
TEST_CASES = [
    {
        "name": "단순 뉴스 조회",
        "prompt": """금융 애널리스트로서 답변하세요.

**질의**: 삼성전자 최근 뉴스

3-4문장으로 간단히 요약하세요.""",
        "expected_time": "3-5초",
        "weight": 0.2
    },
    {
        "name": "기업 분석",
        "prompt": """금융 애널리스트로서 답변하세요.

**질의**: 삼성전자 HBM 경쟁력

5-7문장으로 핵심 경쟁력을 분석하세요.""",
        "expected_time": "5-8초",
        "weight": 0.3
    },
    {
        "name": "비교 분석 (종합)",
        "prompt": """금융 애널리스트로서 다음 질의에 대한 투자 분석 보고서를 작성하세요.

**질의**: 삼성전자와 SK하이닉스의 HBM 경쟁력 비교
**데이터**:
- 삼성전자: HBM3E 16단 개발 중, 하이브리드 본딩 기술 도입 계획
- SK하이닉스: HBM3E 이미 양산 중, 엔비디아 주요 공급업체

다음 구조로 Markdown 보고서를 작성하세요 (800자 이내):

# Executive Summary
- 핵심 발견사항 3개 (bullet points)

# Market Analysis
- 시장 상황 (100-150자)

# Key Insights
- 기술 경쟁력 비교
- 시장 점유율 분석

# Investment Perspective
- 투자 관점 권장사항

바로 시작:""",
        "expected_time": "10-15초",
        "weight": 0.5
    }
]


async def test_single_model(model_name: str, test_case: dict, ollama_url: str = "http://192.168.0.11:11434") -> dict:
    """단일 모델 테스트"""

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": test_case["prompt"],
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 1000
                    }
                }
            )

            total_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")

                # 통계
                tokens_generated = data.get("eval_count", 0)
                generation_time = data.get("eval_duration", 0) / 1e9
                tokens_per_sec = tokens_generated / generation_time if generation_time > 0 else 0

                # 품질 평가
                quality = evaluate_quality(response_text, test_case["name"])

                return {
                    "success": True,
                    "total_time": total_time,
                    "response_text": response_text,
                    "response_length": len(response_text),
                    "tokens_generated": tokens_generated,
                    "generation_time": generation_time,
                    "tokens_per_sec": tokens_per_sec,
                    "quality_score": quality,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "total_time": total_time,
                    "error": f"HTTP {response.status_code}"
                }

    except Exception as e:
        total_time = time.time() - start_time
        return {
            "success": False,
            "total_time": total_time,
            "error": str(e)
        }


def evaluate_quality(response_text: str, test_type: str) -> dict:
    """응답 품질 평가"""

    scores = {}

    # 1. 길이 적절성
    length = len(response_text)
    if test_type == "단순 뉴스 조회":
        target_range = (150, 400)
    elif test_type == "기업 분석":
        target_range = (300, 600)
    else:  # 종합 분석
        target_range = (600, 1200)

    if target_range[0] <= length <= target_range[1]:
        scores["length"] = 1.0
    elif target_range[0] * 0.7 <= length <= target_range[1] * 1.3:
        scores["length"] = 0.7
    else:
        scores["length"] = 0.3

    # 2. 한국어 품질
    korean_chars = sum(1 for c in response_text if '가' <= c <= '힣')
    korean_ratio = korean_chars / length if length > 0 else 0

    if korean_ratio > 0.4:
        scores["korean"] = 1.0
    elif korean_ratio > 0.2:
        scores["korean"] = 0.6
    elif korean_ratio > 0.05:
        scores["korean"] = 0.3
    else:
        scores["korean"] = 0.0

    # 3. 구조화 (Markdown)
    has_headers = "#" in response_text
    has_bullets = ("•" in response_text or "-" in response_text or "*" in response_text)

    if test_type == "비교 분석 (종합)":
        if has_headers and has_bullets:
            scores["structure"] = 1.0
        elif has_headers or has_bullets:
            scores["structure"] = 0.5
        else:
            scores["structure"] = 0.2
    else:
        scores["structure"] = 1.0 if has_bullets else 0.5

    # 4. 금융 용어 (투자 분석 품질)
    finance_keywords = ["투자", "경쟁력", "시장", "성장", "수익", "리스크", "전망", "분석", "매출", "기업"]
    keyword_count = sum(1 for kw in finance_keywords if kw in response_text)
    scores["finance"] = min(keyword_count / 5.0, 1.0)

    # 5. 이상한 출력 감지 (qwen3의 <think> 같은 것)
    has_artifacts = any(tag in response_text for tag in ["<think>", "<|", "```thinking"])
    scores["clean"] = 0.0 if has_artifacts else 1.0

    # 종합 점수
    weights = {
        "length": 0.15,
        "korean": 0.35,
        "structure": 0.15,
        "finance": 0.20,
        "clean": 0.15
    }

    overall = sum(scores[k] * weights[k] for k in scores)
    scores["overall"] = overall

    return scores


async def compare_models():
    """모델 비교 테스트 실행"""

    print("=" * 80)
    print("🔥 Gemma3 vs 최적 후보 모델 비교 테스트")
    print("=" * 80)
    print()
    print(f"테스트 대상 모델: {len(CANDIDATE_MODELS)}개")
    for model in CANDIDATE_MODELS:
        print(f"  - {model['name']} [{model['status']}] {model['note']}")
    print()
    print(f"테스트 케이스: {len(TEST_CASES)}개")
    print()

    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "models": {}
    }

    for model_info in CANDIDATE_MODELS:
        model_name = model_info["name"]

        print(f"\n{'='*80}")
        print(f"📊 모델: {model_name}")
        print(f"{'='*80}")

        model_results = {
            "model_name": model_name,
            "status": model_info["status"],
            "tests": []
        }

        for test_case in TEST_CASES:
            print(f"\n  📝 테스트: {test_case['name']} (목표: {test_case['expected_time']})")

            test_result = await test_single_model(model_name, test_case)

            if test_result["success"]:
                model_results["tests"].append({
                    "test_name": test_case["name"],
                    "weight": test_case["weight"],
                    "speed": {
                        "total_time": test_result["total_time"],
                        "tokens_per_sec": test_result["tokens_per_sec"],
                        "tokens_generated": test_result["tokens_generated"]
                    },
                    "quality": test_result["quality_score"],
                    "response_preview": test_result["response_text"][:300]
                })

                print(f"    ✅ 성공")
                print(f"       시간: {test_result['total_time']:.2f}초")
                print(f"       속도: {test_result['tokens_per_sec']:.1f} t/s")
                print(f"       품질: {test_result['quality_score']['overall']:.2f}")
                print(f"       길이: {test_result['response_length']}자")
                print(f"       한국어: {test_result['quality_score']['korean']:.2f}")
                print(f"       깔끔함: {test_result['quality_score']['clean']:.2f}")

            else:
                model_results["tests"].append({
                    "test_name": test_case["name"],
                    "error": test_result["error"]
                })
                print(f"    ❌ 실패: {test_result['error']}")

            await asyncio.sleep(2)

        # 모델별 종합 점수 계산
        successful_tests = [t for t in model_results["tests"] if "error" not in t]
        if successful_tests:
            # 가중 평균
            weighted_quality = sum(
                t["quality"]["overall"] * t["weight"]
                for t in successful_tests
            ) / sum(t["weight"] for t in successful_tests)

            weighted_time = sum(
                t["speed"]["total_time"] * t["weight"]
                for t in successful_tests
            ) / sum(t["weight"] for t in successful_tests)

            avg_speed = sum(
                t["speed"]["tokens_per_sec"] for t in successful_tests
            ) / len(successful_tests)

            # 종합 점수 (품질 60%, 속도 40%)
            # 속도 점수: 빠를수록 높음 (기준: 15초 = 0점, 5초 = 100점)
            speed_score = max(0, min(100, (15 - weighted_time) * 10))
            quality_score = weighted_quality * 100

            final_score = quality_score * 0.6 + speed_score * 0.4

            model_results["summary"] = {
                "weighted_quality": weighted_quality,
                "weighted_time": weighted_time,
                "avg_tokens_per_sec": avg_speed,
                "speed_score": speed_score,
                "quality_score": quality_score,
                "final_score": final_score
            }

            print(f"\n  📈 종합 평가:")
            print(f"     품질 점수: {quality_score:.1f} (가중 평균: {weighted_quality:.2f})")
            print(f"     속도 점수: {speed_score:.1f} (가중 시간: {weighted_time:.2f}초)")
            print(f"     토큰 속도: {avg_speed:.1f} t/s")
            print(f"     🏆 최종 점수: {final_score:.1f}")

        results["models"][model_name] = model_results

    # 최종 순위 및 권장사항
    print(f"\n{'='*80}")
    print("🏆 최종 순위 및 권장사항")
    print(f"{'='*80}\n")

    ranked = []
    for model_name, data in results["models"].items():
        if "summary" in data:
            ranked.append({
                "name": model_name,
                "score": data["summary"]["final_score"],
                "quality": data["summary"]["weighted_quality"],
                "time": data["summary"]["weighted_time"],
                "speed": data["summary"]["avg_tokens_per_sec"],
                "status": data["status"]
            })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    print(f"{'순위':<4} {'모델명':<35} {'최종점수':<10} {'품질':<8} {'시간':<10} {'속도':<12} {'상태'}")
    print("-" * 100)

    for i, model in enumerate(ranked, 1):
        status_emoji = "🌟" if model["status"] == "baseline" else "🆕" if model["status"] == "new" else "🔸"
        print(f"{i:<4} {status_emoji} {model['name']:<33} "
              f"{model['score']:>6.1f} {' '*3} "
              f"{model['quality']:>4.2f} {' '*3} "
              f"{model['time']:>6.2f}초 {' '*2} "
              f"{model['speed']:>6.1f} t/s {' '*2} "
              f"{model['status']}")

    # 권장사항
    if ranked:
        best = ranked[0]
        baseline = next((m for m in ranked if m["status"] == "baseline"), None)

        print(f"\n✨ 권장 모델: {best['name']}")
        print(f"   최종 점수: {best['score']:.1f}")
        print(f"   품질: {best['quality']:.2f}")
        print(f"   속도: {best['time']:.2f}초")

        if baseline and best["name"] != baseline["name"]:
            quality_diff = (best["quality"] - baseline["quality"]) / baseline["quality"] * 100
            time_diff = (baseline["time"] - best["time"]) / baseline["time"] * 100

            print(f"\n📊 {baseline['name']} 대비:")
            print(f"   품질: {quality_diff:+.1f}%")
            print(f"   속도: {time_diff:+.1f}%")

            if quality_diff > 5 or time_diff > 10:
                print(f"\n✅ 권장: {best['name']}로 변경")
            else:
                print(f"\n⚠️ 개선 폭이 작아 현재 모델 유지 권장")
        else:
            print(f"\n✅ 현재 모델({baseline['name']})이 최적입니다!")

    # 결과 저장
    output_file = f"gemma3_comparison_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {output_file}")

    return results


if __name__ == "__main__":
    print("⏳ Gemma3 모델 다운로드 대기 중...")
    print("   다운로드 완료 후 테스트를 시작합니다.\n")

    results = asyncio.run(compare_models())
