# src/ontolog_chat/main.py
from fastapi import Body, Depends, FastAPI, HTTPException
from api.logging import setup_logging
from api.config import settings
from api.routers import health
from api.services.chat_service import ChatService
from api.services.report_service import (
    ReportRequest,
    ReportResponse,
    ReportService,
)
from api.mcp import router as mcp_router  # ← 추가

logger = setup_logging()
app = FastAPI(title="ontolog_chat", version="0.1.0")

app.include_router(health.router)
app.include_router(mcp_router.router)  # ← 추가

chat_service = ChatService()
report_service = ReportService()


def get_report_service() -> ReportService:
    return report_service


@app.post("/chat")
async def chat(query: str = Body(..., embed=True)):
    result = await chat_service.generate_answer(query)
    return result


@app.post("/report", response_model=ReportResponse)
async def create_report(
    req: ReportRequest, service: ReportService = Depends(get_report_service)
):
    try:
        out = await service.generate_report(
            query=req.query,
            domain=req.domain,
            lookback_days=req.lookback_days,
            news_size=req.news_size,
            graph_limit=req.graph_limit,
            symbol=req.symbol,
        )
        # meta는 클라이언트에서 쓸 수 있도록 조금 포함해 줌
        meta = {
            "query": req.query,
            "domain": req.domain,
            "lookback_days": req.lookback_days,
            "news_size": req.news_size,
            "graph_limit": req.graph_limit,
            "symbol": req.symbol,
        }
        return ReportResponse(
            markdown=out["markdown"],
            metrics=out["metrics"],
            meta=meta,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"name": "ontolog_chat", "env": settings.app_env}
