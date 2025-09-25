#!/usr/bin/env python3
"""
Quality 필드 수정사항 테스트
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.services.langgraph_report_service import LangGraphReportEngine, ReportQuality

async def test_quality_fix():
    """Quality 필드 수정사항 테스트"""
    print("🔧 Quality 필드 수정사항 테스트")
    print("="*40)

    try:
        engine = LangGraphReportEngine()
        print("✅ LangGraph 엔진 초기화 성공")

        # 1. 상태 초기화 테스트
        print("\n1. 상태 초기화 테스트")
        state = engine._initialize_state(
            query="테스트 쿼리",
            analysis_depth="standard"
        )

        # quality_level이 제대로 초기화되었는지 확인
        if "quality_level" in state:
            print(f"✅ quality_level 초기화됨: {state['quality_level']}")
            print(f"   타입: {type(state['quality_level'])}")
            print(f"   값: {state['quality_level'].value if hasattr(state['quality_level'], 'value') else state['quality_level']}")
        else:
            print("❌ quality_level 초기화 실패")

        # 2. 품질 검사 로직 테스트
        print("\n2. 품질 검사 로직 테스트")

        # 테스트용 상태 설정
        test_state = state.copy()
        test_state["final_report"] = "테스트 리포트"
        test_state["quality_score"] = 0.7
        test_state["quality_level"] = ReportQuality.GOOD
        test_state["retry_count"] = 0

        # _should_enhance_report 메서드 테스트
        result = engine._should_enhance_report(test_state)
        print(f"✅ _should_enhance_report 결과: {result}")

        # 3. quality_level 없는 경우 테스트
        print("\n3. quality_level 누락 시 안전성 테스트")

        broken_state = state.copy()
        if "quality_level" in broken_state:
            del broken_state["quality_level"]

        result = engine._should_enhance_report(broken_state)
        print(f"✅ 누락된 quality_level 처리: {result}")

        if "quality_level" in broken_state:
            print(f"   복원된 quality_level: {broken_state['quality_level']}")

        return True

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """메인 테스트"""
    print("🧪 Quality 필드 수정사항 테스트 시작")
    print("="*50)

    success = await test_quality_fix()

    if success:
        print("\n🎉 Quality 필드 수정사항 테스트 성공!")
    else:
        print("\n❌ Quality 필드 수정사항 테스트 실패")

if __name__ == "__main__":
    asyncio.run(main())