from __future__ import annotations
from typing import Any, Dict, List
from api.logging import setup_logging
logger = setup_logging()
from opensearchpy import OpenSearch, helpers
import anyio
import requests
import json
from requests.auth import HTTPBasicAuth
from api.config import settings

class OpenSearchMCP:
    """
    OpenSearch 어댑터 (동기 클라이언트를 비동기에서 사용)
    - search / get / bulk / ping
    """
    def __init__(self) -> None:
        self._host = settings.opensearch_host
        self._user = settings.opensearch_user
        self._password = settings.opensearch_password
        self._client: OpenSearch | None = None

    def _get_client(self) -> OpenSearch:
        if self._client is None:
            logger.info(f"[OS] Connecting host={self._host}")
            # HTTP/Basic 인증
            self._client = OpenSearch(
                hosts=[self._host],
                http_auth=(self._user, self._password),
                verify_certs=False,  # 사설망/자체 서명일 수 있으므로 기본 False
                ssl_show_warn=False,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True,
                # UTF-8 인코딩 명시적 설정
                http_compress=True,
                headers={'Content-Type': 'application/json; charset=utf-8'},
            )
        return self._client

    async def ping(self) -> bool:
        def _ping() -> bool:
            return self._get_client().ping()
        try:
            return await anyio.to_thread.run_sync(_ping)
        except Exception as e:
            logger.error(f"[OS] ping error: {e}")
            return False

    async def search(self, index: str, query: Dict[str, Any], size: int = 10, from_: int = 0) -> Dict[str, Any]:
        def _search() -> Dict[str, Any]:
            # requests를 사용한 직접 호출 (UTF-8 문제 해결)
            url = f"{self._host}/{index}/_search"
            
            # 쿼리에 size와 from 추가
            search_body = {
                **query,
                "size": size,
                "from": from_
            }
            
            # UTF-8 인코딩으로 JSON 직렬화
            json_data = json.dumps(search_body, ensure_ascii=False)
            
            headers = {
                'Content-Type': 'application/json; charset=utf-8'
            }
            
            response = requests.post(
                url,
                data=json_data.encode('utf-8'),
                headers=headers,
                auth=HTTPBasicAuth(self._user, self._password),
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"[OS] search error: {response.status_code} - {response.text}")
                raise Exception(f"OpenSearch search failed: {response.status_code} - {response.text}")
                
        logger.debug(f"[OS] search index={index} q={query}")
        return await anyio.to_thread.run_sync(_search)

    async def get(self, index: str, id: str) -> Dict[str, Any]:
        def _get() -> Dict[str, Any]:
            return self._get_client().get(index=index, id=id)
        return await anyio.to_thread.run_sync(_get)

    async def bulk_index(self, index: str, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        docs: [{"_id": "...", "_source": {...}}, ...] 또는 {"id": "...", "doc": {...}} 형태 지원
        """
        def _bulk() -> Dict[str, Any]:
            actions = []
            for d in docs:
                if "_source" in d or d.get("_op_type"):
                    # 이미 actions 형태
                    actions.append({**d, "_index": index})
                else:
                    # 단순 문서 → index action으로 변환
                    doc_id = d.get("_id") or d.get("id")
                    actions.append({"_op_type": "index", "_index": index, "_id": doc_id, "_source": d.get("_source") or d.get("doc") or d})
            success, errors = helpers.bulk(self._get_client(), actions)
            return {"success": success, "errors": errors}
        logger.info(f"[OS] bulk_index index={index} count={len(docs)}")
        return await anyio.to_thread.run_sync(_bulk)