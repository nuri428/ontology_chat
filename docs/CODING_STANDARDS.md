# 온톨로지 채팅 시스템 코딩 표준

## 1. 파일 구조 규칙

### API 서비스 (`api/services/`)
- `chat_service.py`: 핵심 채팅 로직
- `context_*.py`: 컨텍스트 처리 모듈들
- 새 서비스는 기존 패턴 따라 생성

### 어댑터 (`api/adapters/`)
- MCP 프로토콜 어댑터만 허용
- 외부 라이브러리 래퍼 금지
- 직접 라이브러리 사용 원칙

## 2. 네이밍 규칙

### 함수명
```python
# ✅ 좋은 예
async def _get_context_keywords(self, query: str) -> str:
async def search_parallel(self, query: str, size: int = 5):

# ❌ 나쁜 예
async def func1(self, q):
async def doSomething(self, data):
```

### 변수명
```python
# ✅ 좋은 예
news_hits = []
semantic_score = 0.85
ollama_llm = OllamaLLM(...)

# ❌ 나쁜 예
data = []
score = 0.85
llm = OllamaLLM(...)
```

## 3. 비동기 처리 규칙

### 병렬 처리 필수 패턴
```python
# ✅ 올바른 병렬 처리
async def search_parallel(self, query: str):
    async def search_news():
        return await self._search_news(query)

    async def search_graph():
        return await self._query_graph(query)

    results = await asyncio.gather(
        search_news(),
        search_graph()
    )
```

### 타임아웃 설정 필수
```python
# ✅ 타임아웃 적용
try:
    result = await asyncio.wait_for(
        slow_operation(),
        timeout=2.0
    )
except asyncio.TimeoutError:
    # 폴백 처리
    result = fallback_result()
```

## 4. 에러 처리 규칙

### 예외 처리 패턴
```python
# ✅ 구체적 예외 처리
try:
    result = await external_service_call()
except asyncio.TimeoutError:
    print(f"[WARNING] 서비스 타임아웃, 폴백 사용")
    result = fallback_value
except Exception as e:
    print(f"[ERROR] 예상치 못한 오류: {e}")
    result = default_value
```

## 5. 성능 최적화 규칙

### 캐싱 적용
```python
# ✅ 캐시 데코레이터 사용
@cache_context(ttl=3600)
async def expensive_operation(self, query: str):
    # 무거운 작업
    return result
```

### 인스턴스 재사용
```python
# ✅ 기존 인스턴스 재사용
if self.ollama_llm:
    fast_llm = self.ollama_llm
    fast_llm.temperature = 0.0
else:
    fast_llm = OllamaLLM(...)
```

## 6. 품질 보증 규칙

### A급 품질 유지
- 모든 변경사항 후 `test_a_grade_performance.py` 실행
- 0.9 이상 점수 유지 필수
- 성능 회귀 시 즉시 롤백

### 로깅 규칙
```python
# ✅ 적절한 로깅
print(f"[DEBUG] 키워드 추출: {elapsed:.1f}ms")
print(f"[INFO] A급 점수: {score:.3f}")
print(f"[WARNING] 타임아웃, 폴백 사용")
print(f"[ERROR] 치명적 오류: {error}")
```

## 7. 금지 패턴

### ❌ 절대 하지 말 것
```python
# 기존 라이브러리 기능 중복 구현 (ollama_llm.py 케이스)
from langchain_ollama import OllamaLLM  # 이미 완전한 기능

class OllamaLLMAdapter:  # ❌ 불필요한 래퍼
    def __init__(self):
        self.llm = OllamaLLM(...)

    async def extract_keywords(self, text):
        # ❌ 기존 라이브러리로 충분한 기능을 다시 구현
        return await self.llm.ainvoke(f"Extract: {text}")

# ✅ 올바른 방법: 직접 사용
llm = OllamaLLM(...)
result = await llm.ainvoke(f"Extract: {text}")

# 불필요한 래퍼 클래스
class UnnecessaryWrapper:
    def __init__(self):
        self.client = ExternalLibrary()

# 동기 코드 (비동기 필수)
def sync_function():
    time.sleep(1)

# 하드코딩된 값
TIMEOUT = 5.0  # ❌
timeout = settings.get_timeout()  # ✅

# 예외 무시
try:
    risky_operation()
except:  # ❌ 모든 예외 무시
    pass
```

## 8. 기존 패키지 우선 원칙

### 🔍 새 기능 구현 전 체크리스트
```python
# 1. 기존 임포트 확인
# 현재 프로젝트에 이미 임포트된 패키지들 검토
# requirements.txt, pyproject.toml, 기존 import 문 확인

# 2. 라이브러리 기능 조사
# 기존 라이브러리의 문서나 API 확인
# 파라미터나 메서드로 요구사항 충족 가능한지 검토

# 3. 설정 조정으로 해결 시도
# 기존 인스턴스의 설정만 변경으로 목표 달성 가능한지 확인

# 4. 마지막 수단으로만 새 구현
# 정말 기존 라이브러리로 불가능한 경우에만 커스텀 클래스 생성
```

### 📋 ollama_llm.py 교훈
- ✅ `langchain_ollama.OllamaLLM` 이미 완벽한 기능 제공
- ❌ `OllamaLLMAdapter` 클래스는 단순 래핑만 함
- 🎯 **결론**: 367줄 제거, 42% 성능 향상

## 9. 필수 체크리스트

변경사항 적용 전 확인:
- [ ] **기존 임포트로 해결 가능한지 먼저 확인**
- [ ] **불필요한 래퍼 클래스 생성하지 않았는지 검토**
- [ ] A급 성능 테스트 통과
- [ ] 기존 기능 회귀 없음
- [ ] 적절한 에러 처리 포함
- [ ] 타임아웃 설정 적용
- [ ] 로깅 정보 추가
- [ ] 코드 중복 제거
- [ ] 주석 및 문서화 완료