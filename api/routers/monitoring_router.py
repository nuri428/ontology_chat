"""
모니터링 라우터
Prometheus 메트릭 엔드포인트 및 헬스체크 제공
"""

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from typing import Dict, Any
import logging
import time
import psutil
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.get("/metrics")
async def get_metrics():
    """Prometheus 메트릭 엔드포인트"""
    try:
        # Prometheus 메트릭 생성
        metrics_data = generate_latest()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"메트릭 생성 실패: {e}")
        return Response(content="", media_type=CONTENT_TYPE_LATEST, status_code=500)

@router.get("/health/detailed")
async def get_detailed_health() -> Dict[str, Any]:
    """상세 헬스 체크"""
    try:
        # 시스템 정보
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # 프로세스 정보
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()

        health_info = {
            "status": "healthy",
            "timestamp": time.time(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                }
            },
            "process": {
                "pid": process.pid,
                "memory_rss": process_memory.rss,
                "memory_vms": process_memory.vms,
                "cpu_percent": process.cpu_percent(),
                "create_time": process.create_time()
            },
            "services": {
                "langfuse_tracing": _check_langfuse_connection(),
                "prometheus_available": _check_prometheus_available()
            }
        }

        return health_info

    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e)
        }

@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """애플리케이션 통계"""
    try:
        from api.monitoring.metrics_collector import query_metrics, session_manager

        stats = {
            "timestamp": time.time(),
            "active_queries": query_metrics.active_queries._value.get(),
            "active_sessions": len(session_manager.active_sessions),
            "session_details": [
                {
                    "session_id": sid,
                    "user_id": info["user_id"],
                    "duration": time.time() - info["start_time"],
                    "queries": info["queries"]
                }
                for sid, info in session_manager.active_sessions.items()
            ]
        }

        return stats

    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        return {
            "timestamp": time.time(),
            "error": str(e)
        }

@router.post("/sessions/{user_id}")
async def start_session(user_id: str) -> Dict[str, Any]:
    """세션 시작"""
    try:
        from api.monitoring.metrics_collector import session_manager

        session_id = session_manager.start_session(user_id)

        return {
            "session_id": session_id,
            "user_id": user_id,
            "start_time": time.time(),
            "status": "started"
        }

    except Exception as e:
        logger.error(f"세션 시작 실패: {e}")
        return {
            "error": str(e),
            "status": "failed"
        }

@router.delete("/sessions/{session_id}")
async def end_session(session_id: str) -> Dict[str, Any]:
    """세션 종료"""
    try:
        from api.monitoring.metrics_collector import session_manager

        session_manager.end_session(session_id)

        return {
            "session_id": session_id,
            "end_time": time.time(),
            "status": "ended"
        }

    except Exception as e:
        logger.error(f"세션 종료 실패: {e}")
        return {
            "error": str(e),
            "status": "failed"
        }

def _check_langfuse_connection() -> bool:
    """Langfuse 연결 상태 확인"""
    try:
        from api.utils.langfuse_tracer import tracer
        return tracer.is_enabled
    except:
        return False

def _check_prometheus_available() -> bool:
    """Prometheus 메트릭 시스템 사용 가능 여부 확인"""
    try:
        from api.monitoring.metrics_collector import MONITORING_AVAILABLE
        return MONITORING_AVAILABLE
    except:
        return False