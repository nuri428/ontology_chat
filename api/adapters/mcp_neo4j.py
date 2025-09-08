from __future__ import annotations
from typing import Any, Dict, List
from loguru import logger
from neo4j import AsyncGraphDatabase, AsyncDriver
from api.config import settings


class Neo4jMCP:
    """
    비동기 Neo4j 어댑터 (MCP 스타일)
    - query: Cypher 실행 후 list[dict] 반환
    - ping: 연결 확인
    """

    def __init__(self) -> None:
        self._uri = settings.neo4j_uri
        self._user = settings.neo4j_user
        self._password = settings.neo4j_password
        self._database = settings.neo4j_database
        self._driver: AsyncDriver | None = None

    async def _ensure_driver(self) -> AsyncDriver:
        if self._driver is None:
            logger.info(f"[Neo4j] Connecting uri={self._uri} db={self._database}")
            self._driver = AsyncGraphDatabase.driver(
                self._uri, auth=(self._user, self._password)
            )
        return self._driver

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("[Neo4j] Driver closed")

    async def ping(self) -> bool:
        """
        연결 확인 + 현재 DB + 전체 DB 목록(권한 시) 반환
        - Neo4j 4.x: CALL db.info() 사용
        - Neo4j 5.x: SHOW CURRENT DATABASE 사용 (fallback 포함)
        """
        info: Dict[str, Any] = {"database": self._database}

        driver = await self._ensure_driver()

        # 1) 최소 핑 (현재 DB 세션)
        try:
            async with driver.session(database=self._database) as session:
                r = await session.run("RETURN 1 AS ok")
                row = await r.single()
                info["ok"] = bool(row and row.get("ok") == 1)
        except Exception as e:
            info["ok"] = False
            info["error"] = f"basic ping failed: {e!s}"
            return info

        # 2) 현재 세션 DB 이름 조회 (버전 호환: 5.x → SHOW, 4.x → CALL db.info())
        current_db: List[Dict[str, Any]] = []
        try:
            async with driver.session(database=self._database) as session:
                # 우선 5.x 구문 시도
                cur = await session.run("SHOW CURRENT DATABASE")
                current_db = [rec.data() async for rec in cur]
        except Exception:
            try:
                async with driver.session(database=self._database) as session:
                    cur = await session.run("CALL db.info() YIELD name RETURN name")
                    current_db = [rec.data() async for rec in cur]
            except Exception as e:
                info["current_database_error"] = str(e)
        if current_db:
            info["current_database"] = current_db

        # 3) 전체 DB 목록은 system DB에서 (권한 필요). 중복 제거.
        try:
            async with driver.session(database="system") as sys_sess:
                cur = await sys_sess.run(
                    "SHOW DATABASES YIELD name, currentStatus, default "
                    "RETURN name, currentStatus, default ORDER BY name"
                )
                rows = [rec.data() async for rec in cur]
                dedup = {}
                for r in rows:
                    dedup[r["name"]] = r  # 같은 이름이 오면 마지막 값으로 덮어씀
                info["databases"] = list(dedup.values())
        except Exception as e:
            info["databases_error"] = (
                f"SHOW DATABASES failed (need permissions?): {e!s}"
            )
        return info

    async def query(
        self, cypher: str, params: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        params = params or {}
        driver = await self._ensure_driver()
        logger.debug(f"[Neo4j] Cypher={cypher} params={params}")
        async with driver.session(database=self._database) as session:
            cursor = await session.run(cypher, params)
            records = []
            async for record in cursor:
                records.append(record.data())
            return records
