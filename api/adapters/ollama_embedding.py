from __future__ import annotations
from typing import List, Dict, Any
import json
import requests
import anyio
from api.config import settings
from api.logging import setup_logging

logger = setup_logging()

class OllamaEmbeddingMCP:
    """
    원격 Ollama 서버(192.168.0.10)의 BGE-M3를 이용한 임베딩 생성 어댑터
    """

    def __init__(self):
        self.base_url = settings.get_bge_m3_base_url()
        self.model = settings.bge_m3_model

    async def ping(self) -> bool:
        """BGE-M3 Ollama 서버 연결 상태 확인"""
        def _ping() -> bool:
            try:
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                return response.status_code == 200
            except Exception as e:
                logger.error(f"[BGE-M3] ping error: {e}")
                return False

        return await anyio.to_thread.run_sync(_ping)

    async def encode(self, text: str) -> List[float]:
        """텍스트를 BGE-M3로 벡터화"""
        def _encode() -> List[float]:
            url = f"{self.base_url}/api/embeddings"

            payload = {
                "model": self.model,
                "prompt": text
            }

            headers = {
                "Content-Type": "application/json; charset=utf-8"
            }

            try:
                response = requests.post(
                    url,
                    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                    headers=headers,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("embedding", [])
                else:
                    logger.error(f"[BGE-M3] embedding error: {response.status_code} - {response.text}")
                    raise Exception(f"BGE-M3 embedding failed: {response.status_code}")

            except Exception as e:
                logger.error(f"[BGE-M3] encode error: {e}")
                raise

        logger.debug(f"[BGE-M3] encoding text: {text[:100]}...")
        return await anyio.to_thread.run_sync(_encode)

    async def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트를 일괄 벡터화"""
        embeddings = []

        for text in texts:
            embedding = await self.encode(text)
            embeddings.append(embedding)

        return embeddings

    async def similarity_search(self, query_embedding: List[float], candidate_embeddings: List[List[float]]) -> List[float]:
        """코사인 유사도 계산"""
        import numpy as np

        def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
            vec1_np = np.array(vec1)
            vec2_np = np.array(vec2)

            dot_product = np.dot(vec1_np, vec2_np)
            norm1 = np.linalg.norm(vec1_np)
            norm2 = np.linalg.norm(vec2_np)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return dot_product / (norm1 * norm2)

        similarities = []
        for candidate in candidate_embeddings:
            similarity = _cosine_similarity(query_embedding, candidate)
            similarities.append(similarity)

        return similarities