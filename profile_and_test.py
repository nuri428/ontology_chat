"""
실제 시스템 성능 프로파일링 및 품질 테스트
- 각 단계별 실행 시간 측정
- 실제 응답 품질 확인
- 병목 지점 식별
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, List
import sys
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceProfiler:
    """성능 프로파일러"""

    def __init__(self):
        self.timings: Dict[str, List[float]] = {}
        self.current_timings: Dict[str, float] = {}

    def start(self, label: str):
        """타이밍 시작"""
        self.current_timings[label] = time.time()

    def end(self, label: str) -> float:
        """타이밍 종료 및 기록"""
        if label not in self.current_timings:
            return 0.0

        elapsed = time.time() - self.current_timings[label]

        if label not in self.timings:
            self.timings[label] = []
        self.timings[label].append(elapsed)

        del self.current_timings[label]
        return elapsed

    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """타이밍 요약"""
        summary = {}
        for label, times in self.timings.items():
            summary[label] = {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "count": len(times)
            }
        return summary

    def print_summary(self):
        """타이밍 요약 출력"""
        print("\n" + "="*80)
        print("⏱️  성능 프로파일링 결과")
        print("="*80)

        summary = self.get_summary()
        for label, stats in sorted(summary.items(), key=lambda x: x[1]["avg"], reverse=True):
            print(f"\n📊 {label}")
            print(f"   평균: {stats['avg']:.3f}초")
            print(f"   최소: {stats['min']:.3f}초")
            print(f"   최대: {stats['max']:.3f}초")
            print(f"   횟수: {stats['count']}회")


async def test_simple_query(profiler: PerformanceProfiler):
    """단순 질의 테스트"""
    from api.services.chat_service import ChatService
    from api.services.response_formatter import ResponseFormatter

    print("\n" + "="*80)
    print("🔵 단순 질의 테스트: '삼성전자 뉴스'")
    print("="*80)

    chat_service = ChatService()

    query = "삼성전자 뉴스"

    # 전체 실행 시간
    profiler.start("simple_query_total")

    # 의도 분석
    profiler.start("simple_intent_analysis")
    intent_result = await chat_service.intent_analyzer.analyze_intent(query)
    intent_time = profiler.end("simple_intent_analysis")
    print(f"\n✓ 의도 분석: {intent_time:.3f}초")
    print(f"  - 의도: {intent_result.get('intent')}")
    print(f"  - 신뢰도: {intent_result.get('confidence', 0):.2f}")

    # 엔티티 추출
    profiler.start("simple_entity_extraction")
    entities = await chat_service.entity_extractor.extract_entities(query)
    entity_time = profiler.end("simple_entity_extraction")
    print(f"\n✓ 엔티티 추출: {entity_time:.3f}초")
    print(f"  - 엔티티: {entities}")

    # 데이터 수집
    profiler.start("simple_data_collection")

    # 각 데이터 소스별 시간 측정
    profiler.start("simple_news_search")
    news_task = chat_service.news_service.search_news(query, limit=10)

    profiler.start("simple_graph_search")
    graph_task = chat_service.graph_service.search_graph(query, limit=5)

    profiler.start("simple_vector_search")
    vector_task = chat_service.vector_service.search(query, k=5)

    # 병렬 실행
    news_results, graph_results, vector_results = await asyncio.gather(
        news_task, graph_task, vector_task, return_exceptions=True
    )

    news_time = profiler.end("simple_news_search")
    graph_time = profiler.end("simple_graph_search")
    vector_time = profiler.end("simple_vector_search")

    collection_time = profiler.end("simple_data_collection")

    print(f"\n✓ 데이터 수집 (병렬): {collection_time:.3f}초")
    print(f"  - 뉴스 검색: {news_time:.3f}초 ({len(news_results) if isinstance(news_results, list) else 0}건)")
    print(f"  - 그래프 검색: {graph_time:.3f}초 ({len(graph_results) if isinstance(graph_results, list) else 0}건)")
    print(f"  - 벡터 검색: {vector_time:.3f}초 ({len(vector_results) if isinstance(vector_results, list) else 0}건)")

    # 컨텍스트 구성
    profiler.start("simple_context_building")
    context = await chat_service.context_builder.build_context(
        query=query,
        intent=intent_result.get("intent", "general"),
        entities=entities,
        news_results=news_results if isinstance(news_results, list) else [],
        graph_results=graph_results if isinstance(graph_results, list) else [],
        vector_results=vector_results if isinstance(vector_results, list) else []
    )
    context_time = profiler.end("simple_context_building")
    print(f"\n✓ 컨텍스트 구성: {context_time:.3f}초")
    print(f"  - 컨텍스트 길이: {len(context.get('context_text', ''))} 문자")

    # 답변 생성
    profiler.start("simple_answer_generation")
    answer = chat_service.context_answer_generator.generate_context_based_answer(
        query=query,
        intent=intent_result.get("intent", "general"),
        search_results={"sources": news_results if isinstance(news_results, list) else []},
        entities=entities
    )
    answer_time = profiler.end("simple_answer_generation")
    print(f"\n✓ 답변 생성: {answer_time:.3f}초")
    print(f"  - 답변 길이: {len(answer)} 문자")

    total_time = profiler.end("simple_query_total")

    print(f"\n{'='*80}")
    print(f"⏱️  전체 실행 시간: {total_time:.3f}초")
    print(f"{'='*80}")

    # 실제 답변 출력
    print("\n" + "="*80)
    print("📄 생성된 답변:")
    print("="*80)
    print(answer[:1000])  # 처음 1000자만
    if len(answer) > 1000:
        print(f"\n... (총 {len(answer)}자, {len(answer)-1000}자 생략)")

    return {
        "total_time": total_time,
        "answer_length": len(answer),
        "data_sources": {
            "news": len(news_results) if isinstance(news_results, list) else 0,
            "graph": len(graph_results) if isinstance(graph_results, list) else 0,
            "vector": len(vector_results) if isinstance(vector_results, list) else 0
        }
    }


async def test_complex_query(profiler: PerformanceProfiler):
    """복잡한 질의 테스트 (LangGraph)"""
    from api.services.langgraph_report_service import LangGraphReportService

    print("\n" + "="*80)
    print("🔴 복잡한 질의 테스트: '삼성전자와 SK하이닉스 HBM 경쟁력 비교'")
    print("="*80)

    langgraph_service = LangGraphReportService()

    query = "삼성전자와 SK하이닉스 HBM 경쟁력 비교"

    # 전체 실행 시간
    profiler.start("complex_query_total")

    # LangGraph 실행 (내부 상세 타이밍은 로그에서 확인)
    print("\n⚙️  LangGraph 워크플로우 실행 중...")
    print("   (각 에이전트 실행 시간은 로그에서 확인)")

    try:
        profiler.start("langgraph_execution")
        result = await asyncio.wait_for(
            langgraph_service.generate_langgraph_report(
                query=query,
                domain=None,
                lookback_days=30,
                analysis_depth="standard"
            ),
            timeout=60.0  # 60초 타임아웃
        )
        langgraph_time = profiler.end("langgraph_execution")

        total_time = profiler.end("complex_query_total")

        print(f"\n{'='*80}")
        print(f"⏱️  전체 실행 시간: {total_time:.3f}초")
        print(f"   - LangGraph 실행: {langgraph_time:.3f}초")
        print(f"{'='*80}")

        # 결과 분석
        report = result.get("report", "")
        metadata = result.get("metadata", {})

        print(f"\n✓ 보고서 생성 완료")
        print(f"  - 보고서 길이: {len(report)} 문자")
        print(f"  - 메타데이터: {metadata}")

        # 실제 보고서 출력
        print("\n" + "="*80)
        print("📄 생성된 보고서:")
        print("="*80)
        print(report[:2000])  # 처음 2000자만
        if len(report) > 2000:
            print(f"\n... (총 {len(report)}자, {len(report)-2000}자 생략)")

        return {
            "total_time": total_time,
            "langgraph_time": langgraph_time,
            "report_length": len(report),
            "metadata": metadata
        }

    except asyncio.TimeoutError:
        profiler.end("langgraph_execution")
        profiler.end("complex_query_total")
        print("\n❌ 타임아웃: LangGraph 실행이 60초를 초과했습니다.")
        print("   → 성능 최적화가 필요합니다!")
        return {
            "total_time": 60.0,
            "timeout": True
        }
    except Exception as e:
        profiler.end("langgraph_execution")
        profiler.end("complex_query_total")
        print(f"\n❌ 오류 발생: {e}")
        logger.exception("복잡한 질의 테스트 오류")
        return {
            "error": str(e)
        }


async def main():
    """메인 실행"""
    profiler = PerformanceProfiler()

    print("\n" + "="*80)
    print("🚀 시스템 성능 프로파일링 및 품질 테스트 시작")
    print("="*80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # 1. 단순 질의 테스트
    try:
        results["simple"] = await test_simple_query(profiler)
    except Exception as e:
        logger.exception("단순 질의 테스트 오류")
        results["simple"] = {"error": str(e)}

    print("\n\n" + "="*80)
    print("⏸️  잠시 대기 (1초)")
    print("="*80)
    await asyncio.sleep(1)

    # 2. 복잡한 질의 테스트
    try:
        results["complex"] = await test_complex_query(profiler)
    except Exception as e:
        logger.exception("복잡한 질의 테스트 오류")
        results["complex"] = {"error": str(e)}

    # 3. 결과 요약
    print("\n\n" + "="*80)
    print("📊 최종 결과 요약")
    print("="*80)

    profiler.print_summary()

    # 병목 지점 분석
    print("\n" + "="*80)
    print("🔍 병목 지점 분석")
    print("="*80)

    if "simple" in results and "total_time" in results["simple"]:
        simple_time = results["simple"]["total_time"]
        print(f"\n✅ 단순 질의: {simple_time:.3f}초")
        if simple_time > 2.0:
            print("   ⚠️  목표(1.5초) 초과 - 최적화 필요")
        else:
            print("   ✓ 목표 달성")

    if "complex" in results:
        if results["complex"].get("timeout"):
            print(f"\n❌ 복잡한 질의: 60초 초과 (타임아웃)")
            print("   🚨 심각한 성능 문제 - LangGraph 워크플로우 최적화 필수")
        elif "total_time" in results["complex"]:
            complex_time = results["complex"]["total_time"]
            print(f"\n✅ 복잡한 질의: {complex_time:.3f}초")
            if complex_time > 10.0:
                print("   ⚠️  10초 초과 - 사용자 경험 저하 가능성")
            elif complex_time > 5.0:
                print("   ⚠️  5초 초과 - 추가 최적화 권장")
            else:
                print("   ✓ 허용 범위")

    # 품질 분석
    print("\n" + "="*80)
    print("✨ 품질 분석")
    print("="*80)

    if "simple" in results and "answer_length" in results["simple"]:
        length = results["simple"]["answer_length"]
        sources = results["simple"]["data_sources"]
        print(f"\n단순 질의:")
        print(f"  - 답변 길이: {length}자")
        print(f"  - 데이터 소스: 뉴스 {sources['news']}건, 그래프 {sources['graph']}건, 벡터 {sources['vector']}건")
        if length < 100:
            print("  ⚠️  답변이 너무 짧음")
        elif length > 2000:
            print("  ⚠️  답변이 너무 길 수 있음")
        else:
            print("  ✓ 적절한 길이")

    if "complex" in results and "report_length" in results["complex"]:
        length = results["complex"]["report_length"]
        print(f"\n복잡한 질의:")
        print(f"  - 보고서 길이: {length}자")
        if length < 500:
            print("  ⚠️  보고서가 너무 짧음")
        elif length > 5000:
            print("  ⚠️  보고서가 너무 길 수 있음")
        else:
            print("  ✓ 적절한 길이")

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"profile_results_{timestamp}.json"

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "results": results,
            "timings": profiler.get_summary()
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📁 상세 결과 저장: {result_file}")
    print("\n" + "="*80)
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
