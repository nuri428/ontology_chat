#!/usr/bin/env python3
"""
설치된 Ollama 모델 성능 비교 테스트

목표:
1. 속도: 토큰 생성 속도 측정
2. 품질: 한국어 금융 분석 품질 평가
3. 최적 모델 선정
"""

import asyncio
import time
import httpx
import json
from datetime import datetime


# 테스트할 모델 목록 (크기와 성능 고려)
TEST_MODELS = [
    # 현재 사용 중
    {"name": "llama3.1:8b", "size": "4.9GB", "priority": "baseline"},

    # Qwen 시리즈 (한국어 강점)
    {"name": "qwen3:8b", "size": "5.2GB", "priority": "high"},
    {"name": "qwen3:8b-q8_0", "size": "8.9GB", "priority": "high"},
    {"name": "qwen2.5:14b", "size": "9.0GB", "priority": "medium"},
    {"name": "qwen2:7b-instruct-q4_K_M", "size": "4.7GB", "priority": "medium"},

    # 기타 강력한 모델
    {"name": "deepseek-r1:14b", "size": "9.0GB", "priority": "medium"},
    {"name": "mistral-nemo:latest", "size": "7.1GB", "priority": "low"},
]

# 테스트 프롬프트 (실제 사용 케이스)
TEST_PROMPTS = [
    {
        "name": "간단한 분석",
        "prompt": """금융 애널리스트로서 다음 질의에 답변하세요.

**질의**: 삼성전자 HBM 경쟁력

간단히 3-4 문장으로 핵심만 답변하세요.""",
        "expected_tokens": 150
    },
    {
        "name": "종합 분석",
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
        "expected_tokens": 600
    }
]


async def test_model_speed(model_name: str, prompt: str, ollama_url: str = "http://192.168.0.11:11434") -> dict:
    """모델 속도 테스트"""

    print(f"  [Testing] {model_name}...")

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 800  # 최대 토큰 수
                    }
                }
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")

                # 통계 추출
                eval_count = data.get("eval_count", 0)  # 생성된 토큰 수
                eval_duration = data.get("eval_duration", 0) / 1e9  # 나노초 → 초

                tokens_per_sec = eval_count / eval_duration if eval_duration > 0 else 0

                return {
                    "success": True,
                    "total_time": elapsed,
                    "response_text": response_text,
                    "response_length": len(response_text),
                    "tokens_generated": eval_count,
                    "generation_time": eval_duration,
                    "tokens_per_sec": tokens_per_sec,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}"
                }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "total_time": elapsed,
            "error": str(e)
        }


def evaluate_response_quality(response_text: str, prompt_type: str) -> dict:
    """응답 품질 평가 (간단한 휴리스틱)"""

    scores = {}

    # 1. 길이 적절성
    length = len(response_text)
    if prompt_type == "간단한 분석":
        # 150-400자 적절
        if 150 <= length <= 400:
            scores["length"] = 1.0
        elif 100 <= length <= 600:
            scores["length"] = 0.7
        else:
            scores["length"] = 0.3
    else:  # 종합 분석
        # 600-1200자 적절
        if 600 <= length <= 1200:
            scores["length"] = 1.0
        elif 400 <= length <= 1500:
            scores["length"] = 0.7
        else:
            scores["length"] = 0.3

    # 2. 한국어 품질 (간단한 체크)
    korean_chars = sum(1 for c in response_text if '가' <= c <= '힣')
    korean_ratio = korean_chars / len(response_text) if length > 0 else 0

    if korean_ratio > 0.3:  # 한국어 30% 이상
        scores["korean_quality"] = 1.0
    elif korean_ratio > 0.1:
        scores["korean_quality"] = 0.5
    else:
        scores["korean_quality"] = 0.0

    # 3. 구조화 (Markdown 사용 여부)
    has_headers = "#" in response_text
    has_bullets = ("•" in response_text or "-" in response_text or "*" in response_text)

    if has_headers and has_bullets:
        scores["structure"] = 1.0
    elif has_headers or has_bullets:
        scores["structure"] = 0.6
    else:
        scores["structure"] = 0.2

    # 4. 금융 용어 사용 (간단한 키워드 체크)
    finance_keywords = ["투자", "경쟁력", "시장", "성장", "수익", "리스크", "전망", "분석", "기업", "매출"]
    keyword_count = sum(1 for kw in finance_keywords if kw in response_text)
    scores["finance_terms"] = min(keyword_count / 5.0, 1.0)

    # 5. 종합 점수
    overall = sum(scores.values()) / len(scores)
    scores["overall"] = overall

    return scores


