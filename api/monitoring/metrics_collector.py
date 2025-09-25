"""
Prometheus 메트릭 수집기
사용자 질의-응답 과정의 모든 단계를 추적하고 메트릭으로 기록
"""

import time
import asyncio
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, Gauge, Enum, Info
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Prometheus 메트릭 정의
class QueryMetrics:
    """질의 응답 관련 메트릭들"""

    def __init__(self):
        # 전체 질의 수
        self.total_queries = Counter(
            'ontology_total_queries',
            'Total number of user queries',
            ['intent', 'status', 'user_type']
        )

        # 응답 시간 분포
        self.response_time = Histogram(
            'ontology_response_time_seconds',
            'Query response time in seconds',
            ['intent', 'processing_stage'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )

        # 각 처리 단계별 시간
        self.stage_processing_time = Histogram(
            'ontology_stage_processing_seconds',
            'Processing time for each stage',
            ['stage', 'intent'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )

        # 검색 결과 수
        self.search_results_count = Histogram(
            'ontology_search_results_count',
            'Number of search results returned',
            ['search_type', 'intent'],
            buckets=[0, 1, 5, 10, 20, 50, 100]
        )

        # 캐시 히트/미스
        self.cache_operations = Counter(
            'ontology_cache_operations',
            'Cache hit/miss operations',
            ['operation', 'cache_type', 'stage']
        )

        # LLM 호출 추적
        self.llm_calls = Counter(
            'ontology_llm_calls_total',
            'Total LLM calls',
            ['model', 'operation', 'status']
        )

        # LLM 토큰 사용량
        self.llm_tokens = Counter(
            'ontology_llm_tokens_total',
            'Total tokens used',
            ['model', 'token_type']  # input/output
        )

        # 품질 점수
        self.quality_score = Gauge(
            'ontology_quality_score',
            'A-grade quality score',
            ['metric_type']
        )

        # 현재 진행 중인 질의 수
        self.active_queries = Gauge(
            'ontology_active_queries',
            'Number of currently processing queries'
        )

        # 오류 추적
        self.errors = Counter(
            'ontology_errors_total',
            'Total errors by type',
            ['error_type', 'stage', 'intent']
        )

        # 사용자 세션 정보
        self.user_sessions = Gauge(
            'ontology_active_user_sessions',
            'Number of active user sessions'
        )

        # 질의-응답 내용 로깅 (Info 메트릭으로 텍스트 데이터 저장)
        self.query_content = Info(
            'ontology_query_content',
            'Query and response content information',
            ['session_id', 'user_id', 'intent']
        )

# 전역 메트릭 인스턴스
query_metrics = QueryMetrics()

class QueryTracker:
    """개별 질의 추적기"""

    def __init__(self, query: str, user_id: str = "anonymous", session_id: str = None):
        self.query = query
        self.user_id = user_id
        self.session_id = session_id or f"session_{int(time.time())}"
        self.start_time = time.time()
        self.intent = "unknown"
        self.stages = {}
        self.search_results = {}
        self.llm_calls = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.quality_metrics = {}

        # 활성 질의 수 증가
        query_metrics.active_queries.inc()

        logger.info(f"[Query Tracker] 시작: {query[:50]}... (사용자: {user_id})")

    def set_intent(self, intent: str, confidence: float):
        """의도 분류 결과 기록"""
        self.intent = intent
        logger.debug(f"[Query Tracker] 의도 분류: {intent} (신뢰도: {confidence:.2f})")

    def start_stage(self, stage_name: str):
        """처리 단계 시작"""
        self.stages[stage_name] = {"start": time.time()}
        logger.debug(f"[Query Tracker] 단계 시작: {stage_name}")

    def end_stage(self, stage_name: str, metadata: Dict[str, Any] = None):
        """처리 단계 종료"""
        if stage_name in self.stages:
            duration = time.time() - self.stages[stage_name]["start"]
            self.stages[stage_name]["duration"] = duration
            self.stages[stage_name]["metadata"] = metadata or {}

            # 메트릭 기록
            query_metrics.stage_processing_time.labels(
                stage=stage_name,
                intent=self.intent
            ).observe(duration)

            logger.debug(f"[Query Tracker] 단계 완료: {stage_name} ({duration:.3f}s)")

    def record_search_results(self, search_type: str, count: int, results: List[Dict] = None):
        """검색 결과 기록"""
        self.search_results[search_type] = {
            "count": count,
            "results": results or []
        }

        # 메트릭 기록
        query_metrics.search_results_count.labels(
            search_type=search_type,
            intent=self.intent
        ).observe(count)

        logger.debug(f"[Query Tracker] 검색 결과: {search_type} - {count}건")

    def record_cache_operation(self, cache_type: str, operation: str, stage: str):
        """캐시 작업 기록"""
        if operation == "hit":
            self.cache_hits += 1
        elif operation == "miss":
            self.cache_misses += 1

        query_metrics.cache_operations.labels(
            operation=operation,
            cache_type=cache_type,
            stage=stage
        ).inc()

        logger.debug(f"[Query Tracker] 캐시 {operation}: {cache_type} @ {stage}")

    def record_llm_call(self, model: str, operation: str, tokens_input: int = 0,
                       tokens_output: int = 0, status: str = "success"):
        """LLM 호출 기록"""
        llm_call = {
            "model": model,
            "operation": operation,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "status": status,
            "timestamp": time.time()
        }
        self.llm_calls.append(llm_call)

        # 메트릭 기록
        query_metrics.llm_calls.labels(
            model=model,
            operation=operation,
            status=status
        ).inc()

        if tokens_input > 0:
            query_metrics.llm_tokens.labels(
                model=model,
                token_type="input"
            ).inc(tokens_input)

        if tokens_output > 0:
            query_metrics.llm_tokens.labels(
                model=model,
                token_type="output"
            ).inc(tokens_output)

        logger.debug(f"[Query Tracker] LLM 호출: {model} - {operation} ({status})")

    def record_error(self, error_type: str, stage: str, details: str = None):
        """오류 기록"""
        query_metrics.errors.labels(
            error_type=error_type,
            stage=stage,
            intent=self.intent
        ).inc()

        logger.warning(f"[Query Tracker] 오류: {error_type} @ {stage} - {details}")

    def record_quality_metrics(self, metrics: Dict[str, float]):
        """품질 메트릭 기록"""
        self.quality_metrics = metrics

        for metric_name, value in metrics.items():
            query_metrics.quality_score.labels(
                metric_type=metric_name
            ).set(value)

    def record_response(self, response_type: str, response_content: str, metadata: Dict[str, Any] = None):
        """응답 내용 기록"""
        self.response_type = response_type
        self.response_content = response_content[:1000]  # 처음 1000자만 저장
        self.response_metadata = metadata or {}

        # 구조화된 JSON 로그로 질의-응답 전체 내용 기록
        import json
        log_data = {
            "event_type": "query_response",
            "timestamp": int(time.time()),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "intent": self.intent,
            "query": self.query,
            "response_type": response_type,
            "response_content": response_content,
            "processing_time": round(time.time() - self.start_time, 2),
            "metadata": metadata or {}
        }

        # JSON 형태로 로그 출력 (Grafana에서 파싱 가능)
        logger.info(f"QUERY_RESPONSE_LOG: {json.dumps(log_data, ensure_ascii=False)}")

        # Info 메트릭으로도 기본 정보 저장 (대시보드용)
        try:
            query_metrics.query_content.labels(
                session_id=self.session_id[:50],
                user_id=self.user_id[:50],
                intent=self.intent
            ).info({
                'query_preview': self.query[:200],
                'response_type': response_type,
                'response_preview': response_content[:300],
                'processing_time': str(round(time.time() - self.start_time, 2)),
                'timestamp': str(int(time.time()))
            })
        except Exception as e:
            logger.error(f"[Query Tracker] 메트릭 기록 실패: {e}")

        logger.info(f"[Query Tracker] 응답 기록: {response_type} ({len(response_content)} chars)")

    def complete(self, status: str = "success", result_length: int = 0, final_response: Dict[str, Any] = None):
        """질의 처리 완료"""
        total_duration = time.time() - self.start_time

        # 응답 내용이 있으면 기록
        if final_response:
            response_type = final_response.get('type', 'unknown')
            response_markdown = final_response.get('markdown', '')
            self.record_response(response_type, response_markdown, final_response.get('meta', {}))

        # 사용자 타입 결정 (간단한 로직)
        user_type = "registered" if self.user_id != "anonymous" else "anonymous"

        # 전체 메트릭 기록
        query_metrics.total_queries.labels(
            intent=self.intent,
            status=status,
            user_type=user_type
        ).inc()

        query_metrics.response_time.labels(
            intent=self.intent,
            processing_stage="total"
        ).observe(total_duration)

        # 활성 질의 수 감소
        query_metrics.active_queries.dec()

        logger.info(f"[Query Tracker] 완료: {status} ({total_duration:.3f}s, 결과: {result_length}자)")

        # 요약 로그
        self._log_summary()

    def _log_summary(self):
        """처리 요약 로그"""
        summary = {
            "query": self.query[:100],
            "intent": self.intent,
            "total_time": time.time() - self.start_time,
            "stages": len(self.stages),
            "search_results": sum(r["count"] for r in self.search_results.values()),
            "llm_calls": len(self.llm_calls),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses
        }
        logger.info(f"[Query Summary] {summary}")

# 데코레이터
def track_query_processing(intent: str = None):
    """질의 처리 과정을 추적하는 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 추적기 생성 (첫 번째 인자가 질의라고 가정)
            query = kwargs.get('query') or (args[0] if args else "unknown")
            tracker = QueryTracker(str(query))

            if intent:
                tracker.set_intent(intent, 1.0)

            try:
                # 함수 실행 추적
                tracker.start_stage(func.__name__)
                result = await func(*args, **kwargs, _tracker=tracker)
                tracker.end_stage(func.__name__)
                tracker.complete("success", len(str(result)) if result else 0)
                return result

            except Exception as e:
                tracker.record_error(type(e).__name__, func.__name__, str(e))
                tracker.complete("error")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            query = kwargs.get('query') or (args[0] if args else "unknown")
            tracker = QueryTracker(str(query))

            if intent:
                tracker.set_intent(intent, 1.0)

            try:
                tracker.start_stage(func.__name__)
                result = func(*args, **kwargs, _tracker=tracker)
                tracker.end_stage(func.__name__)
                tracker.complete("success", len(str(result)) if result else 0)
                return result

            except Exception as e:
                tracker.record_error(type(e).__name__, func.__name__, str(e))
                tracker.complete("error")
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# 컨텍스트 매니저
class TrackingContext:
    """질의 추적 컨텍스트"""
    def __init__(self, tracker: QueryTracker):
        self.tracker = tracker
        self.response = None

    def set_response(self, response: Dict[str, Any]):
        """응답 설정"""
        self.response = response

    def __getattr__(self, name):
        """QueryTracker의 모든 메소드에 대한 프록시"""
        return getattr(self.tracker, name)

@asynccontextmanager
async def track_query(query: str, user_id: str = "anonymous", session_id: str = None):
    """질의 처리를 추적하는 컨텍스트 매니저"""
    tracker = QueryTracker(query, user_id, session_id)
    context = TrackingContext(tracker)
    try:
        yield context
        # 응답이 설정되었으면 함께 완료
        if context.response:
            tracker.complete("success", final_response=context.response)
        else:
            tracker.complete("success")
    except Exception as e:
        tracker.record_error(type(e).__name__, "context", str(e))
        tracker.complete("error")
        raise

# 세션 관리
class SessionManager:
    """사용자 세션 관리"""

    def __init__(self):
        self.active_sessions = {}

    def start_session(self, user_id: str, session_id: str = None):
        """세션 시작"""
        session_id = session_id or f"session_{user_id}_{int(time.time())}"
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "start_time": time.time(),
            "queries": 0
        }
        query_metrics.user_sessions.set(len(self.active_sessions))
        return session_id

    def record_query(self, session_id: str):
        """세션의 질의 수 증가"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["queries"] += 1

    def end_session(self, session_id: str):
        """세션 종료"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            query_metrics.user_sessions.set(len(self.active_sessions))

# 전역 세션 매니저
session_manager = SessionManager()