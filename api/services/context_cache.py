# Context Caching Mechanism for Ontology Chat
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import time
import json
from datetime import datetime, timedelta
from collections import OrderedDict
import asyncio
from dataclasses import dataclass, field, asdict

@dataclass
class CacheEntry:
    """캐시 엔트리 구조체"""
    key: str
    query: str
    context: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    timestamp: float
    hit_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    ttl: int = 900  # 15분 기본 TTL

    def is_expired(self) -> bool:
        """캐시 만료 여부 확인"""
        return time.time() - self.timestamp > self.ttl

    def update_access(self) -> None:
        """접근 정보 업데이트"""
        self.hit_count += 1
        self.last_accessed = time.time()

class ContextCache:
    """컨텍스트 캐싱 시스템"""

    def __init__(
        self,
        max_size: int = 100,
        default_ttl: int = 900,
        cleanup_interval: int = 300
    ):
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0
        }
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    def _generate_key(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """쿼리와 파라미터로 캐시 키 생성"""
        # query가 리스트인 경우 문자열로 변환
        if isinstance(query, list):
            query = " ".join(str(item) for item in query)
        elif not isinstance(query, str):
            query = str(query)

        key_parts = [query]

        if params:
            # 파라미터를 정렬하여 일관된 키 생성
            sorted_params = sorted(params.items())
            param_str = json.dumps(sorted_params, sort_keys=True)
            key_parts.append(param_str)

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def get(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
        """캐시에서 컨텍스트 조회"""
        async with self._lock:
            key = self._generate_key(query, params)
            self.stats["total_requests"] += 1

            if key in self.cache:
                entry = self.cache[key]

                if not entry.is_expired():
                    # LRU: 최근 사용 항목을 끝으로 이동
                    self.cache.move_to_end(key)
                    entry.update_access()

                    self.stats["hits"] += 1

                    # 캐시 히트 로그
                    cache_info = {
                        "hit_rate": self._calculate_hit_rate(),
                        "cache_size": len(self.cache),
                        "hit_count": entry.hit_count
                    }

                    return entry.context, {
                        **entry.metadata,
                        "cache_hit": True,
                        "cache_info": cache_info
                    }
                else:
                    # 만료된 엔트리 제거
                    del self.cache[key]

            self.stats["misses"] += 1
            return None

    async def set(
        self,
        query: str,
        context: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> None:
        """컨텍스트를 캐시에 저장"""
        async with self._lock:
            key = self._generate_key(query, params)

            # 캐시 크기 제한 확인
            if len(self.cache) >= self.max_size:
                # LRU 정책: 가장 오래된 항목 제거
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.stats["evictions"] += 1

            # 새 엔트리 추가
            entry = CacheEntry(
                key=key,
                query=query,
                context=context,
                metadata=metadata or {},
                timestamp=time.time(),
                ttl=ttl or self.default_ttl
            )

            self.cache[key] = entry

    async def invalidate(
        self,
        query: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> int:
        """특정 쿼리 또는 패턴의 캐시 무효화"""
        async with self._lock:
            invalidated = 0

            if query:
                # 특정 쿼리 무효화
                key = self._generate_key(query)
                if key in self.cache:
                    del self.cache[key]
                    invalidated = 1
            elif pattern:
                # 패턴 매칭으로 무효화
                keys_to_remove = []
                for key, entry in self.cache.items():
                    if pattern in entry.query:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self.cache[key]
                    invalidated += 1

            return invalidated

    async def clear(self) -> None:
        """전체 캐시 초기화"""
        async with self._lock:
            self.cache.clear()
            self.stats = {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "total_requests": 0
            }

    async def cleanup_expired(self) -> int:
        """만료된 엔트리 정리"""
        async with self._lock:
            expired_keys = []
            current_time = time.time()

            for key, entry in self.cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache[key]

            return len(expired_keys)

    async def start_cleanup_task(self) -> None:
        """주기적 정리 작업 시작"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_expired()

        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        """정리 작업 중지"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    def _calculate_hit_rate(self) -> float:
        """캐시 히트율 계산"""
        if self.stats["total_requests"] == 0:
            return 0.0
        return self.stats["hits"] / self.stats["total_requests"]

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        return {
            **self.stats,
            "hit_rate": self._calculate_hit_rate(),
            "cache_size": len(self.cache),
            "max_size": self.max_size
        }

    def get_hot_queries(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """자주 사용되는 쿼리 반환"""
        sorted_entries = sorted(
            self.cache.values(),
            key=lambda x: x.hit_count,
            reverse=True
        )

        return [
            {
                "query": entry.query,
                "hit_count": entry.hit_count,
                "last_accessed": datetime.fromtimestamp(entry.last_accessed).isoformat()
            }
            for entry in sorted_entries[:top_n]
        ]

# 전역 캐시 인스턴스
context_cache = ContextCache()

# 캐시 데코레이터
def cache_context(ttl: Optional[int] = None):
    """컨텍스트 캐싱 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 첫 번째 인자 추출 (query 또는 keywords)
            cache_key = None
            if args:
                if len(args) >= 2:  # self, query 형태
                    cache_key = args[1]
                elif len(args) >= 1:  # query만 있는 경우
                    cache_key = args[0]

            # cache_key가 리스트인 경우 문자열로 변환
            if isinstance(cache_key, list):
                cache_key = " ".join(str(item) for item in cache_key)
            elif not isinstance(cache_key, str):
                cache_key = str(cache_key) if cache_key else "default"

            # 캐시 체크
            cache_params = kwargs.get("cache_params", {})
            try:
                cached_result = await context_cache.get(cache_key, cache_params)

                if cached_result:
                    context, metadata = cached_result
                    return context, metadata
            except Exception as e:
                print(f"[WARNING] 캐시 조회 실패: {e}")

            # 캐시 미스: 실제 함수 실행
            result = await func(*args, **kwargs)

            # 결과 캐싱 (에러 방지)
            try:
                if result:
                    # 다양한 반환 형태 처리
                    if isinstance(result, tuple) and len(result) >= 2:
                        # (list, dict) 형태
                        if isinstance(result[0], list) and isinstance(result[1], dict):
                            context, metadata = result[0], result[1]
                        # (list, float, str) 형태
                        elif isinstance(result[0], list):
                            context = result[0]
                            metadata = {"source": "search_result"}
                        # 기타 형태
                        else:
                            context = [str(result)]
                            metadata = {"source": "generic"}
                    elif isinstance(result, str):
                        # 문자열 결과 (키워드 등)
                        context = [result]
                        metadata = {"source": "keyword_extraction"}
                    else:
                        # 기타 결과
                        context = [str(result)]
                        metadata = {"source": "unknown"}

                    await context_cache.set(
                        query=cache_key,
                        context=context,
                        metadata=metadata,
                        params=cache_params,
                        ttl=ttl
                    )
            except Exception as e:
                print(f"[WARNING] 캐시 저장 실패: {e}")
                # Debug 정보 추가
                print(f"[DEBUG] 캐시 저장 실패 - 결과 타입: {type(result)}, 내용: {str(result)[:100]}")

            return result

        return wrapper
    return decorator