async def compare_models():
    """모든 모델 비교 테스트"""

    print("=" * 80)
    print("🚀 Ollama 모델 성능 비교 테스트")
    print("=" * 80)
    print()

    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "models": {}
    }

    for model_info in TEST_MODELS:
        model_name = model_info["name"]
        model_size = model_info["size"]
        priority = model_info["priority"]

        print(f"\n{'='*80}")
        print(f"📊 모델: {model_name} ({model_size}) [Priority: {priority}]")
        print(f"{'='*80}")

        model_results = {
            "model_name": model_name,
            "size": model_size,
            "priority": priority,
            "tests": []
        }

        for test_prompt in TEST_PROMPTS:
            prompt_name = test_prompt["name"]
            prompt_text = test_prompt["prompt"]

            print(f"\n  📝 테스트: {prompt_name}")

            # 속도 테스트
            speed_result = await test_model_speed(model_name, prompt_text)

            if speed_result["success"]:
                # 품질 평가
                quality_scores = evaluate_response_quality(
                    speed_result["response_text"],
                    prompt_name
                )

                test_result = {
                    "prompt_type": prompt_name,
                    "speed": {
                        "total_time": speed_result["total_time"],
                        "generation_time": speed_result["generation_time"],
                        "tokens_per_sec": speed_result["tokens_per_sec"],
                        "tokens_generated": speed_result["tokens_generated"]
                    },
                    "quality": quality_scores,
                    "response_preview": speed_result["response_text"][:300]
                }

                print(f"    ✅ 성공")
                print(f"       총 시간: {speed_result['total_time']:.2f}초")
                print(f"       토큰/초: {speed_result['tokens_per_sec']:.1f} tokens/sec")
                print(f"       품질 점수: {quality_scores['overall']:.2f}")
                print(f"       응답 길이: {speed_result['response_length']}자")

            else:
                test_result = {
                    "prompt_type": prompt_name,
                    "error": speed_result["error"]
                }
                print(f"    ❌ 실패: {speed_result['error']}")

            model_results["tests"].append(test_result)

            # 다음 테스트 전 잠시 대기
            await asyncio.sleep(2)

        # 모델별 평균 계산
        successful_tests = [t for t in model_results["tests"] if "error" not in t]
        if successful_tests:
            avg_speed = sum(t["speed"]["tokens_per_sec"] for t in successful_tests) / len(successful_tests)
            avg_quality = sum(t["quality"]["overall"] for t in successful_tests) / len(successful_tests)

            종합분석_test = next((t for t in successful_tests if t["prompt_type"] == "종합 분석"), None)
            종합분석_time = 종합분석_test["speed"]["total_time"] if 종합분석_test else 0

            model_results["summary"] = {
                "avg_tokens_per_sec": avg_speed,
                "avg_quality_score": avg_quality,
                "comprehensive_analysis_time": 종합분석_time,
                "score": avg_speed * 0.4 + avg_quality * 60  # 종합 점수 (속도 40%, 품질 60%)
            }

            print(f"\n  📈 요약:")
            print(f"     평균 속도: {avg_speed:.1f} tokens/sec")
            print(f"     평균 품질: {avg_quality:.2f}")
            print(f"     종합 분석 시간: {종합분석_time:.2f}초")
            print(f"     종합 점수: {model_results['summary']['score']:.1f}")

        results["models"][model_name] = model_results

    # 최종 결과 요약 및 순위
    print(f"\n{'='*80}")
    print("🏆 최종 결과 요약 및 권장사항")
    print(f"{'='*80}\n")

    # 순위 매기기
    ranked_models = []
    for model_name, model_data in results["models"].items():
        if "summary" in model_data:
            ranked_models.append({
                "name": model_name,
                "size": model_data["size"],
                "score": model_data["summary"]["score"],
                "speed": model_data["summary"]["avg_tokens_per_sec"],
                "quality": model_data["summary"]["avg_quality_score"],
                "time": model_data["summary"]["comprehensive_analysis_time"]
            })

    ranked_models.sort(key=lambda x: x["score"], reverse=True)

    print("순위 | 모델명 | 크기 | 속도 | 품질 | 종합분석 시간 | 종합점수")
    print("-" * 90)

    for i, model in enumerate(ranked_models, 1):
        print(f"{i:2d}. {model['name']:30s} | {model['size']:7s} | "
              f"{model['speed']:5.1f} t/s | {model['quality']:4.2f} | "
              f"{model['time']:6.2f}초 | {model['score']:6.1f}")

    # 권장사항
    if ranked_models:
        best_model = ranked_models[0]
        print(f"\n✨ 권장 모델: {best_model['name']}")
        print(f"   - 종합 점수: {best_model['score']:.1f}")
        print(f"   - 예상 개선: {best_model['time']:.1f}초 (현재 13.8초 대비)")

        # 현재 모델과 비교
        current_model = next((m for m in ranked_models if m["name"] == "llama3.1:8b"), None)
        if current_model and best_model["name"] != "llama3.1:8b":
            time_improvement = (current_model["time"] - best_model["time"]) / current_model["time"] * 100
            quality_improvement = (best_model["quality"] - current_model["quality"]) / current_model["quality"] * 100

            print(f"\n📊 llama3.1:8b 대비 개선율:")
            print(f"   - 속도: {time_improvement:+.1f}%")
            print(f"   - 품질: {quality_improvement:+.1f}%")

    # 결과 저장
    output_file = f"model_comparison_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {output_file}")

    return results


if __name__ == "__main__":
    print("🔍 Ollama 모델 성능 비교 테스트 시작\n")
    print("테스트 대상:")
    for model in TEST_MODELS:
        print(f"  - {model['name']} ({model['size']}) [Priority: {model['priority']}]")
    print()
    print("예상 소요 시간: 약 10-15분")
    print()

    results = asyncio.run(compare_models())
