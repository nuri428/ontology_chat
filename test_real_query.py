#!/usr/bin/env python3
"""실제 쿼리 테스트 및 분석"""
import asyncio
import sys
import json
import time
sys.path.append('.')

async def test_real_query():
    """실제 쿼리로 테스트하고 결과 분석"""
    print("🔬 실제 쿼리 테스트 및 개선점 분석")
    print("=" * 80)

    try:
        from api.services.chat_service import ChatService

        service = ChatService()

        # 테스트 쿼리
        query = "최근 반도체 업계 이슈 관련 기사를 표시해줘"

        print(f"📝 질문: {query}")
        print("-" * 80)

        start_time = time.time()

        # 답변 생성
        result = await service.generate_answer(query)

        processing_time = (time.time() - start_time) * 1000

        # 결과 분석
        print("\n📊 결과 분석:")
        print("=" * 80)

        # 1. 기본 메트릭
        print("\n1️⃣ 기본 메트릭:")
        print(f"   - 처리 시간: {processing_time:.2f}ms")
        print(f"   - 소스 개수: {len(result.get('sources', []))}개")
        print(f"   - 그래프 데이터: {len(result.get('graph_samples', []))}개")

        # 2. 답변 구조 분석
        answer = result.get("answer", "")
        print(f"\n2️⃣ 답변 구조:")
        print(f"   - 전체 길이: {len(answer)}자")
        print(f"   - LLM 인사이트 포함: {'💡' in answer or '인사이트' in answer}")
        print(f"   - 섹션 구분: {'##' in answer}")
        print(f"   - 뉴스 섹션: {'📰' in answer}")
        print(f"   - 기업 정보: {'🏢' in answer}")

        # 3. 소스 품질 분석
        sources = result.get("sources", [])
        print(f"\n3️⃣ 소스 품질:")
        if sources:
            # 제목 분석
            titles = [s.get("title", "") for s in sources]
            semiconductor_keywords = ["반도체", "칩", "메모리", "파운드리", "TSMC", "삼성전자", "SK하이닉스"]
            relevant_count = sum(1 for title in titles if any(kw in title for kw in semiconductor_keywords))
            print(f"   - 관련성 있는 기사: {relevant_count}/{len(sources)}개 ({relevant_count/len(sources)*100:.1f}%)")

            # 날짜 분석
            dates_available = sum(1 for s in sources if s.get("date"))
            print(f"   - 날짜 정보 있음: {dates_available}/{len(sources)}개")

            # 미디어 다양성
            media_sources = set(s.get("media", "Unknown") for s in sources)
            print(f"   - 미디어 다양성: {len(media_sources)}개 소스")
            print(f"     {list(media_sources)[:5]}")

        # 4. 메타데이터 분석
        meta = result.get("meta", {})
        print(f"\n4️⃣ 시스템 메타데이터:")
        print(f"   - 오케스트레이터: {meta.get('orchestrator', 'N/A')}")

        latency = meta.get("latency_ms", {})
        if latency:
            print(f"   - OpenSearch: {latency.get('opensearch', 0):.2f}ms")
            print(f"   - Neo4j: {latency.get('neo4j', 0):.2f}ms")
            print(f"   - Stock API: {latency.get('stock', 0):.2f}ms")

        errors = meta.get("errors", {})
        error_count = sum(1 for v in errors.values() if v)
        print(f"   - 오류 발생: {error_count}개 서비스")

        # 5. 답변 내용 샘플
        print(f"\n5️⃣ 답변 미리보기 (처음 800자):")
        print("-" * 80)
        print(answer[:800] + "..." if len(answer) > 800 else answer)

        # 6. 개선점 분석
        print("\n" + "=" * 80)
        print("🔍 개선점 분석:")
        print("-" * 80)

        improvements = []

        # 처리 시간 체크
        if processing_time > 5000:
            improvements.append("⚠️ 처리 시간이 5초 이상 - 캐싱 또는 병렬 처리 개선 필요")
        elif processing_time > 3000:
            improvements.append("⚠️ 처리 시간 3-5초 - 최적화 여지 있음")
        else:
            improvements.append("✅ 처리 시간 양호 (3초 이내)")

        # 관련성 체크
        if sources and relevant_count / len(sources) < 0.5:
            improvements.append("⚠️ 검색 결과 관련성 낮음 - 키워드 추출 개선 필요")
        elif sources and relevant_count / len(sources) < 0.8:
            improvements.append("⚠️ 일부 비관련 결과 포함 - 필터링 강화 필요")
        else:
            improvements.append("✅ 검색 결과 관련성 높음")

        # LLM 인사이트 체크
        if not ('💡' in answer or '인사이트' in answer):
            improvements.append("⚠️ LLM 인사이트 미생성 - LLM 연결 상태 확인 필요")
        else:
            improvements.append("✅ LLM 인사이트 생성됨")

        # 소스 다양성 체크
        if sources and len(media_sources) < 2:
            improvements.append("⚠️ 미디어 소스 다양성 부족")
        else:
            improvements.append("✅ 다양한 미디어 소스")

        # 답변 구조 체크
        if len(answer) < 500:
            improvements.append("⚠️ 답변이 너무 짧음 - 컨텍스트 부족 가능성")
        elif len(answer) > 3000:
            improvements.append("⚠️ 답변이 너무 김 - 요약 필요")
        else:
            improvements.append("✅ 답변 길이 적절")

        # 오류 체크
        if error_count > 0:
            improvements.append(f"⚠️ {error_count}개 서비스 오류 발생 - 안정성 개선 필요")
        else:
            improvements.append("✅ 모든 서비스 정상 동작")

        # 개선점 출력
        for i, improvement in enumerate(improvements, 1):
            print(f"{i}. {improvement}")

        # 7. 권장 사항
        print("\n📌 권장 개선 사항:")
        print("-" * 80)

        recommendations = []

        if processing_time > 3000:
            recommendations.append("1. 응답 속도 개선:")
            recommendations.append("   - 더 공격적인 캐싱 전략 적용")
            recommendations.append("   - 병렬 처리 최적화")
            recommendations.append("   - LLM 타임아웃 단축 (10초 → 5초)")

        if sources and relevant_count / len(sources) < 0.8:
            recommendations.append("2. 검색 관련성 개선:")
            recommendations.append("   - 키워드 확장 로직 개선")
            recommendations.append("   - 의미적 유사도 임계값 조정")
            recommendations.append("   - 도메인 특화 키워드 매핑 강화")

        if not ('💡' in answer or '인사이트' in answer):
            recommendations.append("3. LLM 인사이트 생성:")
            recommendations.append("   - Ollama 연결 상태 확인")
            recommendations.append("   - 프롬프트 엔지니어링 개선")
            recommendations.append("   - 폴백 메커니즘 구현")

        if len(answer) < 500 or len(answer) > 3000:
            recommendations.append("4. 답변 품질 개선:")
            recommendations.append("   - 컨텍스트 프루닝 조정")
            recommendations.append("   - LLM 프롬프트에 길이 제한 명시")
            recommendations.append("   - 중요도 기반 정보 선별")

        for rec in recommendations:
            print(rec)

        # 결과를 파일로 저장
        with open("query_analysis_result.json", "w", encoding="utf-8") as f:
            json.dump({
                "query": query,
                "processing_time_ms": processing_time,
                "sources_count": len(sources),
                "answer_length": len(answer),
                "improvements": improvements,
                "recommendations": recommendations,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }, f, ensure_ascii=False, indent=2)

        print("\n💾 분석 결과가 query_analysis_result.json에 저장되었습니다.")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_query())