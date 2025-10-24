"""
빠른 상용 서비스 준비도 체크
핵심 지표만 빠르게 평가
"""

import asyncio
import time
from api.services.chat_service import ChatService
from api.services.langgraph_report_service import LangGraphReportEngine
from api.services.query_router import QueryRouter
from api.services.response_formatter import ResponseFormatter


async def quick_evaluate():
    print("\n" + "=" * 80)
    print("💰 빠른 상용 서비스 준비도 평가")
    print("=" * 80)

    # 초기화
    print("\n🔧 초기화 중...")
    chat_service = ChatService()
    langgraph_engine = LangGraphReportEngine()
    router = QueryRouter(chat_service, ResponseFormatter(), langgraph_engine)
    print("✅ 초기화 완료\n")

    # 핵심 테스트 케이스 (대표 시나리오)
    test_cases = [
        # (질문, 예상 시간, 카테고리)
        ("삼성전자 뉴스", 2.0, "단순 조회"),
        ("2차전지 관련 종목", 2.0, "단순 조회"),
        ("SK하이닉스 최근 실적", 3.0, "정보 조회"),
        ("PER이 뭐야?", 2.0, "일반 QA"),
        ("삼성전자와 SK하이닉스 비교", 15.0, "심층 분석"),
    ]

    # 평가 지표
    speed_scores = []
    quality_scores = []
    errors = 0

    print("📊 테스트 실행")
    print("-" * 80)

    for i, (query, max_time, category) in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] {query} ({category})")

        start = time.time()
        try:
            result = await router.process_query(query)
            elapsed = time.time() - start

            # 속도 평가
            is_fast = elapsed <= max_time
            speed_score = 1.0 if is_fast else (max_time / elapsed)
            speed_scores.append(speed_score)

            # 품질 평가 (간단)
            answer = result.get("markdown", "")
            has_content = len(answer) >= 50
            has_structure = "##" in answer or len(answer.split("\n")) > 3
            quality_score = 1.0 if (has_content and has_structure) else 0.5
            quality_scores.append(quality_score)

            # 결과 출력
            speed_icon = "✅" if is_fast else "⚠️"
            quality_icon = "✅" if quality_score >= 0.8 else "⚠️"

            print(f"  {speed_icon} 속도: {elapsed:.1f}초 (최대: {max_time}초)")
            print(f"  {quality_icon} 품질: {len(answer)}자, 구조화: {has_structure}")

        except Exception as e:
            print(f"  ❌ 오류: {e}")
            errors += 1
            speed_scores.append(0.0)
            quality_scores.append(0.0)

    # 종합 평가
    print("\n\n" + "=" * 80)
    print("📊 종합 평가 결과")
    print("=" * 80)

    avg_speed = sum(speed_scores) / len(speed_scores) if speed_scores else 0
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    error_rate = errors / len(test_cases) if test_cases else 0
    stability = 1.0 - error_rate

    print(f"\n⚡ 응답 속도:  {avg_speed:.1%}")
    print(f"📝 답변 품질:  {avg_quality:.1%}")
    print(f"🛡️ 안정성:    {stability:.1%} (오류율: {error_rate:.1%})")

    # 가중치 적용 종합 점수
    final_score = (
        avg_speed * 0.3 +      # 속도 30%
        avg_quality * 0.4 +    # 품질 40%
        stability * 0.3        # 안정성 30%
    )

    print(f"\n{'=' * 80}")
    print(f"🎯 종합 점수: {final_score:.1%}")
    print("=" * 80)

    # 등급 및 권장사항
    if final_score >= 0.9:
        grade = "A급"
        color = "🟢"
        recommendation = "프리미엄 유료 서비스 가능 (월 9,900원 ~ 19,900원)"
        status = "✅ 상용화 준비 완료"
    elif final_score >= 0.8:
        grade = "B급"
        color = "🟡"
        recommendation = "표준 유료 서비스 가능 (월 4,900원 ~ 9,900원) 또는 애드센스 무료"
        status = "✅ 상용화 가능"
    elif final_score >= 0.7:
        grade = "C급"
        color = "🟠"
        recommendation = "애드센스 무료 서비스 권장 (광고 기반)"
        status = "⚠️ 개선 권장"
    else:
        grade = "D급"
        color = "🔴"
        recommendation = "베타 서비스 또는 개선 후 재평가 필요"
        status = "❌ 상용화 부적합"

    print(f"\n{color} 등급: {grade}")
    print(f"📋 권장사항: {recommendation}")
    print(f"🎯 상태: {status}")

    # 세부 분석
    print(f"\n📈 세부 분석:")

    if avg_speed < 0.8:
        print(f"  ⚠️ 응답 속도 개선 필요 ({avg_speed:.1%})")
        print(f"     - 캐싱 강화")
        print(f"     - 데이터베이스 쿼리 최적화")

    if avg_quality < 0.8:
        print(f"  ⚠️ 답변 품질 개선 필요 ({avg_quality:.1%})")
        print(f"     - 프롬프트 엔지니어링 강화")
        print(f"     - 컨텍스트 정보 확대")

    if stability < 0.95:
        print(f"  ⚠️ 안정성 개선 필요 ({stability:.1%})")
        print(f"     - 오류 처리 강화")
        print(f"     - 폴백 메커니즘 개선")

    if final_score >= 0.8:
        print(f"\n  ✅ 모든 핵심 지표 양호!")

    # 비즈니스 추정
    print(f"\n💰 비즈니스 추정 (참고용):")
    print(f"   - 유료 서비스 가격: 월 {4900 if final_score >= 0.8 else 0}원 ~ {19900 if final_score >= 0.9 else 9900}원")
    print(f"   - 애드센스 수익 (무료): DAU 1,000명 기준 월 약 30,000원 ~ 100,000원")
    print(f"   - 예상 전환율: {10 if final_score >= 0.9 else 5 if final_score >= 0.8 else 2}%")

    return {
        "final_score": final_score,
        "grade": grade,
        "speed": avg_speed,
        "quality": avg_quality,
        "stability": stability,
    }


if __name__ == "__main__":
    result = asyncio.run(quick_evaluate())

    print("\n\n" + "=" * 80)
    print("✅ 평가 완료!")
    print("=" * 80)
