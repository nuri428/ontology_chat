"""
RDB MCP 기반 주식 데이터 서비스
RDB MCP를 통해 테마/종목 데이터를 조회하고 실시간 가격 정보 보강
"""
import asyncio
import yfinance as yf
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
from dataclasses import dataclass
from api.config import settings
from api.logging import setup_logging
from api.adapters.mcp_rdb import rdb_mcp

logger = setup_logging()

@dataclass
class StockInfo:
    """주식 정보"""
    symbol: str
    name: str
    sector: str
    industry: str
    market_cap: Optional[float] = None
    price: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None

@dataclass
class ThemeInfo:
    """테마 정보"""
    theme_name: str
    description: str
    stocks: List[StockInfo]
    performance: Optional[Dict[str, float]] = None

class StockDataService:
    """RDB MCP 기반 주식 데이터 서비스"""

    def __init__(self):
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = 300  # 5분 캐시
        self.rdb = rdb_mcp

    async def get_theme_stocks(self, theme_keyword: str) -> List[StockInfo]:
        """테마 키워드 기반 관련 종목 조회 - RDB MCP 사용"""
        try:
            # 캐시 확인
            cache_key = f"theme_{theme_keyword}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]

            # RDB MCP를 통해 테마 관련 종목 조회
            stock_data_list = await self.rdb.get_stocks_by_theme(theme_keyword, limit=20)

            theme_stocks = []
            for stock_data in stock_data_list:
                # RDB 데이터를 StockInfo로 변환
                stock_info = StockInfo(
                    symbol=stock_data.symbol,
                    name=stock_data.name,
                    sector=stock_data.sector,
                    industry=stock_data.industry,
                    market_cap=stock_data.market_cap,
                    price=stock_data.price,
                    change_percent=stock_data.change_percent,
                    volume=stock_data.volume
                )

                # 실시간 가격 정보가 없다면 보강
                if not stock_info.price:
                    enriched_stock = await self._enrich_with_price_data(
                        symbol=stock_info.symbol,
                        name=stock_info.name,
                        sector=stock_info.sector,
                        industry=stock_info.industry,
                        market_cap=stock_info.market_cap
                    )
                    if enriched_stock:
                        stock_info = enriched_stock

                theme_stocks.append(stock_info)

            # 캐시 저장
            self.cache[cache_key] = theme_stocks
            self.cache_expiry[cache_key] = datetime.now() + timedelta(seconds=self.cache_duration)

            return theme_stocks[:10]  # 상위 10개만

        except Exception as e:
            logger.error(f"테마 종목 조회 실패: {e}")
            return []

    async def get_stock_info(self, symbol: str, name: str = None) -> Optional[StockInfo]:
        """개별 종목 정보 조회"""
        try:
            cache_key = f"stock_{symbol}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]

            # Yahoo Finance에서 데이터 가져오기
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1d")

            if hist.empty:
                return None

            current_price = float(hist['Close'].iloc[-1])
            prev_close = float(info.get('previousClose', current_price))
            change_percent = ((current_price - prev_close) / prev_close * 100) if prev_close else 0

            stock_info = StockInfo(
                symbol=symbol,
                name=name or info.get('longName', info.get('shortName', symbol)),
                sector=info.get('sector', '정보없음'),
                industry=info.get('industry', '정보없음'),
                market_cap=info.get('marketCap'),
                price=current_price,
                change_percent=change_percent,
                volume=int(hist['Volume'].iloc[-1]) if not hist.empty else None
            )

            # 캐시 저장
            self.cache[cache_key] = stock_info
            self.cache_expiry[cache_key] = datetime.now() + timedelta(seconds=self.cache_duration)

            return stock_info

        except Exception as e:
            logger.error(f"종목 정보 조회 실패 {symbol}: {e}")
            return None

    async def get_market_themes(self) -> List[ThemeInfo]:
        """시장 주요 테마 조회 - RDB MCP 사용"""
        try:
            cache_key = "market_themes"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]

            # RDB MCP를 통해 모든 테마 조회
            theme_data_list = await self.rdb.get_all_themes()

            themes = []
            for theme_data in theme_data_list:
                # 각 테마의 종목들 조회
                stock_data_list = await self.rdb.get_theme_stocks(theme_data.theme_id)

                # StockData를 StockInfo로 변환
                stocks = []
                for stock_data in stock_data_list[:5]:  # 상위 5개만
                    stock_info = StockInfo(
                        symbol=stock_data.symbol,
                        name=stock_data.name,
                        sector=stock_data.sector,
                        industry=stock_data.industry,
                        market_cap=stock_data.market_cap,
                        price=stock_data.price,
                        change_percent=stock_data.change_percent,
                        volume=stock_data.volume
                    )

                    # 실시간 가격 정보가 없다면 보강
                    if not stock_info.price:
                        enriched_stock = await self._enrich_with_price_data(
                            symbol=stock_info.symbol,
                            name=stock_info.name,
                            sector=stock_info.sector,
                            industry=stock_info.industry,
                            market_cap=stock_info.market_cap
                        )
                        if enriched_stock:
                            stock_info = enriched_stock

                    stocks.append(stock_info)

                if stocks:
                    # 테마 성과 계산
                    valid_changes = [s.change_percent for s in stocks if s.change_percent is not None]
                    avg_change = sum(valid_changes) / len(valid_changes) if valid_changes else 0

                    theme_info = ThemeInfo(
                        theme_name=theme_data.theme_name,
                        description=theme_data.description or self._get_theme_description(theme_data.theme_name),
                        stocks=stocks,
                        performance={"avg_change_percent": avg_change}
                    )
                    themes.append(theme_info)

            # 캐시 저장
            self.cache[cache_key] = themes
            self.cache_expiry[cache_key] = datetime.now() + timedelta(seconds=self.cache_duration)

            return themes

        except Exception as e:
            logger.error(f"시장 테마 조회 실패: {e}")
            return []

    async def search_stocks_by_query(self, query: str, limit: int = 5) -> List[StockInfo]:
        """검색 쿼리 기반 종목 추천"""
        try:
            # AI 기반 키워드 추출 및 매핑
            keywords = self._extract_keywords_from_query(query)
            logger.info(f"추출된 키워드: {keywords}")

            all_stocks = []

            # 키워드별 종목 검색
            for keyword in keywords:
                theme_stocks = await self.get_theme_stocks(keyword)
                all_stocks.extend(theme_stocks)

            # 중복 제거 및 상위 종목 선택
            unique_stocks = {}
            for stock in all_stocks:
                if stock.symbol not in unique_stocks:
                    unique_stocks[stock.symbol] = stock

            # 시가총액 기준 정렬
            sorted_stocks = sorted(
                unique_stocks.values(),
                key=lambda x: x.market_cap or 0,
                reverse=True
            )

            return sorted_stocks[:limit]

        except Exception as e:
            logger.error(f"종목 검색 실패: {e}")
            return []

    async def get_top_performing_stocks(self, theme: str = None) -> List[StockInfo]:
        """상승률 기준 상위 종목"""
        try:
            if theme:
                stocks = await self.get_theme_stocks(theme)
            else:
                # 전체 주요 종목에서 조회
                all_stocks = []
                for theme_stocks in self.major_stocks.values():
                    for symbol, name, sector in theme_stocks:
                        stock = await self._get_stock_info(symbol, name, sector)
                        if stock:
                            all_stocks.append(stock)
                stocks = all_stocks

            # 상승률 기준 정렬
            sorted_stocks = sorted(
                [s for s in stocks if s.change_percent is not None],
                key=lambda x: x.change_percent,
                reverse=True
            )

            return sorted_stocks[:10]

        except Exception as e:
            logger.error(f"상위 종목 조회 실패: {e}")
            return []

    def _match_theme(self, keyword: str) -> Optional[str]:
        """키워드를 테마에 매핑"""
        keyword_lower = keyword.lower()

        theme_mapping = {
            "ai": "AI",
            "인공지능": "AI",
            "기계학습": "AI",
            "딥러닝": "AI",
            "반도체": "반도체",
            "메모리": "반도체",
            "칩": "반도체",
            "2차전지": "2차전지",
            "배터리": "2차전지",
            "에너지": "2차전지",
            "전기차": "자동차",
            "자동차": "자동차",
            "모빌리티": "자동차",
            "바이오": "바이오",
            "제약": "바이오",
            "의료": "바이오"
        }

        for key, theme in theme_mapping.items():
            if key in keyword_lower:
                return theme

        return None

    def _get_theme_description(self, theme: str) -> str:
        """테마 설명"""
        descriptions = {
            "AI": "인공지능, 머신러닝, 빅데이터 관련 기술 기업들",
            "반도체": "메모리, 시스템반도체, 반도체장비 관련 기업들",
            "2차전지": "리튬이온배터리, ESS, 전기차 배터리 관련 기업들",
            "자동차": "완성차, 자동차부품, 전기차, 자율주행 관련 기업들",
            "바이오": "신약개발, 바이오의약품, 헬스케어 관련 기업들"
        }
        return descriptions.get(theme, f"{theme} 관련 기업들")

    def _extract_keywords_from_query(self, query: str) -> List[str]:
        """쿼리에서 핵심 키워드 추출"""
        # 주요 키워드 패턴
        patterns = [
            r"AI|인공지능|기계학습|딥러닝",
            r"반도체|메모리|칩|HBM",
            r"배터리|2차전지|에너지|ESS",
            r"전기차|자동차|모빌리티",
            r"바이오|제약|의료|헬스케어"
        ]

        keywords = []
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            keywords.extend(matches)

        # 기본 키워드가 없으면 범용 검색
        if not keywords:
            keywords = ["AI"]  # 기본값

        return list(set(keywords))

    async def _get_stock_info(self, symbol: str, name: str, sector: str) -> Optional[StockInfo]:
        """내부용 주식 정보 조회"""
        return await self.get_stock_info(symbol, name)

    async def _search_stocks_by_keyword(self, keyword: str) -> List[StockInfo]:
        """키워드 기반 종목 검색 (백업 메서드)"""
        # 기본 테마 매핑에서 관련 종목 찾기
        related_stocks = []

        for theme_name, stock_list in self.major_stocks.items():
            if keyword.lower() in theme_name.lower():
                for symbol, name, sector in stock_list:
                    stock = await self._get_stock_info(symbol, name, sector)
                    if stock:
                        related_stocks.append(stock)

        return related_stocks[:5]

    async def _enrich_with_price_data(
        self,
        symbol: str,
        name: str,
        sector: str,
        industry: str = "",
        market_cap: float = None
    ) -> Optional[StockInfo]:
        """실시간 가격 정보로 종목 정보 보강"""
        if not symbol or not name:
            return None

        try:
            # Yahoo Finance에서 실시간 가격 조회
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            info = ticker.info

            if hist.empty:
                # 가격 정보가 없어도 기본 정보는 반환
                return StockInfo(
                    symbol=symbol,
                    name=name,
                    sector=sector,
                    industry=industry or sector,
                    market_cap=market_cap,
                    price=None,
                    change_percent=None,
                    volume=None
                )

            current_price = float(hist['Close'].iloc[-1])
            prev_close = float(info.get('previousClose', current_price))
            change_percent = ((current_price - prev_close) / prev_close * 100) if prev_close else 0

            return StockInfo(
                symbol=symbol,
                name=name,
                sector=sector,
                industry=industry or info.get('industry', sector),
                market_cap=market_cap or info.get('marketCap'),
                price=current_price,
                change_percent=change_percent,
                volume=int(hist['Volume'].iloc[-1]) if len(hist) > 0 else None
            )

        except Exception as e:
            logger.warning(f"가격 정보 조회 실패 {symbol}: {e}")
            # 가격 정보 없이라도 기본 정보 반환
            return StockInfo(
                symbol=symbol,
                name=name,
                sector=sector,
                industry=industry,
                market_cap=market_cap,
                price=None,
                change_percent=None,
                volume=None
            )

    async def search_stocks_by_query(self, query: str, limit: int = 5) -> List[StockInfo]:
        """검색 쿼리 기반 종목 추천 - RDB MCP 사용"""
        try:
            # RDB MCP를 통해 직접 검색
            stock_data_list = await self.rdb.search_stocks(query, limit)

            stocks = []
            for stock_data in stock_data_list:
                stock_info = StockInfo(
                    symbol=stock_data.symbol,
                    name=stock_data.name,
                    sector=stock_data.sector,
                    industry=stock_data.industry,
                    market_cap=stock_data.market_cap,
                    price=stock_data.price,
                    change_percent=stock_data.change_percent,
                    volume=stock_data.volume
                )

                # 실시간 가격 정보가 없다면 보강
                if not stock_info.price:
                    enriched_stock = await self._enrich_with_price_data(
                        symbol=stock_info.symbol,
                        name=stock_info.name,
                        sector=stock_info.sector,
                        industry=stock_info.industry,
                        market_cap=stock_info.market_cap
                    )
                    if enriched_stock:
                        stock_info = enriched_stock

                stocks.append(stock_info)

            return stocks

        except Exception as e:
            logger.error(f"종목 검색 실패: {e}")
            return []

    async def get_top_performing_stocks(self, theme: str = None) -> List[StockInfo]:
        """상승률 기준 상위 종목 - RDB MCP 사용"""
        try:
            # RDB MCP를 통해 상위 종목 조회
            stock_data_list = await self.rdb.get_top_performing_stocks(sector=theme, limit=20)

            stocks = []
            for stock_data in stock_data_list:
                stock_info = StockInfo(
                    symbol=stock_data.symbol,
                    name=stock_data.name,
                    sector=stock_data.sector,
                    industry=stock_data.industry,
                    market_cap=stock_data.market_cap,
                    price=stock_data.price,
                    change_percent=stock_data.change_percent,
                    volume=stock_data.volume
                )

                # 실시간 가격 정보가 없다면 보강
                if not stock_info.price:
                    enriched_stock = await self._enrich_with_price_data(
                        symbol=stock_info.symbol,
                        name=stock_info.name,
                        sector=stock_info.sector,
                        industry=stock_info.industry,
                        market_cap=stock_info.market_cap
                    )
                    if enriched_stock:
                        stock_info = enriched_stock

                stocks.append(stock_info)

            return stocks[:10]

        except Exception as e:
            logger.error(f"상위 종목 조회 실패: {e}")
            return []

    def _extract_keywords_from_query(self, query: str) -> List[str]:
        """쿼리에서 핵심 키워드 추출"""
        # 주요 키워드 패턴
        patterns = [
            r"AI|인공지능|기계학습|딥러닝",
            r"반도체|메모리|칩|HBM",
            r"배터리|2차전지|에너지|ESS",
            r"전기차|자동차|모빌리티",
            r"바이오|제약|의료|헬스케어",
            r"원자력|SMR|원전",
            r"건설|인프라|부동산"
        ]

        keywords = []
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            keywords.extend(matches)

        # 기본 키워드가 없으면 범용 검색
        if not keywords:
            keywords = ["반도체"]  # 기본값

        return list(set(keywords))

    def _get_theme_description(self, theme: str) -> str:
        """테마 설명"""
        descriptions = {
            "정보기술": "IT 서비스, 소프트웨어, 인터넷 플랫폼 기업들",
            "반도체": "메모리, 시스템반도체, 반도체장비 관련 기업들",
            "2차전지": "리튬이온배터리, ESS, 전기차 배터리 관련 기업들",
            "자동차": "완성차, 자동차부품, 전기차, 자율주행 관련 기업들",
            "바이오": "신약개발, 바이오의약품, 헬스케어 관련 기업들",
            "화학": "정유, 석유화학, 특수화학 관련 기업들",
            "건설": "건설, 인프라, 부동산 개발 관련 기업들",
            "에너지": "전력, 신재생에너지, 원자력 관련 기업들"
        }
        return descriptions.get(theme, f"{theme} 관련 기업들")

    def _is_cache_valid(self, key: str) -> bool:
        """캐시 유효성 확인"""
        if key not in self.cache or key not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[key]

    async def close(self):
        """리소스 정리"""
        if self.driver:
            await self.driver.close()

# 전역 인스턴스
stock_data_service = StockDataService()