# Dynamic Context Pruning System
"""
관련성 감소 기반 동적 컨텍스트 프루닝 시스템
- 시간 기반 감쇠 (recency decay)
- 거리 기반 감쇠 (distance decay)
- 중복도 기반 제거 (redundancy pruning)
- 임계값 기반 필터링 (threshold filtering)
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import time
from datetime import datetime, timedelta
import numpy as np
from collections import Counter
import hashlib
import re

@dataclass
class ContextItem:
    """컨텍스트 항목"""
    content: str
    source: str
    timestamp: Optional[datetime]
    relevance_score: float
    metadata: Dict[str, Any]

    def get_age_hours(self) -> float:
        """항목 나이(시간) 계산"""
        if not self.timestamp:
            return 0.0
        delta = datetime.now() - self.timestamp
        return delta.total_seconds() / 3600

class DynamicContextPruner:
    """동적 컨텍스트 프루닝 시스템"""

    def __init__(
        self,
        max_tokens: int = 2048,
        relevance_threshold: float = 0.3,
        time_decay_factor: float = 0.95,
        redundancy_threshold: float = 0.85
    ):
        self.max_tokens = max_tokens
        self.relevance_threshold = relevance_threshold
        self.time_decay_factor = time_decay_factor
        self.redundancy_threshold = redundancy_threshold

    def prune_context(
        self,
        context_items: List[Dict[str, Any]],
        query: str,
        strategy: str = "adaptive"
    ) -> List[Dict[str, Any]]:
        """컨텍스트 프루닝 실행"""

        # ContextItem 객체로 변환
        items = self._convert_to_context_items(context_items)

        # 1. 관련성 기반 필터링
        items = self._filter_by_relevance(items, self.relevance_threshold)

        # 2. 시간 기반 감쇠 적용
        items = self._apply_time_decay(items)

        # 3. 중복 제거
        items = self._remove_redundancy(items)

        # 4. 전략별 프루닝
        if strategy == "aggressive":
            items = self._aggressive_pruning(items, query)
        elif strategy == "conservative":
            items = self._conservative_pruning(items, query)
        else:  # adaptive
            items = self._adaptive_pruning(items, query)

        # 5. 토큰 제한 적용
        items = self._apply_token_limit(items)

        # Dict로 다시 변환
        return self._convert_to_dicts(items)

    def _convert_to_context_items(
        self,
        context_items: List[Dict[str, Any]]
    ) -> List[ContextItem]:
        """Dict를 ContextItem으로 변환"""
        items = []
        for item in context_items:
            # 타임스탬프 파싱
            timestamp = None
            if "timestamp" in item:
                try:
                    timestamp = datetime.fromisoformat(item["timestamp"])
                except:
                    pass
            elif "created_at" in item:
                try:
                    timestamp = datetime.fromisoformat(item["created_at"])
                except:
                    pass

            items.append(ContextItem(
                content=item.get("content", item.get("text", "")),
                source=item.get("source", "unknown"),
                timestamp=timestamp,
                relevance_score=item.get("score", item.get("relevance_score", 1.0)),
                metadata=item.get("metadata", {})
            ))
        return items

    def _convert_to_dicts(self, items: List[ContextItem]) -> List[Dict[str, Any]]:
        """ContextItem을 Dict로 변환"""
        result = []
        for item in items:
            d = {
                "content": item.content,
                "source": item.source,
                "relevance_score": item.relevance_score,
                "metadata": item.metadata
            }
            if item.timestamp:
                d["timestamp"] = item.timestamp.isoformat()
            result.append(d)
        return result

    def _filter_by_relevance(
        self,
        items: List[ContextItem],
        threshold: float
    ) -> List[ContextItem]:
        """관련성 임계값 기반 필터링"""
        filtered = [item for item in items if item.relevance_score >= threshold]

        # 최소 3개는 유지
        if len(filtered) < 3 and len(items) >= 3:
            sorted_items = sorted(items, key=lambda x: x.relevance_score, reverse=True)
            return sorted_items[:3]

        return filtered

    def _apply_time_decay(self, items: List[ContextItem]) -> List[ContextItem]:
        """시간 기반 관련성 감쇠"""
        for item in items:
            age_hours = item.get_age_hours()

            # 24시간마다 5% 감쇠
            decay_factor = self.time_decay_factor ** (age_hours / 24)
            item.relevance_score *= decay_factor

            # 메타데이터에 감쇠 정보 저장
            item.metadata["time_decay_applied"] = decay_factor
            item.metadata["age_hours"] = age_hours

        return items

    def _remove_redundancy(self, items: List[ContextItem]) -> List[ContextItem]:
        """중복 컨텐츠 제거"""
        unique_items = []
        seen_hashes = set()

        for item in items:
            # 컨텐츠 해시 생성 (소문자, 공백 정규화)
            normalized = re.sub(r'\s+', ' ', item.content.lower().strip())
            content_hash = hashlib.md5(normalized.encode()).hexdigest()[:8]

            # 유사도 체크
            is_redundant = False
            for seen_hash in seen_hashes:
                similarity = self._calculate_similarity(content_hash, seen_hash)
                if similarity > self.redundancy_threshold:
                    is_redundant = True
                    item.metadata["redundant"] = True
                    break

            if not is_redundant:
                unique_items.append(item)
                seen_hashes.add(content_hash)

        return unique_items

    def _calculate_similarity(self, hash1: str, hash2: str) -> float:
        """해시 기반 유사도 계산 (간단한 버전)"""
        if hash1 == hash2:
            return 1.0

        # 해시 문자 일치 비율
        matches = sum(c1 == c2 for c1, c2 in zip(hash1, hash2))
        return matches / len(hash1)

    def _aggressive_pruning(
        self,
        items: List[ContextItem],
        query: str
    ) -> List[ContextItem]:
        """공격적 프루닝 - 상위 N개만 유지"""
        # 관련성 점수 상위 30%만 유지
        sorted_items = sorted(items, key=lambda x: x.relevance_score, reverse=True)
        keep_count = max(3, len(items) // 3)
        return sorted_items[:keep_count]

    def _conservative_pruning(
        self,
        items: List[ContextItem],
        query: str
    ) -> List[ContextItem]:
        """보수적 프루닝 - 최대한 유지"""
        # 관련성 점수 하위 20%만 제거
        sorted_items = sorted(items, key=lambda x: x.relevance_score, reverse=True)
        keep_count = max(5, int(len(items) * 0.8))
        return sorted_items[:keep_count]

    def _adaptive_pruning(
        self,
        items: List[ContextItem],
        query: str
    ) -> List[ContextItem]:
        """적응형 프루닝 - 쿼리 복잡도에 따라 조절"""
        # 쿼리 복잡도 계산
        query_words = query.split()
        complexity = len(query_words)

        if complexity < 3:  # 간단한 쿼리
            return self._aggressive_pruning(items, query)
        elif complexity > 7:  # 복잡한 쿼리
            return self._conservative_pruning(items, query)
        else:  # 중간 복잡도
            # 상위 50% 유지
            sorted_items = sorted(items, key=lambda x: x.relevance_score, reverse=True)
            keep_count = max(4, len(items) // 2)
            return sorted_items[:keep_count]

    def _apply_token_limit(self, items: List[ContextItem]) -> List[ContextItem]:
        """토큰 제한 적용"""
        result = []
        total_tokens = 0

        # 관련성 순으로 정렬
        sorted_items = sorted(items, key=lambda x: x.relevance_score, reverse=True)

        for item in sorted_items:
            # 간단한 토큰 추정 (실제로는 tokenizer 사용 권장)
            item_tokens = len(item.content.split()) * 1.3

            if total_tokens + item_tokens <= self.max_tokens:
                result.append(item)
                total_tokens += item_tokens
            else:
                # 토큰 한계 도달
                item.metadata["pruned_reason"] = "token_limit"
                break

        return result

    def calculate_pruning_stats(
        self,
        original: List[Dict[str, Any]],
        pruned: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """프루닝 통계 계산"""
        original_tokens = sum(len(item.get("content", "").split()) for item in original)
        pruned_tokens = sum(len(item.get("content", "").split()) for item in pruned)

        return {
            "original_count": len(original),
            "pruned_count": len(pruned),
            "reduction_ratio": 1 - (len(pruned) / len(original)) if original else 0,
            "original_tokens": original_tokens,
            "pruned_tokens": pruned_tokens,
            "token_reduction": 1 - (pruned_tokens / original_tokens) if original_tokens else 0
        }

# 전역 프루너 인스턴스
context_pruner = DynamicContextPruner()

def prune_search_results(
    results: List[Dict[str, Any]],
    query: str,
    max_items: int = 10
) -> List[Dict[str, Any]]:
    """검색 결과 프루닝 헬퍼 함수"""
    # 점수가 없는 항목에 기본값 설정
    for result in results:
        if "score" not in result:
            result["score"] = result.get("relevance_score", 1.0)

    # 프루닝 실행
    pruned = context_pruner.prune_context(
        results[:max_items * 2],  # 일단 2배수 가져옴
        query,
        strategy="adaptive"
    )

    return pruned[:max_items]