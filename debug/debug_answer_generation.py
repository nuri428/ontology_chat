#!/usr/bin/env python3
"""답변 생성 로직 디버깅"""
import asyncio
import sys
sys.path.insert(0, '/app')

async def test_answer_generation():
    """답변 생성 전체 흐름 테스트"""
    from api.services.response_formatter import ResponseFormatter
    from api.services.chat_service import ChatService

    print("="*80)
    print("답변 생성 디버깅 시작")
    print("="*80)

    # 1. ResponseFormatter 직접 테스트
    print("\n[1] ResponseFormatter 테스트")
    formatter = ResponseFormatter()

    # 샘플 데이터
    sample_news = [
        {
            "id": "1",
            "title": "삼성전자, 신규 반도체 공장 착공",
            "url": "http://example.com/1",
            "date": "2025-09-30",
            "media": "테스트뉴스",
            "score": 0.9
        }
    ]

    sample_graph = [
        {
            "n": {"name": "삼성전자", "labels": ["Company"]},
            "r": {"type": "RELATED_TO"}
        }
    ]

    try:
        answer = formatter.format_comprehensive_answer(
            query="삼성전자 최근 뉴스",
            news_hits=sample_news,
            graph_rows=sample_graph,
            stock=None,
            insights="테스트 인사이트입니다.",
            search_meta={"search_strategy": "hybrid"}
        )

        print(f"  ✓ ResponseFormatter 정상 동작")
        print(f"  ✓ 답변 길이: {len(answer)} chars")
        print(f"\n  답변 샘플 (처음 200자):")
        print(f"  {answer[:200]}...")

    except Exception as e:
        print(f"  ✗ ResponseFormatter 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 2. ChatService._compose_answer 테스트
    print("\n[2] ChatService._compose_answer 테스트")
    try:
        service = ChatService()

        # _compose_answer 직접 호출
        answer2 = await service._compose_answer(
            query="삼성전자",
            news_hits=sample_news,
            graph_rows=sample_graph,
            stock=None,
            search_meta={"search_strategy": "test"}
        )

        print(f"  ✓ _compose_answer 정상 동작")
        print(f"  ✓ 답변 길이: {len(answer2)} chars")

        if len(answer2) == 0:
            print(f"  ⚠️  경고: 답변이 비어있음!")
        else:
            print(f"\n  답변 샘플:")
            print(f"  {answer2[:200]}...")

    except Exception as e:
        print(f"  ✗ _compose_answer 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 3. 전체 generate_answer 흐름 테스트
    print("\n[3] ChatService.generate_answer 통합 테스트")
    try:
        result = await service.generate_answer("삼성전자")

        answer3 = result.get("answer", "")
        sources = result.get("sources", [])

        print(f"  ✓ generate_answer 실행 완료")
        print(f"  - 답변 길이: {len(answer3)} chars")
        print(f"  - 출처 개수: {len(sources)}")
        print(f"  - 메타데이터: {result.get('meta', {}).keys()}")

        if len(answer3) == 0:
            print(f"\n  ⚠️  답변이 비어있습니다!")
            print(f"  - 출처가 있나요? {len(sources) > 0}")
            print(f"  - 에러 메시지: {result.get('meta', {}).get('error', 'None')}")
        else:
            print(f"\n  ✓ 답변 생성 성공!")

    except Exception as e:
        print(f"  ✗ generate_answer 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "="*80)
    print("디버깅 완료")
    print("="*80)
    return True

if __name__ == "__main__":
    result = asyncio.run(test_answer_generation())
    sys.exit(0 if result else 1)