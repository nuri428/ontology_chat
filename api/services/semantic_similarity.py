# Semantic Similarity Filtering System
"""
의미적 유사도 필터링 시스템
- 벡터 임베딩 기반 유사도 계산
- 코사인 유사도 측정
- 의미적 중복 제거
- 관련성 기반 재정렬
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from api.config import settings
try:
    from langchain_ollama import OllamaEmbeddings
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import asyncio
from functools import lru_cache
import hashlib

@dataclass
class SemanticDocument:
    """의미적 문서 표현"""
    id: str
    text: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = None
    similarity_score: float = 0.0

class SemanticSimilarityFilter:
    """Ollama 기반 의미적 유사도 필터링 시스템"""

    def __init__(
        self,
        ollama_base_url: str = None,
        model_name: str = "bge-m3",
        similarity_threshold: float = 0.5,
        diversity_weight: float = 0.3,
        cache_embeddings: bool = True
    ):
        """
        초기화
        Args:
            ollama_base_url: Ollama 서버 URL
            model_name: Ollama에서 사용할 임베딩 모델
            similarity_threshold: 유사도 임계값
            diversity_weight: 다양성 가중치 (0-1)
            cache_embeddings: 임베딩 캐싱 여부
        """
        if not OLLAMA_AVAILABLE:
            raise ImportError("langchain_ollama가 필요합니다: pip install langchain-ollama")

        # 설정에서 임베딩 서버 URL 가져오기 (192.168.0.10)
        base_url = ollama_base_url or settings.get_bge_m3_base_url()

        self.embedding_client = OllamaEmbeddings(
            base_url=base_url,
            model=model_name
        )
        self.similarity_threshold = similarity_threshold
        self.diversity_weight = diversity_weight
        self.cache_embeddings = cache_embeddings
        self._embedding_cache = {} if cache_embeddings else None

    def _get_text_hash(self, text: str) -> str:
        """텍스트 해시 생성"""
        return hashlib.md5(text.encode()).hexdigest()

    def _get_embedding(self, text: str) -> np.ndarray:
        """Ollama를 통한 텍스트 임베딩 생성 (캐싱 지원)"""
        if self.cache_embeddings:
            text_hash = self._get_text_hash(text)
            if text_hash in self._embedding_cache:
                return self._embedding_cache[text_hash]

        # Ollama를 통한 임베딩 생성
        embedding_list = self.embedding_client.embed_query(text)
        embedding = np.array(embedding_list, dtype=np.float32)

        # 정규화
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        if self.cache_embeddings:
            self._embedding_cache[text_hash] = embedding

        return embedding

    async def filter_by_similarity(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        diversity_mode: bool = True,
        fast_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """
        의미적 유사도 기반 필터링

        Args:
            query: 검색 쿼리
            documents: 필터링할 문서 목록
            top_k: 반환할 최대 문서 수
            diversity_mode: 다양성 모드 활성화 여부

        Returns:
            필터링된 문서 목록
        """
        if not documents:
            return []

        # 쿼리 임베딩
        query_embedding = self._get_embedding(query)

        # 문서를 SemanticDocument로 변환
        semantic_docs = []
        for i, doc in enumerate(documents):
            text = doc.get("content") or doc.get("text") or doc.get("title") or ""
            if not text:
                continue

            semantic_doc = SemanticDocument(
                id=str(i),
                text=text,
                embedding=self._get_embedding(text),
                metadata=doc
            )
            semantic_docs.append(semantic_doc)

        # 유사도 계산
        for doc in semantic_docs:
            similarity = cosine_similarity(
                query_embedding.reshape(1, -1),
                doc.embedding.reshape(1, -1)
            )[0][0]
            doc.similarity_score = similarity

        # 관련성 임계값 적용으로 노이즈 감소
        filtered_docs = [doc for doc in semantic_docs if doc.similarity_score >= self.similarity_threshold]

        # 필터링 후 결과가 너무 적으면 임계값을 완화
        if len(filtered_docs) < 2:
            print(f"[DEBUG] 필터링 결과 부족({len(filtered_docs)}개), 임계값 완화")
            filtered_docs = [doc for doc in semantic_docs if doc.similarity_score >= 0.3]

        # 다양성 모드 (fast_mode일 때는 건너뛰어서 속도 향상)
        if diversity_mode and len(filtered_docs) > 1 and not fast_mode:
            filtered_docs = self._apply_diversity_filtering(filtered_docs)

        # 정렬
        filtered_docs.sort(key=lambda x: x.similarity_score, reverse=True)

        # top_k 적용
        if top_k:
            filtered_docs = filtered_docs[:top_k]

        # 원본 형식으로 변환하여 반환
        result = []
        for doc in filtered_docs:
            original_doc = doc.metadata.copy()
            original_doc["semantic_score"] = float(doc.similarity_score)
            result.append(original_doc)

        return result

    def _apply_diversity_filtering(
        self,
        documents: List[SemanticDocument]
    ) -> List[SemanticDocument]:
        """
        다양성 필터링 적용
        유사한 문서들을 제거하여 다양성 확보
        """
        if len(documents) <= 1:
            return documents

        selected = [documents[0]]  # 가장 유사도 높은 문서 선택

        for candidate in documents[1:]:
            # 기존 선택된 문서들과의 최대 유사도 계산
            max_similarity = 0
            for selected_doc in selected:
                similarity = cosine_similarity(
                    candidate.embedding.reshape(1, -1),
                    selected_doc.embedding.reshape(1, -1)
                )[0][0]
                max_similarity = max(max_similarity, similarity)

            # 다양성 점수 계산
            diversity_score = 1 - max_similarity

            # 최종 점수 = 쿼리 유사도 + 다양성 가중치
            final_score = (
                candidate.similarity_score * (1 - self.diversity_weight) +
                diversity_score * self.diversity_weight
            )

            # 다양성과 관련성의 균형을 위한 기준 강화
            if final_score >= 0.4:  # 기준 상향 조정
                selected.append(candidate)

        return selected

    async def rerank_by_semantic_relevance(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        combine_with_original: bool = True
    ) -> List[Dict[str, Any]]:
        """
        의미적 관련성으로 재정렬

        Args:
            query: 검색 쿼리
            documents: 재정렬할 문서 목록
            combine_with_original: 원본 점수와 결합 여부

        Returns:
            재정렬된 문서 목록
        """
        if not documents:
            return []

        # 쿼리 임베딩
        query_embedding = self._get_embedding(query)

        # 각 문서의 의미적 점수 계산
        for doc in documents:
            # 텍스트 찾기: content -> text -> title 순서로 시도
            text = doc.get("content") or doc.get("text") or doc.get("title") or ""
            if not text:
                doc["semantic_score"] = 0.0
                continue

            doc_embedding = self._get_embedding(text)
            similarity = cosine_similarity(
                query_embedding.reshape(1, -1),
                doc_embedding.reshape(1, -1)
            )[0][0]

            doc["semantic_score"] = float(similarity)

            # 원본 점수와 결합
            if combine_with_original and "score" in doc:
                original_score = doc.get("score", 0.0)
                # 정규화된 점수 결합 (7:3 비율)
                doc["combined_score"] = (
                    original_score * 0.7 +
                    similarity * 0.3
                )
            else:
                doc["combined_score"] = similarity

        # 결합 점수로 정렬
        documents.sort(key=lambda x: x.get("combined_score", 0), reverse=True)

        return documents

    def calculate_semantic_diversity(
        self,
        documents: List[Dict[str, Any]]
    ) -> float:
        """
        문서 집합의 의미적 다양성 계산

        Returns:
            다양성 점수 (0-1)
        """
        if len(documents) <= 1:
            return 1.0

        # 모든 문서의 임베딩 생성
        embeddings = []
        for doc in documents:
            text = doc.get("content") or doc.get("text") or doc.get("title") or ""
            if text:
                embeddings.append(self._get_embedding(text))

        if len(embeddings) <= 1:
            return 1.0

        # 모든 쌍의 유사도 계산
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(
                    embeddings[i].reshape(1, -1),
                    embeddings[j].reshape(1, -1)
                )[0][0]
                similarities.append(sim)

        # 평균 유사도가 낮을수록 다양성이 높음
        avg_similarity = np.mean(similarities)
        diversity_score = 1 - avg_similarity

        return float(diversity_score)

    def find_semantic_clusters(
        self,
        documents: List[Dict[str, Any]],
        n_clusters: int = 3
    ) -> List[List[Dict[str, Any]]]:
        """
        문서를 의미적 클러스터로 그룹화

        Args:
            documents: 클러스터링할 문서 목록
            n_clusters: 클러스터 수

        Returns:
            클러스터별 문서 목록
        """
        from sklearn.cluster import KMeans

        if len(documents) <= n_clusters:
            return [[doc] for doc in documents]

        # 임베딩 생성
        embeddings = []
        valid_docs = []
        for doc in documents:
            text = doc.get("content") or doc.get("text") or doc.get("title") or ""
            if text:
                embeddings.append(self._get_embedding(text))
                valid_docs.append(doc)

        if not embeddings:
            return []

        # K-means 클러스터링
        embeddings_matrix = np.vstack(embeddings)
        kmeans = KMeans(n_clusters=min(n_clusters, len(valid_docs)), random_state=42)
        labels = kmeans.fit_predict(embeddings_matrix)

        # 클러스터별로 문서 그룹화
        clusters = [[] for _ in range(n_clusters)]
        for doc, label in zip(valid_docs, labels):
            clusters[label].append(doc)

        # 빈 클러스터 제거
        clusters = [c for c in clusters if c]

        return clusters

    def clear_cache(self):
        """임베딩 캐시 초기화"""
        if self._embedding_cache:
            self._embedding_cache.clear()

# 전역 인스턴스 - 지연 초기화로 변경
semantic_filter = None

def get_semantic_filter():
    """지연 초기화된 semantic_filter 반환"""
    global semantic_filter
    if semantic_filter is None:
        semantic_filter = SemanticSimilarityFilter()
    return semantic_filter

# 헬퍼 함수
async def filter_similar_content(
    query: str,
    documents: List[Dict[str, Any]],
    threshold: float = 0.7,
    top_k: Optional[int] = None,
    fast_mode: bool = False
) -> List[Dict[str, Any]]:
    """
    유사 컨텐츠 필터링 헬퍼 함수
    """
    filter_instance = get_semantic_filter()
    return await filter_instance.filter_by_similarity(
        query=query,
        documents=documents,
        top_k=top_k,
        diversity_mode=True,
        fast_mode=fast_mode
    )

async def semantic_rerank(
    query: str,
    documents: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    의미적 재정렬 헬퍼 함수
    """
    filter_instance = get_semantic_filter()
    return await filter_instance.rerank_by_semantic_relevance(
        query=query,
        documents=documents,
        combine_with_original=True
    )