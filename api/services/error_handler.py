"""
고급 오류 처리 및 복구 메커니즘
Circuit Breaker, Retry Logic, Graceful Degradation 포함
"""
import time
import asyncio
from typing import Any, Dict, Optional, List, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from api.logging import setup_logging
logger = setup_logging()
import threading

class ServiceStatus(Enum):
    """서비스 상태"""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    FAILED = "failed"
    MAINTENANCE = "maintenance"

@dataclass
class ErrorRecord:
    """오류 기록"""
    timestamp: float
    error_type: str
    error_message: str
    service: str
    severity: str = "ERROR"
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ServiceHealth:
    """서비스 상태 정보"""
    status: ServiceStatus
    error_count: int = 0
    last_error_time: Optional[float] = None
    success_count: int = 0
    last_success_time: Optional[float] = None
    circuit_open: bool = False
    circuit_open_time: Optional[float] = None

class CircuitBreaker:
    """서킷 브레이커 구현"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs):
        """서킷 브레이커를 통한 함수 호출"""
        with self._lock:
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
    
    async def acall(self, func: Callable, *args, **kwargs):
        """비동기 함수용 서킷 브레이커"""
        with self._lock:
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """리셋 시도 여부 확인"""
        return (
            self.last_failure_time and 
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """성공 시 처리"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """실패 시 처리"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class RetryHandler:
    """재시도 처리기"""
    
    @staticmethod
    def exponential_backoff(
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exceptions: tuple = (Exception,)
    ):
        """지수 백오프 재시도 데코레이터"""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        
                        if attempt == max_retries:
                            break
                            
                        # 지수 백오프 계산
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        print(f"[WARNING] Retry {attempt + 1}/{max_retries} for {func.__name__} after {delay}s: {e}")
                        
                        await asyncio.sleep(delay)
                
                raise last_exception
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        
                        if attempt == max_retries:
                            break
                            
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        print(f"[WARNING] Retry {attempt + 1}/{max_retries} for {func.__name__} after {delay}s: {e}")
                        
                        time.sleep(delay)
                
                raise last_exception
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator

