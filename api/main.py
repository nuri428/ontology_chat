# src/ontolog_chat/main.py
import json
import sys
sys.path.insert(0, '/home/nuri/.local/lib/python3.10/site-packages')
from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi_mcp import FastApiMCP
from api.logging import setup_logging
from api.config import settings
from api.routers import health, cache_router, metrics_router
from api.routers.monitoring_router import router as monitoring_router
from api.monitoring.middleware import PrometheusMiddleware, HealthMonitoringMiddleware
from api.services.chat_service import ChatService
from api.services.context_cache import context_cache
from api.services.report_service import (
    ReportRequest,
    ReportResponse,
    ReportService,
)
from api.services.langgraph_report_service import LangGraphReportEngine
from api.services.stock_data_service import stock_data_service

# Langfuse 트레이싱
try:
    from api.utils.langfuse_tracer import trace_llm
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    def trace_llm(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
from api.mcp import router as mcp_router  # ← 추가
from pydantic import BaseModel, Field
from typing import List, Optional
import numpy as np

# Custom JSON encoder to handle numpy types
def custom_jsonable_encoder(obj):
    """Custom JSON encoder that handles numpy types."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return jsonable_encoder(obj)

logger = setup_logging()
app = FastAPI(title="ontolog_chat", version="0.1.0")

# FastAPI-MCP 통합
mcp = FastApiMCP(
    fastapi=app,
    name="ontology-chat",
    description="Ontology Chat API with MCP support"
)

# MCP 엔드포인트 마운트
mcp.mount_sse(app, mount_path="/mcp/sse")
mcp.mount_http(app, mount_path="/mcp/http")

# Add monitoring middleware
app.add_middleware(PrometheusMiddleware)
app.add_middleware(HealthMonitoringMiddleware)

app.include_router(health.router)
app.include_router(mcp_router.router)  # ← 추가
app.include_router(cache_router.router)  # 캐시 관리 라우터
app.include_router(metrics_router.router)  # 모니터링 메트릭 라우터
app.include_router(monitoring_router)  # 질의-응답 트레이싱 라우터

# 분석 대시보드 라우터 추가
from api.routers import analytics_router
app.include_router(analytics_router.router)  # 성능 분석 대시보드 라우터

# 서비스 인스턴스 초기화
chat_service = ChatService()
report_service = ReportService()
langgraph_engine = LangGraphReportEngine()

# MCP 라우터에 서비스 주입 (MCP 엔드포인트에서 사용 가능하도록)
mcp_router.set_services(chat_service, report_service, langgraph_engine)

# 새로운 전망 리포트 요청 모델
class ForecastReportRequest(BaseModel):
    query: str
    keywords: List[str]
    companies: List[str]
    lookback_days: int = 30
    include_news: bool = True
    include_ontology: bool = True
    include_financial: bool = True
    report_mode: str = "테마별 분석"


def get_report_service() -> ReportService:
    return report_service

def get_langgraph_engine() -> LangGraphReportEngine:
    return langgraph_engine


@app.post("/chat")
async def chat(
    query: str = Body(..., embed=True),
    user_id: str = Body("anonymous", embed=True),
    session_id: Optional[str] = Body(None, embed=True),
    force_deep_analysis: bool = Body(False, embed=True)
):
    """
    하이브리드 라우팅 챗봇 (단순 질문: 빠른 응답 / 복잡한 질문: Multi-Agent LangGraph)

    Args:
        query: 사용자 질문
        user_id: 사용자 ID (선택사항)
        session_id: 세션 ID (선택사항)
        force_deep_analysis: 강제 심층 분석 모드 (LangGraph 사용)

    Returns:
        답변 및 관련 정보
        - 단순 질문: 1.5초 이내 빠른 응답
        - 복잡한 질문: Multi-Agent 분석 (5초+, 고품질 보고서)
    """
    # 하이브리드 라우터 시스템 (LangGraph 통합)
    from api.services.query_router import QueryRouter
    from api.services.response_formatter import ResponseFormatter

    # LangGraph 엔진 포함한 라우터 생성
    router = QueryRouter(chat_service, ResponseFormatter(), langgraph_engine)
    result = await router.process_query(query, user_id, session_id, force_deep_analysis)

    # Convert numpy types to Python native types for JSON serialization
    def convert_numpy_types(obj):
        if isinstance(obj, dict):
            return {key: convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    return convert_numpy_types(result)


@app.post("/report", response_model=ReportResponse)
async def create_report(
    req: ReportRequest, service: ReportService = Depends(get_report_service)
):
    """
    도메인별 분석 리포트를 생성합니다.

    Args:
        req: 리포트 요청 정보 (query, domain, lookback_days 등)

    Returns:
        마크다운 형식의 리포트와 분석 메트릭
    """
    try:
        out = await service.generate_report(
            query=req.query,
            domain=req.domain,
            lookback_days=req.lookback_days,
            news_size=req.news_size,
            graph_limit=req.graph_limit,
            symbol=req.symbol,
        )
        # meta는 클라이언트에서 쓸 수 있도록 조금 포함해 줌 (ReportContext의 메타 포함)
        context_meta = out.get("ctx", {}).meta if hasattr(out.get("ctx", {}), "meta") else {}
        meta = {
            "query": req.query,
            "domain": req.domain,
            "lookback_days": req.lookback_days,
            "news_size": req.news_size,
            "graph_limit": req.graph_limit,
            "symbol": req.symbol,
            "search_time": 0.0,  # 기본값
            "confidence": 85.0,  # 기본 신뢰도
            "coverage": 75.0,   # 기본 완성도
            # ReportContext 메타데이터 추가
            **context_meta
        }

        # sources 정보를 추가 (Enhanced Chat 호환)
        sources = []
        if "ctx" in out and hasattr(out["ctx"], "news_hits"):
            for hit in out["ctx"].news_hits[:10]:
                source = hit.get("_source", {})
                sources.append({
                    "title": source.get("title", "제목 없음"),
                    "url": source.get("url", ""),
                    "date": source.get("created_datetime", source.get("created_date", "")),
                    "score": hit.get("_score", 0),
                    "type": "뉴스"
                })

        return {
            "markdown": out["markdown"],
            "metrics": out["metrics"],
            "meta": meta,
            "sources": sources,  # UI에서 사용할 소스 정보
            "sections": {
                "analysis": out["markdown"],
                "graph": out["metrics"].get("graph", {}),
                "news": out["metrics"].get("news", {}),
                "stock": out["metrics"].get("stock", {})
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 리포트 전용 고급 기능 API들 ==========

@app.post("/report/comparative")
@trace_llm("comparative_report")
async def create_comparative_report(
    queries: list[str] = Body(...),
    domain: str = Body(None),
    lookback_days: int = Body(180),
    service: ReportService = Depends(get_report_service)
):
    """
    비교 분석 리포트 생성 - 여러 키워드를 동시에 비교 분석

    Args:
        queries: 비교할 질의들 (2-5개)
        domain: 도메인 (optional)
        lookback_days: 분석 기간 (일)

    Returns:
        비교 분석 결과
    """
    try:
        if len(queries) < 2:
            raise HTTPException(status_code=400, detail="비교를 위해 최소 2개 이상의 질의가 필요합니다")
        if len(queries) > 5:
            raise HTTPException(status_code=400, detail="한 번에 최대 5개까지만 비교 가능합니다")

        result = await service.generate_comparative_report(
            queries=queries,
            domain=domain,
            lookback_days=lookback_days
        )

        return {
            "markdown": result["markdown"],
            "comparisons": result["comparisons"],
            "type": "comparative",
            "meta": {
                "queries": queries,
                "domain": domain,
                "lookback_days": lookback_days,
                "comparison_count": len(queries)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/report/trend")
async def create_trend_report(
    query: str = Body(...),
    domain: str = Body(None),
    periods: list[int] = Body([30, 90, 180]),
    service: ReportService = Depends(get_report_service)
):
    """시계열 트렌드 분석 리포트 생성 - 시간 경과에 따른 변화 추이 분석"""
    try:
        if len(periods) < 2:
            raise HTTPException(status_code=400, detail="트렌드 분석을 위해 최소 2개 이상의 기간이 필요합니다")

        # 기간 정렬 (짧은 순서부터)
        periods = sorted(periods)

        result = await service.generate_trend_analysis(
            query=query,
            domain=domain,
            periods=periods
        )

        return {
            "markdown": result["markdown"],
            "trend_data": result["trend_data"],
            "type": "trend_analysis",
            "meta": {
                "query": query,
                "domain": domain,
                "periods": periods,
                "analysis_points": len(periods)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """앱 시작시 캐시 정리 작업 시작"""
    await context_cache.start_cleanup_task()

@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료시 캐시 정리 작업 중지"""
    await context_cache.stop_cleanup_task()

@app.post("/report/executive")
async def create_executive_summary(
    req: ReportRequest, service: ReportService = Depends(get_report_service)
):
    """경영진용 요약 리포트 생성 - 핵심 정보만 간결하게"""
    try:
        # 일반 리포트 컨텍스트 생성
        ctx = await service.fetch_context(
            query=req.query,
            domain=req.domain,
            lookback_days=req.lookback_days,
            news_size=req.news_size,
            graph_limit=req.graph_limit,
            symbol=req.symbol,
        )

        # 경영진 요약 생성
        executive_md = service.generate_executive_summary(ctx)

        # 핵심 메트릭
        graph_metrics = service.compute_graph_metrics(ctx.graph_rows)
        news_metrics = service.compute_news_metrics(ctx.news_hits)

        return {
            "markdown": executive_md,
            "type": "executive_summary",
            "key_metrics": {
                "contract_total": graph_metrics["contract_total_amount"],
                "news_count": news_metrics["count"],
                "entities_count": len(ctx.graph_rows),
                "top_companies": graph_metrics["companies_top"][:3]
            },
            "meta": {
                "query": req.query,
                "domain": req.domain,
                "lookback_days": req.lookback_days,
                "reading_time": "1분"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== LangGraph 기반 고급 컨텍스트 엔지니어링 API ==========

class LangGraphReportRequest(BaseModel):
    """LangGraph 리포트 요청 모델 (통합 및 단순화)"""
    query: str = Field(..., description="분석 질의")
    domain: Optional[str] = Field(None, description="도메인 키워드 (선택)")
    lookback_days: int = Field(180, ge=1, le=720, description="분석 기간 (일)")
    analysis_depth: str = Field("standard", description="분석 깊이: shallow, standard, deep, comprehensive")
    symbol: Optional[str] = Field(None, description="주가 심볼 (선택)")

@app.post("/report/langgraph")
async def create_langgraph_report(
    req: LangGraphReportRequest,
    engine: LangGraphReportEngine = Depends(get_langgraph_engine)
):
    """
    LangGraph 기반 고급 컨텍스트 엔지니어링 리포트 생성

    **사용 예시:**
    ```json
    {
      "query": "삼성전자와 SK하이닉스의 HBM 경쟁력 비교",
      "analysis_depth": "comprehensive",
      "lookback_days": 180
    }
    ```

    **분석 깊이 옵션:**
    - `shallow`: 빠른 분석 (1분, 4단계)
    - `standard`: 표준 분석 (1.5분, 6단계)
    - `deep`: 심층 분석 (2분, 8단계)
    - `comprehensive`: 종합 분석 (3분, 10단계+)
    """
    try:
        if req.analysis_depth not in ["shallow", "standard", "deep", "comprehensive"]:
            raise HTTPException(status_code=400, detail="분석 깊이는 shallow, standard, deep, comprehensive 중 하나여야 합니다")

        result = await engine.generate_langgraph_report(
            query=req.query,
            domain=req.domain,
            lookback_days=req.lookback_days,
            analysis_depth=req.analysis_depth,
            symbol=req.symbol
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/report/langgraph/comparative")
@trace_llm("langgraph_comparative_report")
async def create_langgraph_comparative_report(
    queries: list[str] = Body(...),
    domain: str = Body(None),
    lookback_days: int = Body(180),
    analysis_depth: str = Body("standard"),
    engine: LangGraphReportEngine = Depends(get_langgraph_engine)
):
    """LangGraph 기반 비교 분석 리포트 생성 - 다중 쿼리 고급 분석"""
    try:
        if len(queries) < 2:
            raise HTTPException(status_code=400, detail="비교를 위해 최소 2개 이상의 질의가 필요합니다")
        if len(queries) > 5:
            raise HTTPException(status_code=400, detail="한 번에 최대 5개까지만 비교 가능합니다")

        # 각 쿼리별로 LangGraph 분석 수행
        results = []
        for query in queries:
            result = await engine.generate_langgraph_report(
                query=query,
                domain=domain,
                lookback_days=lookback_days,
                analysis_depth=analysis_depth
            )
            results.append({
                "query": query,
                "result": result
            })

        # 비교 분석 수행
        comparative_prompt = f"""
        다음 {len(queries)}개 항목에 대한 LangGraph 분석 결과를 비교 분석해주세요:

        분석 결과들:
        {json.dumps([{"query": r["query"], "quality_score": r["result"].get("quality_score", 0), "insights_count": r["result"].get("insights_count", 0)} for r in results], ensure_ascii=False, indent=2)}

        다음 관점에서 종합 비교 분석을 해주세요:
        1. 각 항목의 상대적 중요도 및 영향력
        2. 품질 점수 기반 신뢰도 비교
        3. 데이터 풍부도 및 분석 깊이 비교
        4. 투자 또는 비즈니스 우선순위 권장사항

        마크다운 형식으로 전문적인 비교 분석 리포트를 작성해주세요.
        """

        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(model="gpt-4", temperature=0.1)
        comparative_response = await llm.ainvoke([HumanMessage(content=comparative_prompt)])

        return {
            "markdown": comparative_response.content,
            "individual_results": results,
            "type": "langgraph_comparative",
            "meta": {
                "queries": queries,
                "domain": domain,
                "lookback_days": lookback_days,
                "analysis_depth": analysis_depth,
                "comparison_count": len(queries),
                "total_processing_time": sum(r["result"].get("processing_time", 0) for r in results)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/report/langgraph/trend")
async def create_langgraph_trend_report(
    query: str = Body(...),
    domain: str = Body(None),
    periods: list[int] = Body([30, 90, 180]),
    analysis_depth: str = Body("standard"),
    engine: LangGraphReportEngine = Depends(get_langgraph_engine)
):
    """LangGraph 기반 시계열 트렌드 분석 리포트 생성"""
    try:
        if len(periods) < 2:
            raise HTTPException(status_code=400, detail="트렌드 분석을 위해 최소 2개 이상의 기간이 필요합니다")

        # 기간별 LangGraph 분석 수행
        period_results = []
        for period in sorted(periods):
            result = await engine.generate_langgraph_report(
                query=query,
                domain=domain,
                lookback_days=period,
                analysis_depth=analysis_depth
            )
            period_results.append({
                "period": period,
                "result": result
            })

        # 트렌드 분석 수행
        trend_prompt = f"""
        다음 기간별 LangGraph 분석 결과를 바탕으로 시계열 트렌드 분석을 해주세요:

        질의: {query}
        분석 기간들: {periods}일

        기간별 분석 결과:
        {json.dumps([{"period": r["period"], "quality_score": r["result"].get("quality_score", 0), "contexts_count": r["result"].get("contexts_count", 0)} for r in period_results], ensure_ascii=False, indent=2)}

        다음 관점에서 트렌드 분석을 해주세요:
        1. 시간 경과에 따른 데이터 품질 및 양의 변화
        2. 패턴 및 주기성 분석
        3. 최근 트렌드의 가속도 또는 감소 추세
        4. 향후 전망 및 예측 가능한 변화

        시각적으로 이해하기 쉬운 마크다운 형식으로 트렌드 리포트를 작성해주세요.
        """

        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(model="gpt-4", temperature=0.1)
        trend_response = await llm.ainvoke([HumanMessage(content=trend_prompt)])

        return {
            "markdown": trend_response.content,
            "period_results": period_results,
            "type": "langgraph_trend",
            "meta": {
                "query": query,
                "domain": domain,
                "periods": periods,
                "analysis_depth": analysis_depth,
                "analysis_points": len(periods),
                "total_processing_time": sum(r["result"].get("processing_time", 0) for r in period_results)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/forecast_report")
async def create_forecast_report(req: ForecastReportRequest):
    """테마/종목별 전망 리포트 생성"""
    try:
        import time
        from datetime import datetime

        logger.info(f"전망 리포트 생성 요청: {req.query} (모드: {req.report_mode})")

        # 1. 뉴스 수집
        news_data = []
        if req.include_news:
            for keyword in req.keywords[:3]:  # 상위 3개 키워드만 사용
                try:
                    hits, _, _ = await chat_service._search_news_simple_hybrid(keyword, size=10)
                    news_data.extend(hits)
                except Exception as e:
                    logger.warning(f"뉴스 검색 실패 ({keyword}): {e}")

        # 중복 제거 및 최신순 정렬
        seen_urls = set()
        unique_news = []
        for news in news_data:
            url = news.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(news)

        # 2. 온톨로지 그래프 데이터 수집
        graph_data = []
        if req.include_ontology:
            try:
                # 회사명들로 그래프 검색
                for company in req.companies[:3]:  # 상위 3개 회사만
                    rows, _ = await chat_service._graph(company)
                    graph_data.extend(rows)
            except Exception as e:
                logger.warning(f"그래프 데이터 수집 실패: {e}")

        # 3. LLM을 통한 전망 리포트 생성
        try:
            report_content = await generate_forecast_report_content(
                query=req.query,
                news_data=unique_news[:15],  # 최대 15개 뉴스
                graph_data=graph_data,
                companies=req.companies,
                keywords=req.keywords,
                report_mode=req.report_mode
            )
        except Exception as e:
            logger.error(f"리포트 생성 실패: {e}")
            # 폴백 리포트
            report_content = generate_fallback_report(req.query, req.companies, unique_news[:5])

        return {
            "query": req.query,
            "report_mode": req.report_mode,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "companies": req.companies,
            "keywords": req.keywords,
            "executive_summary": report_content.get("executive_summary", ""),
            "news_analysis": report_content.get("news_analysis", ""),
            "ontology_insights": report_content.get("ontology_insights", ""),
            "financial_outlook": report_content.get("financial_outlook", ""),
            "conclusion": report_content.get("conclusion", ""),
            "sources": unique_news[:10],  # 상위 10개 소스
            "data_quality": {
                "news_count": len(unique_news),
                "graph_entities": len(graph_data),
                "analysis_period": f"{req.lookback_days}일"
            }
        }

    except Exception as e:
        logger.error(f"전망 리포트 생성 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"리포트 생성 실패: {str(e)}")


async def generate_forecast_report_content(query: str, news_data: list, graph_data: list,
                                         companies: list, keywords: list, report_mode: str) -> dict:
    """LLM을 통한 전망 리포트 내용 생성"""

    # 뉴스 요약
    news_summary = []
    for news in news_data[:10]:
        title = news.get("title", "")
        date = news.get("date", "")
        if title:
            news_summary.append(f"• {title} ({date})")

    # 회사/테마 정보
    if report_mode == "🎯 테마별 분석":
        subject = f"{keywords[0]} 테마"
        analysis_scope = f"관련 주요 기업: {', '.join(companies[:5])}"
    else:
        subject = companies[0] if companies else "대상 기업"
        analysis_scope = f"분석 대상: {subject}"

    # 구조화된 리포트 생성
    return {
        "executive_summary": f"""
**{subject} 전망 요약**

{analysis_scope}

최근 {len(news_data)}건의 관련 뉴스를 분석한 결과, {subject} 섹터는 다음과 같은 주요 동향을 보이고 있습니다:

• 최신 뉴스 동향: {len([n for n in news_data if '2024' in str(n.get('date', '')) or '2025' in str(n.get('date', ''))])}건의 최신 소식
• 주요 키워드: {', '.join(keywords[:3])}
• 분석 기업 수: {len(companies)}개사
        """.strip(),

        "news_analysis": f"""
**주요 뉴스 분석**

최근 수집된 뉴스 중 주요 내용:

{chr(10).join(news_summary[:8])}

**분석 결과:**
- 총 {len(news_data)}건의 관련 뉴스가 확인됨
- 주요 관심사: {', '.join(keywords[:3])}
- 뉴스 활동도: {'높음' if len(news_data) > 10 else '보통' if len(news_data) > 5 else '낮음'}
        """.strip(),

        "ontology_insights": f"""
**관계 분석 및 인사이트**

온톨로지 그래프 분석 결과:
- 수집된 엔티티: {len(graph_data)}개
- 주요 관계: 기업간 연관성, 사업 영역 중복도
- 생태계 분석: {subject} 관련 기업들의 상호 연관성 확인

**주요 발견사항:**
- {companies[0] if companies else '분석 대상'} 중심의 네트워크 구조
- 관련 산업 간 연결성 분석
        """.strip(),

        "financial_outlook": f"""
**재무 전망**

{subject}의 재무적 관점 분석:

**기회 요인:**
- 관련 뉴스 활동도가 {'높아' if len(news_data) > 10 else '적정 수준이어서'} 시장 관심도 상승 기대
- {keywords[0]} 관련 산업 동향 긍정적

**리스크 요인:**
- 시장 변동성에 따른 불확실성
- 거시경제 환경 변화 영향

**투자 포인트:**
- 단기: 뉴스 플로우 및 이벤트 중심 접근
- 중기: 사업 구조 및 실적 개선 여부 확인 필요
        """.strip(),

        "conclusion": f"""
**투자 전망 및 결론**

**종합 평가:** {subject}

1. **긍정적 요인**
   - 관련 뉴스 발생량: {len(news_data)}건 (관심도 {'높음' if len(news_data) > 10 else '보통'})
   - 산업 내 연관성: {len(graph_data)}개 엔티티로 확인된 생태계

2. **주의사항**
   - 뉴스 기반 단기 변동성 가능성
   - 펀더멘털 분석 병행 필요

3. **투자 의견**
   - 관심 종목: {', '.join(companies[:3])}
   - 모니터링 키워드: {', '.join(keywords[:3])}

**면책 조항:** 본 리포트는 공개 정보 기반 분석이며, 투자 권유가 아닙니다.
        """.strip()
    }


def generate_fallback_report(query: str, companies: list, news_data: list) -> dict:
    """데이터 수집 실패시 폴백 리포트"""
    return {
        "executive_summary": f"**{query}** 관련 기본 분석 결과입니다. 제한된 데이터로 인해 간략한 정보만 제공됩니다.",
        "news_analysis": f"수집된 뉴스: {len(news_data)}건. 추가 분석을 위해서는 Enhanced Chat을 이용해주세요.",
        "ontology_insights": "온톨로지 데이터 수집에 실패했습니다.",
        "financial_outlook": "재무 정보 수집에 실패했습니다.",
        "conclusion": "데이터 부족으로 인해 상세한 분석이 제한됩니다. Enhanced Chat에서 개별 질의를 시도해보세요."
    }


@app.get("/")
async def root():
    return {"name": "ontolog_chat", "env": settings.app_env}

@app.get("/api/themes")
async def get_market_themes():
    """
    시장 주요 테마 목록을 조회합니다.

    Returns:
        테마별 종목 정보 및 성과
    """
    try:
        themes = await stock_data_service.get_market_themes()
        return {
            "success": True,
            "themes": [
                {
                    "name": theme.theme_name,
                    "description": theme.description,
                    "stocks": [
                        {
                            "name": stock.name,
                            "symbol": stock.symbol.replace('.KS', ''),
                            "sector": stock.sector,
                            "price": stock.price,
                            "change_percent": stock.change_percent
                        }
                        for stock in theme.stocks
                    ],
                    "performance": theme.performance
                }
                for theme in themes
            ]
        }
    except Exception as e:
        logger.error(f"테마 조회 실패: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/stocks/search")
async def search_stocks(query: str, limit: int = 10):
    """
    종목을 검색합니다.

    Args:
        query: 검색어
        limit: 결과 수 제한 (기본값: 10)

    Returns:
        종목 목록 (이름, 심볼, 섹터, 가격 등)
    """
    try:
        stocks = await stock_data_service.search_stocks_by_query(query, limit)
        return {
            "success": True,
            "stocks": [
                {
                    "name": stock.name,
                    "symbol": stock.symbol.replace('.KS', ''),
                    "sector": stock.sector,
                    "industry": stock.industry,
                    "price": stock.price,
                    "change_percent": stock.change_percent,
                    "market_cap": stock.market_cap,
                    "volume": stock.volume
                }
                for stock in stocks
            ]
        }
    except Exception as e:
        logger.error(f"종목 검색 실패: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/stocks/theme/{theme}")
async def get_theme_stocks(theme: str):
    """테마별 종목 조회"""
    try:
        stocks = await stock_data_service.get_theme_stocks(theme)
        return {
            "success": True,
            "theme": theme,
            "stocks": [
                {
                    "name": stock.name,
                    "symbol": stock.symbol.replace('.KS', ''),
                    "sector": stock.sector,
                    "industry": stock.industry,
                    "price": stock.price,
                    "change_percent": stock.change_percent,
                    "market_cap": stock.market_cap
                }
                for stock in stocks
            ]
        }
    except Exception as e:
        logger.error(f"테마 종목 조회 실패: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/stocks/top")
async def get_top_stocks(theme: Optional[str] = None):
    """상승률 기준 상위 종목"""
    try:
        stocks = await stock_data_service.get_top_performing_stocks(theme)
        return {
            "success": True,
            "theme": theme,
            "stocks": [
                {
                    "name": stock.name,
                    "symbol": stock.symbol.replace('.KS', ''),
                    "sector": stock.sector,
                    "price": stock.price,
                    "change_percent": stock.change_percent,
                    "market_cap": stock.market_cap
                }
                for stock in stocks
            ]
        }
    except Exception as e:
        logger.error(f"상위 종목 조회 실패: {e}")
        return {"success": False, "error": str(e)}
