from __future__ import annotations
from typing import Any, Dict
from api.logging import setup_logging
logger = setup_logging()
import anyio
import yfinance as yf
from api.config import settings

class StockMCP:
    """
    간단한 주가 어댑터
    - yfinance 기반 (무료, 비공식)
    - 필요시 증권사/유료 API 교체 가능 (동일 인터페이스 유지)
    """
    def __init__(self) -> None:
        self._api_key = settings.stock_api_key  # 현재는 미사용 (교체용 자리)
        logger.info("[Stock] adapter ready")

    async def get_price(self, symbol: str) -> Dict[str, Any]:
        """
        현재/최근 종가 근사치 반환
        """
        logger.debug(f"[Stock] get_price symbol={symbol}")
        def _fetch() -> Dict[str, Any]:
            t = yf.Ticker(symbol)
            info = t.fast_info if hasattr(t, "fast_info") else {}
            price = getattr(info, "last_price", None) or info.get("last_price") or None
            if price is None:
                # fallback: 최근 일봉
                hist = t.history(period="5d", interval="1d")
                price = float(hist["Close"].iloc[-1]) if not hist.empty else None
            return {"symbol": symbol, "price": price}
        return await anyio.to_thread.run_sync(_fetch)

    async def get_history(self, symbol: str, period: str = "1mo", interval: str = "1d") -> Dict[str, Any]:
        """
        과거 시세 조회
        period 예: "5d","1mo","3mo","6mo","1y","5y","max"
        interval 예: "1m","5m","15m","30m","60m","1d","1wk","1mo"
        """
        logger.debug(f"[Stock] get_history symbol={symbol} period={period} interval={interval}")
        def _fetch_hist() -> Dict[str, Any]:
            df = yf.Ticker(symbol).history(period=period, interval=interval)
            records = df.reset_index().to_dict(orient="records")
            return {"symbol": symbol, "period": period, "interval": interval, "rows": records}
        return await anyio.to_thread.run_sync(_fetch_hist)