class ErrorHandler:
    """종합 오류 처리기"""
    
    def __init__(self):
        self.error_history: List[ErrorRecord] = []
        self.service_health: Dict[str, ServiceHealth] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
        
        # 기본 서비스들
        self._initialize_services()
    
    def _initialize_services(self):
        """기본 서비스들 초기화"""
        services = [
            "opensearch", "neo4j", "stock_api", 
            "llm_service", "insight_generator", "keyword_extractor"
        ]
        
        for service in services:
            self.service_health[service] = ServiceHealth(ServiceStatus.HEALTHY)
            self.circuit_breakers[service] = CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=30.0
            )
    
    def record_error(
        self,
        service: str,
        error: Exception,
        severity: str = "ERROR",
        context: Optional[Dict[str, Any]] = None
    ):
        """오류 기록"""
        current_time = time.time()
        context = context or {}
        
        error_record = ErrorRecord(
            timestamp=current_time,
            error_type=type(error).__name__,
            error_message=str(error),
            service=service,
            severity=severity,
            context=context
        )
        
        with self._lock:
            self.error_history.append(error_record)
            
            # 최근 1000개만 유지
            if len(self.error_history) > 1000:
                self.error_history.pop(0)
            
            # 서비스 상태 업데이트
            if service in self.service_health:
                health = self.service_health[service]
                health.error_count += 1
                health.last_error_time = current_time
                
                # 상태 평가
                if health.error_count >= 10:
                    health.status = ServiceStatus.FAILED
                elif health.error_count >= 3:
                    health.status = ServiceStatus.DEGRADED
        
        # print(f"[ERROR] [{service}] {severity}: {error} | Context: {context}")
    
    def record_success(self, service: str):
        """성공 기록"""
        current_time = time.time()
        
        with self._lock:
            if service in self.service_health:
                health = self.service_health[service]
                health.success_count += 1
                health.last_success_time = current_time
                
                # 연속 성공으로 상태 회복
                if health.success_count >= 3:
                    health.error_count = max(0, health.error_count - 1)
                    
                    if health.error_count == 0:
                        health.status = ServiceStatus.HEALTHY
                        health.circuit_open = False
    
    def get_service_status(self, service: str) -> ServiceStatus:
        """서비스 상태 조회"""
        with self._lock:
            return self.service_health.get(service, ServiceHealth(ServiceStatus.HEALTHY)).status
    
    def is_service_available(self, service: str) -> bool:
        """서비스 사용 가능 여부"""
        status = self.get_service_status(service)
        return status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]
    
    def get_fallback_data(self, service: str, query: str) -> Optional[Dict[str, Any]]:
        """폴백 데이터 제공"""
        fallback_responses = {
            "opensearch": {
                "hits": [],
                "fallback_message": "뉴스 검색 서비스가 일시적으로 사용할 수 없습니다. 일반적인 시장 동향을 참고하세요."
            },
            "neo4j": {
                "rows": [],
                "fallback_message": "그래프 데이터 서비스가 일시적으로 사용할 수 없습니다."
            },
            "stock_api": {
                "price": None,
                "fallback_message": "주가 정보 서비스가 일시적으로 사용할 수 없습니다. 실시간 시세를 별도 확인하세요."
            },
            "llm_service": {
                "insights": [],
                "fallback_message": "AI 분석 서비스가 일시적으로 사용할 수 없어 기본 분석을 제공합니다."
            }
        }
        
        return fallback_responses.get(service, {
            "fallback_message": f"{service} 서비스가 일시적으로 사용할 수 없습니다."
        })
    
    def with_error_handling(
        self,
        service: str,
        fallback_value: Any = None,
        use_circuit_breaker: bool = True
    ):
        """오류 처리 데코레이터"""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    if use_circuit_breaker:
                        circuit_breaker = self.circuit_breakers.get(service)
                        if circuit_breaker:
                            result = await circuit_breaker.acall(func, *args, **kwargs)
                        else:
                            result = await func(*args, **kwargs)
                    else:
                        result = await func(*args, **kwargs)
                    
                    self.record_success(service)
                    return result
                    
                except Exception as e:
                    self.record_error(service, e, context={"args": args, "kwargs": kwargs})
                    
                    if fallback_value is not None:
                        print(f"[WARNING] Using fallback for {service}: {fallback_value}")
                        return fallback_value
                    
                    # 폴백 데이터 시도
                    query = kwargs.get("query", args[0] if args else "")
                    fallback_data = self.get_fallback_data(service, query)
                    if fallback_data:
                        return fallback_data
                    
                    raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    if use_circuit_breaker:
                        circuit_breaker = self.circuit_breakers.get(service)
                        if circuit_breaker:
                            result = circuit_breaker.call(func, *args, **kwargs)
                        else:
                            result = func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    self.record_success(service)
                    return result
                    
                except Exception as e:
                    self.record_error(service, e, context={"args": args, "kwargs": kwargs})
                    
                    if fallback_value is not None:
                        print(f"[WARNING] Using fallback for {service}: {fallback_value}")
                        return fallback_value
                    
                    query = kwargs.get("query", args[0] if args else "")
                    fallback_data = self.get_fallback_data(service, query)
                    if fallback_data:
                        return fallback_data
                    
                    raise
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def get_health_report(self) -> Dict[str, Any]:
        """전체 상태 보고서"""
        with self._lock:
            recent_errors = [
                error for error in self.error_history 
                if time.time() - error.timestamp < 3600  # 최근 1시간
            ]
            
            service_statuses = {
                service: {
                    "status": health.status.value,
                    "error_count": health.error_count,
                    "success_count": health.success_count,
                    "circuit_open": health.circuit_open,
                    "last_error": health.last_error_time,
                    "last_success": health.last_success_time
                }
                for service, health in self.service_health.items()
            }
            
            return {
                "overall_status": self._calculate_overall_status(),
                "services": service_statuses,
                "recent_errors": len(recent_errors),
                "total_errors": len(self.error_history),
                "error_rate": self._calculate_error_rate()
            }
    
    def _calculate_overall_status(self) -> str:
        """전체 시스템 상태 계산"""
        statuses = [health.status for health in self.service_health.values()]
        
        if any(s == ServiceStatus.FAILED for s in statuses):
            return "DEGRADED"
        elif any(s == ServiceStatus.DEGRADED for s in statuses):
            return "PARTIAL"
        else:
            return "HEALTHY"
    
    def _calculate_error_rate(self) -> float:
        """최근 1시간 오류율 계산"""
        current_time = time.time()
        recent_errors = [
            error for error in self.error_history 
            if current_time - error.timestamp < 3600
        ]
        
        # 간단한 오류율 계산 (시간당 오류 수)
        return len(recent_errors)

# 전역 오류 처리기
error_handler = ErrorHandler()

# 편의 함수들
def with_retry(max_retries: int = 3, exceptions: tuple = (Exception,)):
    """재시도 데코레이터 편의 함수"""
    return RetryHandler.exponential_backoff(max_retries=max_retries, exceptions=exceptions)

def with_error_handling(service: str, fallback_value: Any = None):
    """오류 처리 데코레이터 편의 함수"""
    return error_handler.with_error_handling(service, fallback_value)

def get_system_health() -> Dict[str, Any]:
    """시스템 상태 조회"""
    return error_handler.get_health_report()