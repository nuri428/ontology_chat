"""
RDB MCP Adapter
주식 종목, 테마, 가격 데이터를 관계형 데이터베이스에서 조회
"""
import asyncio
import aiosqlite
import asyncpg
import aiomysql
from typing import Any, Dict, List, Optional, Union
import json
from dataclasses import dataclass
from datetime import datetime, date
from api.config import settings
from api.logging import setup_logging

logger = setup_logging()

@dataclass
class StockData:
    """주식 데이터 모델"""
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    price: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None
    last_updated: Optional[datetime] = None

@dataclass
class ThemeData:
    """테마 데이터 모델"""
    theme_id: str
    theme_name: str
    description: Optional[str] = None
    sector: Optional[str] = None
    stocks: List[StockData] = None

class RdbMCP:
    """관계형 데이터베이스 MCP 어댑터"""

    def __init__(self, db_type: str = "mysql", connection_config: dict = None):
        self.db_type = db_type.lower()
        self.connection_config = connection_config or self._get_default_connection_config()
        self.connection = None
        self.pool = None

    def _get_default_connection_config(self) -> dict:
        """기본 연결 설정 반환"""
        if self.db_type == "mysql":
            return {
                "host": "192.168.0.21",
                "port": 3306,
                "user": "scraper",
                "password": "Scraper123!",
                "db": "stock_db",
                "charset": "utf8mb4",
                "autocommit": True
            }
        elif self.db_type == "sqlite":
            return {"database": getattr(settings, 'sqlite_db_path', './stock_data.db')}
        elif self.db_type == "postgresql":
            return {
                "host": getattr(settings, 'postgres_host', 'localhost'),
                "port": getattr(settings, 'postgres_port', 5432),
                "user": getattr(settings, 'postgres_user', 'postgres'),
                "password": getattr(settings, 'postgres_password', 'password'),
                "database": getattr(settings, 'postgres_database', 'stock_db')
            }
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    async def connect(self):
        """데이터베이스 연결"""
        try:
            if self.db_type == "mysql":
                self.pool = await aiomysql.create_pool(**self.connection_config)
            elif self.db_type == "sqlite":
                self.connection = await aiosqlite.connect(self.connection_config["database"])
                await self.connection.execute("PRAGMA foreign_keys = ON")
            elif self.db_type == "postgresql":
                self.connection = await asyncpg.connect(**self.connection_config)
            logger.info(f"RDB 연결 성공: {self.db_type}")
        except Exception as e:
            logger.error(f"RDB 연결 실패: {e}")
            raise

    async def disconnect(self):
        """데이터베이스 연결 해제"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def _execute_query(self, query: str, params: Union[Dict, List, tuple] = None) -> List[Dict[str, Any]]:
        """쿼리 실행 및 결과 반환"""
        if self.db_type == "mysql" and not self.pool:
            await self.connect()
        elif self.db_type != "mysql" and not self.connection:
            await self.connect()

        try:
            if self.db_type == "mysql":
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(query, params or ())
                        rows = await cursor.fetchall()
                        # 컬럼 정보 가져오기
                        columns = [desc[0] for desc in cursor.description]
                        # 딕셔너리 형태로 변환
                        result = [dict(zip(columns, row)) for row in rows]

            elif self.db_type == "sqlite":
                if params:
                    if isinstance(params, dict):
                        # 딕셔너리 매개변수를 리스트로 변환
                        param_values = [params.get(key) for key in params.keys()]
                        cursor = await self.connection.execute(query, param_values)
                    else:
                        cursor = await self.connection.execute(query, params)
                else:
                    cursor = await self.connection.execute(query)

                rows = await cursor.fetchall()
                # 컬럼명 가져오기
                columns = [description[0] for description in cursor.description]
                # 딕셔너리 형태로 변환
                result = [dict(zip(columns, row)) for row in rows]

            elif self.db_type == "postgresql":
                if params:
                    if isinstance(params, dict):
                        rows = await self.connection.fetch(query, *params.values())
                    else:
                        rows = await self.connection.fetch(query, *params)
                else:
                    rows = await self.connection.fetch(query)

                # asyncpg Row를 딕셔너리로 변환
                result = [dict(row) for row in rows]

            return result

        except Exception as e:
            logger.error(f"쿼리 실행 실패: {query}, 오류: {e}")
            raise

    async def get_stocks_by_theme(self, theme_keyword: str, limit: int = 20) -> List[StockData]:
        """테마 키워드로 관련 종목 조회"""
        query = """
        SELECT DISTINCT
            s.symbol,
            s.name,
            s.sector,
            s.industry,
            s.market_cap,
            p.price,
            p.change_percent,
            p.volume,
            p.last_updated
        FROM stocks s
        LEFT JOIN stock_prices p ON s.symbol = p.symbol
        LEFT JOIN stock_themes st ON s.symbol = st.stock_symbol
        LEFT JOIN themes t ON st.theme_id = t.theme_id
        WHERE (
            s.sector LIKE %s OR
            s.industry LIKE %s OR
            s.name LIKE %s OR
            t.theme_name LIKE %s OR
            t.description LIKE %s
        )
        AND s.is_active = 1
        ORDER BY s.market_cap DESC
        LIMIT %s
        """

        keyword_pattern = f"%{theme_keyword}%"
        params = [keyword_pattern] * 5 + [limit]

        rows = await self._execute_query(query, params)

        stocks = []
        for row in rows:
            stock = StockData(
                symbol=row['symbol'],
                name=row['name'],
                sector=row.get('sector'),
                industry=row.get('industry'),
                market_cap=row.get('market_cap'),
                price=row.get('price'),
                change_percent=row.get('change_percent'),
                volume=row.get('volume'),
                last_updated=row.get('last_updated')
            )
            stocks.append(stock)

        return stocks

    async def get_all_themes(self) -> List[ThemeData]:
        """모든 테마 조회"""
        query = """
        SELECT
            t.theme_id,
            t.theme_name,
            t.description,
            t.sector,
            COUNT(st.stock_symbol) as stock_count
        FROM themes t
        LEFT JOIN stock_themes st ON t.theme_id = st.theme_id
        GROUP BY t.theme_id, t.theme_name, t.description, t.sector
        HAVING stock_count > 0
        ORDER BY stock_count DESC
        """

        rows = await self._execute_query(query)

        themes = []
        for row in rows:
            theme = ThemeData(
                theme_id=row['theme_id'],
                theme_name=row['theme_name'],
                description=row.get('description'),
                sector=row.get('sector')
            )
            themes.append(theme)

        return themes

    async def get_theme_stocks(self, theme_id: str) -> List[StockData]:
        """특정 테마의 종목들 조회"""
        query = """
        SELECT
            s.symbol,
            s.name,
            s.sector,
            s.industry,
            s.market_cap,
            p.price,
            p.change_percent,
            p.volume,
            p.last_updated
        FROM stocks s
        JOIN stock_themes st ON s.symbol = st.stock_symbol
        LEFT JOIN stock_prices p ON s.symbol = p.symbol
        WHERE st.theme_id = %s
        AND s.is_active = 1
        ORDER BY s.market_cap DESC
        """

        rows = await self._execute_query(query, [theme_id])

        stocks = []
        for row in rows:
            stock = StockData(
                symbol=row['symbol'],
                name=row['name'],
                sector=row.get('sector'),
                industry=row.get('industry'),
                market_cap=row.get('market_cap'),
                price=row.get('price'),
                change_percent=row.get('change_percent'),
                volume=row.get('volume'),
                last_updated=row.get('last_updated')
            )
            stocks.append(stock)

        return stocks

    async def get_stock_by_symbol(self, symbol: str) -> Optional[StockData]:
        """종목 코드로 개별 종목 조회"""
        query = """
        SELECT
            s.symbol,
            s.name,
            s.sector,
            s.industry,
            s.market_cap,
            p.price,
            p.change_percent,
            p.volume,
            p.last_updated
        FROM stocks s
        LEFT JOIN stock_prices p ON s.symbol = p.symbol
        WHERE s.symbol = %s
        AND s.is_active = 1
        """

        rows = await self._execute_query(query, [symbol])

        if not rows:
            return None

        row = rows[0]
        return StockData(
            symbol=row['symbol'],
            name=row['name'],
            sector=row.get('sector'),
            industry=row.get('industry'),
            market_cap=row.get('market_cap'),
            price=row.get('price'),
            change_percent=row.get('change_percent'),
            volume=row.get('volume'),
            last_updated=row.get('last_updated')
        )

    async def search_stocks(self, query: str, limit: int = 10) -> List[StockData]:
        """종목 이름/코드로 검색"""
        search_query = """
        SELECT
            s.symbol,
            s.name,
            s.sector,
            s.industry,
            s.market_cap,
            p.price,
            p.change_percent,
            p.volume,
            p.last_updated
        FROM stocks s
        LEFT JOIN stock_prices p ON s.symbol = p.symbol
        WHERE (
            s.name LIKE %s OR
            s.symbol LIKE %s OR
            s.sector LIKE %s OR
            s.industry LIKE %s
        )
        AND s.is_active = 1
        ORDER BY
            CASE
                WHEN s.name LIKE %s THEN 1
                WHEN s.symbol LIKE %s THEN 2
                ELSE 3
            END,
            s.market_cap DESC
        LIMIT %s
        """

        keyword_pattern = f"%{query}%"
        exact_pattern = f"{query}%"
        params = [keyword_pattern] * 4 + [exact_pattern] * 2 + [limit]

        rows = await self._execute_query(search_query, params)

        stocks = []
        for row in rows:
            stock = StockData(
                symbol=row['symbol'],
                name=row['name'],
                sector=row.get('sector'),
                industry=row.get('industry'),
                market_cap=row.get('market_cap'),
                price=row.get('price'),
                change_percent=row.get('change_percent'),
                volume=row.get('volume'),
                last_updated=row.get('last_updated')
            )
            stocks.append(stock)

        return stocks

    async def get_top_performing_stocks(self, sector: str = None, limit: int = 20) -> List[StockData]:
        """상승률 기준 상위 종목 조회"""
        base_query = """
        SELECT
            s.symbol,
            s.name,
            s.sector,
            s.industry,
            s.market_cap,
            p.price,
            p.change_percent,
            p.volume,
            p.last_updated
        FROM stocks s
        JOIN stock_prices p ON s.symbol = p.symbol
        WHERE s.is_active = 1
        AND p.change_percent IS NOT NULL
        """

        params = []
        if sector:
            base_query += " AND s.sector = %s"
            params.append(sector)

        base_query += " ORDER BY p.change_percent DESC LIMIT %s"
        params.append(limit)

        rows = await self._execute_query(base_query, params)

        stocks = []
        for row in rows:
            stock = StockData(
                symbol=row['symbol'],
                name=row['name'],
                sector=row.get('sector'),
                industry=row.get('industry'),
                market_cap=row.get('market_cap'),
                price=row.get('price'),
                change_percent=row.get('change_percent'),
                volume=row.get('volume'),
                last_updated=row.get('last_updated')
            )
            stocks.append(stock)

        return stocks

    async def create_tables(self):
        """데이터베이스 테이블 생성 (초기 설정용) - MySQL 버전"""
        if self.db_type == "mysql":
            tables = [
                """
                CREATE TABLE IF NOT EXISTS stocks (
                    symbol VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    sector VARCHAR(100),
                    industry VARCHAR(100),
                    market_cap BIGINT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """,
                """
                CREATE TABLE IF NOT EXISTS stock_prices (
                    symbol VARCHAR(20) PRIMARY KEY,
                    price DECIMAL(15,4),
                    change_percent DECIMAL(8,4),
                    volume BIGINT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """,
                """
                CREATE TABLE IF NOT EXISTS themes (
                    theme_id VARCHAR(50) PRIMARY KEY,
                    theme_name VARCHAR(200) NOT NULL,
                    description TEXT,
                    sector VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """,
                """
                CREATE TABLE IF NOT EXISTS stock_themes (
                    stock_symbol VARCHAR(20),
                    theme_id VARCHAR(50),
                    weight DECIMAL(3,2) DEFAULT 1.0,
                    PRIMARY KEY (stock_symbol, theme_id),
                    FOREIGN KEY (stock_symbol) REFERENCES stocks(symbol) ON DELETE CASCADE,
                    FOREIGN KEY (theme_id) REFERENCES themes(theme_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            ]
        else:
            # SQLite/PostgreSQL용 기존 테이블 정의
            tables = [
                """
                CREATE TABLE IF NOT EXISTS stocks (
                    symbol VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    sector VARCHAR(100),
                    industry VARCHAR(100),
                    market_cap BIGINT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS stock_prices (
                    symbol VARCHAR(20) PRIMARY KEY,
                    price DECIMAL(15,4),
                    change_percent DECIMAL(8,4),
                    volume BIGINT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS themes (
                    theme_id VARCHAR(50) PRIMARY KEY,
                    theme_name VARCHAR(200) NOT NULL,
                    description TEXT,
                    sector VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS stock_themes (
                    stock_symbol VARCHAR(20),
                    theme_id VARCHAR(50),
                    weight DECIMAL(3,2) DEFAULT 1.0,
                    PRIMARY KEY (stock_symbol, theme_id),
                    FOREIGN KEY (stock_symbol) REFERENCES stocks(symbol),
                    FOREIGN KEY (theme_id) REFERENCES themes(theme_id)
                )
                """
            ]

        for table_sql in tables:
            await self._execute_query(table_sql)

        logger.info(f"데이터베이스 테이블 생성 완료: {self.db_type}")

# 전역 인스턴스 - MySQL 연결
rdb_mcp = RdbMCP(
    db_type="mysql",
    connection_config={
        "host": "192.168.0.21",
        "port": 3306,
        "user": "scraper",
        "password": "Scraper123!",
        "db": "stock_db",
        "charset": "utf8mb4",
        "autocommit": True
    }
)