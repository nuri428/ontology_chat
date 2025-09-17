"""
고성능 캐싱 및 성능 최적화 시스템
메모리 캐시, TTL 관리, 병렬 처리 최적화 포함
"""
import time
import hashlib
import asyncio
from typing import Any, Dict, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict
from api.logging import setup_logging
logger = setup_logging()
import threading
from functools import wraps

@dataclass
class CacheEntry:
    """캐시 엔트리"""
    data: Any
    timestamp: float
    ttl: float
    hit_count: int = 0
    last_access: float = field(default_factory=time.time)
    size_bytes: int = 0

@dataclass 
class CacheStats:
    """캐시 통계"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    average_response_time_ms: float = 0.0
    
    @property
    def hit_ratio(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

class AdvancedCacheManager:
    """고급 캐싱 관리자 - LRU, TTL, 크기 제한 지원"""
    
    def __init__(
        self, 
        max_size: int = 1000,
        default_ttl: float = 300.0,  # 5분
        max_memory_mb: int = 100
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()
        self._ttl_configs: Dict[str, float] = {}
        self._response_times: List[float] = []
        
        # 카테고리별 TTL 설정
        self._setup_category_ttls()
        
        # 백그라운드 정리 작업 시작
        self._cleanup_task = None
        self._start_cleanup_task()
        
    def _setup_category_ttls(self):
        """카테고리별 TTL 설정"""
        self._ttl_configs.update({
            "news_search": 180.0,    # 3분 - 뉴스는 빈번히 변경
            "graph_query": 600.0,    # 10분 - 그래프는 상대적으로 안정
            "stock_price": 60.0,     # 1분 - 주가는 실시간
            "insight_generation": 1800.0,  # 30분 - 인사이트는 재사용 가능
            "keyword_extraction": 3600.0,  # 1시간 - 키워드는 안정적
            "search_strategy": 900.0,      # 15분 - 검색 전략
            "entity_analysis": 1200.0      # 20분 - 엔티티 분석
        })
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """캐시 키 생성"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _estimate_size(self, data: Any) -> int:
        """데이터 크기 추정 (바이트)"""
        try:
            if isinstance(data, str):
                return len(data.encode('utf-8'))
            elif isinstance(data, (list, dict)):
                import sys
                return sys.getsizeof(data)
            else:
                import pickle
                return len(pickle.dumps(data))
        except:
            return 1024  # 기본 추정치
    
    def _should_evict(self) -> bool:
        """캐시 정리가 필요한지 확인"""
        return (
            len(self._cache) >= self.max_size or 
            self._stats.total_size_bytes >= self.max_memory_bytes
        )
    
    def _evict_entries(self):
        """캐시 엔트리 정리"""
        current_time = time.time()
        evicted_count = 0
        
        # 1. 만료된 엔트리 제거
        expired_keys = []
        for key, entry in self._cache.items():
            if current_time > entry.timestamp + entry.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            entry = self._cache.pop(key)
            self._stats.total_size_bytes -= entry.size_bytes
            evicted_count += 1
        
        # 2. 크기/메모리 제한 초과 시 LRU 정리
        while self._should_evict() and len(self._cache) > 0:
            # 가장 오래된 항목 제거 (OrderedDict의 FIFO 특성 이용)
            key, entry = self._cache.popitem(last=False)
            self._stats.total_size_bytes -= entry.size_bytes
            evicted_count += 1
        
        if evicted_count > 0:
            self._stats.evictions += evicted_count
            print(f"[DEBUG] 캐시 정리 완료: {evicted_count}개 엔트리 제거")
    
    def get(self, prefix: str, *args, **kwargs) -> Optional[Any]:
        """캐시에서 데이터 조회"""
        key = self._generate_cache_key(prefix, *args, **kwargs)
        current_time = time.time()
        
        with self._lock:
            self._stats.total_requests += 1
            
            entry = self._cache.get(key)
            if entry is None:
                self._stats.cache_misses += 1
                return None
            
            # TTL 확인
            if current_time > entry.timestamp + entry.ttl:
                # 만료된 엔트리 제거
                self._cache.pop(key)
                self._stats.total_size_bytes -= entry.size_bytes
                self._stats.cache_misses += 1
                return None
            
            # 히트 업데이트
            entry.hit_count += 1
            entry.last_access = current_time
            self._stats.cache_hits += 1
            
            # LRU 업데이트 (맨 뒤로 이동)
            self._cache.move_to_end(key)
            
            print(f"[DEBUG] 캐시 히트: {prefix} (히트율: {self._stats.hit_ratio:.1%})")
            return entry.data
    
    def set(
        self, 
        prefix: str, 
        data: Any, 
        ttl: Optional[float] = None, 
        *args, 
        **kwargs
    ):
        """캐시에 데이터 저장"""
        key = self._generate_cache_key(prefix, *args, **kwargs)
        current_time = time.time()
        
        # TTL 결정
        if ttl is None:
            ttl = self._ttl_configs.get(prefix, self.default_ttl)
        
        # 데이터 크기 추정
        size_bytes = self._estimate_size(data)
        
        with self._lock:
            # 기존 엔트리가 있다면 크기 업데이트
            if key in self._cache:
                old_entry = self._cache[key]
                self._stats.total_size_bytes -= old_entry.size_bytes
            
            # 새 엔트리 생성
            entry = CacheEntry(
                data=data,
                timestamp=current_time,
                ttl=ttl,
                size_bytes=size_bytes
            )
            
            self._cache[key] = entry
            self._stats.total_size_bytes += size_bytes
            
            # 캐시 정리 필요 시 실행
            if self._should_evict():
                self._evict_entries()
            
            print(f"[DEBUG] 캐시 저장: {prefix} (TTL: {ttl}초, 크기: {size_bytes}바이트)")
    
    def invalidate(self, prefix: str, *args, **kwargs):
        """특정 캐시 엔트리 무효화"""
        key = self._generate_cache_key(prefix, *args, **kwargs)
        
        with self._lock:
            entry = self._cache.pop(key, None)
            if entry:
                self._stats.total_size_bytes -= entry.size_bytes
                print(f"[DEBUG] 캐시 무효화: {prefix}")
    
    def invalidate_pattern(self, pattern: str):
        """패턴 매칭으로 캐시 무효화"""
        with self._lock:
            keys_to_remove = []
            for key in self._cache.keys():
                if pattern in key:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                entry = self._cache.pop(key)
                self._stats.total_size_bytes -= entry.size_bytes
            
            if keys_to_remove:
                print(f"[DEBUG] 패턴 매칭 캐시 무효화: {pattern} ({len(keys_to_remove)}개)")
    
    def clear(self):
        """전체 캐시 삭제"""
        with self._lock:
            self._cache.clear()
            self._stats = CacheStats()
            print(f"[INFO] 전체 캐시 삭제 완료")
    
    def get_stats(self) -> CacheStats:
        """캐시 통계 반환"""
        with self._lock:
            # 평균 응답시간 계산
            if self._response_times:
                avg_time = sum(self._response_times) / len(self._response_times)
                self._stats.average_response_time_ms = avg_time
            
            return CacheStats(
                total_requests=self._stats.total_requests,
                cache_hits=self._stats.cache_hits,
                cache_misses=self._stats.cache_misses,
                evictions=self._stats.evictions,
                total_size_bytes=self._stats.total_size_bytes,
                average_response_time_ms=self._stats.average_response_time_ms
            )
    
    def record_response_time(self, time_ms: float):
        """응답 시간 기록"""
        with self._lock:
            self._response_times.append(time_ms)
            # 최근 100개만 유지
            if len(self._response_times) > 100:
                self._response_times.pop(0)
    
    def _start_cleanup_task(self):
        """백그라운드 정리 작업 시작"""
        def cleanup_worker():
            while True:
                time.sleep(60)  # 1분마다 실행
                try:
                    with self._lock:
                        self._evict_entries()
                except Exception as e:
                    print(f"[ERROR] 캐시 정리 오류: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def __del__(self):
        """소멸자"""
        if self._cleanup_task:
            self._cleanup_task.cancel()

class CacheDecorator:
    """캐시 데코레이터"""
    
    def __init__(self, cache_manager: AdvancedCacheManager):
        self.cache_manager = cache_manager
    
    def cached(
        self, 
        prefix: str, 
        ttl: Optional[float] = None,
        include_args: bool = True,
        include_kwargs: bool = True
    ):
        """함수 결과 캐싱 데코레이터"""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # 캐시 키 생성용 인자 준비
                cache_args = args if include_args else ()
                cache_kwargs = kwargs if include_kwargs else {}
                
                # 캐시에서 조회
                cached_result = self.cache_manager.get(
                    prefix, *cache_args, **cache_kwargs
                )
                
                if cached_result is not None:
                    return cached_result
                
                # 캐시 미스 - 함수 실행
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    
                    # 응답 시간 기록
                    response_time = (time.time() - start_time) * 1000
                    self.cache_manager.record_response_time(response_time)
                    
                    # 캐시에 저장
                    self.cache_manager.set(
                        prefix, result, ttl, *cache_args, **cache_kwargs
                    )
                    
                    return result
                except Exception as e:
                    # 오류 시 응답 시간만 기록
                    response_time = (time.time() - start_time) * 1000
                    self.cache_manager.record_response_time(response_time)
                    raise
                    
            @wraps(func) 
            def sync_wrapper(*args, **kwargs):
                # 동기 함수용 래퍼
                cache_args = args if include_args else ()
                cache_kwargs = kwargs if include_kwargs else {}
                
                cached_result = self.cache_manager.get(
                    prefix, *cache_args, **cache_kwargs
                )
                
                if cached_result is not None:
                    return cached_result
                
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    
                    response_time = (time.time() - start_time) * 1000
                    self.cache_manager.record_response_time(response_time)
                    
                    self.cache_manager.set(
                        prefix, result, ttl, *cache_args, **cache_kwargs
                    )
                    
                    return result
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    self.cache_manager.record_response_time(response_time)
                    raise
            
            # 비동기 함수인지 확인
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator

# 전역 캐시 관리자 인스턴스
cache_manager = AdvancedCacheManager(
    max_size=2000,
    default_ttl=300.0,
    max_memory_mb=200
)

# 캐시 데코레이터 인스턴스
cache_decorator = CacheDecorator(cache_manager)

# 편의 함수들
def get_cache_stats() -> CacheStats:
    """캐시 통계 조회"""
    return cache_manager.get_stats()

def clear_cache():
    """전체 캐시 삭제"""
    cache_manager.clear()

def invalidate_cache_pattern(pattern: str):
    """패턴으로 캐시 무효화"""
    cache_manager.invalidate_pattern(pattern)