"""
Langfuse 트레이싱 유틸리티
LLM 호출에 대한 추적, 모니터링, 분석 제공
"""

import os
import asyncio
import functools
from typing import Optional, Dict, Any, Callable, Awaitable
import logging

# Langfuse 선택적 임포트
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    Langfuse = None
    LANGFUSE_AVAILABLE = False

logger = logging.getLogger(__name__)

class LangfuseTracer:
    """Langfuse 트레이싱 관리자"""

    def __init__(self):
        self.langfuse: Optional[Langfuse] = None
        self.is_enabled = False
        self._initialize()

    def _initialize(self):
        """Langfuse 초기화"""
        if not LANGFUSE_AVAILABLE:
            logger.info("[Langfuse] 모듈이 설치되지 않음 - 트레이싱 비활성화")
            self.is_enabled = False
            self.langfuse = None
            return

        try:
            from api.config import settings

            # 환경변수 또는 설정에서 Langfuse 설정 로드
            secret_key = settings.langfuse_secret_key or os.getenv("LANGFUSE_SECRET_KEY")
            public_key = settings.langfuse_public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
            host = settings.langfuse_host or os.getenv("LANGFUSE_HOST")

            if secret_key and public_key and host and Langfuse is not None:
                self.langfuse = Langfuse(
                    secret_key=secret_key,
                    public_key=public_key,
                    host=host
                )
                self.is_enabled = True
                logger.info("[Langfuse] 트레이싱 초기화 완료")
            else:
                logger.warning("[Langfuse] 설정 누락 또는 모듈 없음 - 트레이싱 비활성화")
                self.is_enabled = False
                self.langfuse = None

        except Exception as e:
            logger.error(f"[Langfuse] 초기화 실패: {e}")
            self.is_enabled = False
            self.langfuse = None

    def trace_llm_call(
        self,
        name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """LLM 호출 트레이싱 데코레이터"""
        def decorator(func: Callable):
            # 데코레이터 정의 시점이 아닌, 함수 호출 시점에 is_enabled를 체크
            # 따라서 여기서는 항상 wrapper를 반환
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    return await self._trace_async_call(
                        func, name, user_id, session_id, metadata, *args, **kwargs
                    )
                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    return self._trace_sync_call(
                        func, name, user_id, session_id, metadata, *args, **kwargs
                    )
                return sync_wrapper

        return decorator

    async def _trace_async_call(
        self,
        func: Callable[..., Awaitable[Any]],
        name: str,
        user_id: Optional[str],
        session_id: Optional[str],
        metadata: Optional[Dict[str, Any]],
        *args,
        **kwargs
    ):
        """비동기 LLM 호출 트레이싱"""
        if not self.is_enabled or self.langfuse is None:
            return await func(*args, **kwargs)

        # 트레이스 시작
        trace = self.langfuse.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )

        try:
            # 입력 파라미터 추출 (프롬프트 찾기)
            input_data = self._extract_input_data(*args, **kwargs)

            # LLM 호출 실행
            result = await func(*args, **kwargs)

            # 결과 기록
            trace.generation(
                name=f"{name}_generation",
                model=self._extract_model_info(*args, **kwargs),
                input=input_data,
                output=str(result) if result else None,
                metadata=metadata or {}
            )

            return result

        except Exception as e:
            # 오류 기록
            trace.update(
                output={"error": str(e)},
                metadata={**(metadata or {}), "error": True}
            )
            raise
        finally:
            # 트레이스 종료
            self.langfuse.flush()

    def _trace_sync_call(
        self,
        func: Callable,
        name: str,
        user_id: Optional[str],
        session_id: Optional[str],
        metadata: Optional[Dict[str, Any]],
        *args,
        **kwargs
    ):
        """동기 LLM 호출 트레이싱"""
        if not self.is_enabled or self.langfuse is None:
            return func(*args, **kwargs)

        # 트레이스 시작
        trace = self.langfuse.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )

        try:
            # 입력 파라미터 추출
            input_data = self._extract_input_data(*args, **kwargs)

            # LLM 호출 실행
            result = func(*args, **kwargs)

            # 결과 기록
            trace.generation(
                name=f"{name}_generation",
                model=self._extract_model_info(*args, **kwargs),
                input=input_data,
                output=str(result) if result else None,
                metadata=metadata or {}
            )

            return result

        except Exception as e:
            # 오류 기록
            trace.update(
                output={"error": str(e)},
                metadata={**(metadata or {}), "error": True}
            )
            raise
        finally:
            # 트레이스 종료
            self.langfuse.flush()

    def _extract_input_data(self, *args, **kwargs) -> Dict[str, Any]:
        """입력 데이터 추출 (프롬프트 등)"""
        input_data = {}

        # args에서 프롬프트 찾기
        for i, arg in enumerate(args):
            if isinstance(arg, str) and len(arg) > 10:  # 프롬프트로 추정
                input_data[f"prompt_{i}"] = arg
                break

        # kwargs에서 프롬프트 관련 데이터 찾기
        for key, value in kwargs.items():
            if key in ['prompt', 'input', 'query', 'text'] and isinstance(value, str):
                input_data[key] = value

        return input_data

    def _extract_model_info(self, *args, **kwargs) -> Optional[str]:
        """모델 정보 추출"""
        # self 객체에서 모델 정보 찾기
        if args and hasattr(args[0], 'model'):
            return getattr(args[0], 'model', None)
        if args and hasattr(args[0], 'model_name'):
            return getattr(args[0], 'model_name', None)
        if args and hasattr(args[0], 'ollama_model'):
            return getattr(args[0], 'ollama_model', None)

        return "unknown"

    def create_session(self, user_id: str, session_data: Optional[Dict[str, Any]] = None) -> str:
        """새로운 세션 생성"""
        if not self.is_enabled:
            return "session_disabled"

        trace = self.langfuse.trace(
            name="chat_session",
            user_id=user_id,
            metadata=session_data or {}
        )
        return trace.id

    def log_user_feedback(
        self,
        trace_id: str,
        score: float,
        comment: Optional[str] = None
    ):
        """사용자 피드백 기록"""
        if not self.is_enabled:
            return

        try:
            self.langfuse.score(
                trace_id=trace_id,
                name="user_feedback",
                value=score,
                comment=comment
            )
        except Exception as e:
            logger.error(f"[Langfuse] 피드백 기록 실패: {e}")

# 전역 트레이서 인스턴스
tracer = LangfuseTracer()

# 편의 데코레이터들
def trace_llm(name: str, **trace_kwargs):
    """LLM 호출 트레이싱 데코레이터"""
    return tracer.trace_llm_call(name=name, **trace_kwargs)

def trace_chat(user_id: str = "anonymous", session_id: Optional[str] = None):
    """채팅 트레이싱 데코레이터"""
    return tracer.trace_llm_call(
        name="chat_completion",
        user_id=user_id,
        session_id=session_id
    )

def trace_analysis(analysis_type: str):
    """분석 트레이싱 데코레이터"""
    return tracer.trace_llm_call(
        name=f"analysis_{analysis_type}",
        metadata={"analysis_type": analysis_type}
    )