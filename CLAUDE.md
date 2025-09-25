# Claude Code Configuration

## ⚠️ 중요: Python 실행 방법 ⚠️

### 이 프로젝트는 반드시 다음 방법으로 실행:
1. **uv 사용**: `uv run python script.py`
2. **Docker 컨테이너 내부**: `docker exec -it container_name python script.py`

### ❌ 절대 하지 말아야 할 것:
- `python` 또는 `python3` 직접 실행 금지
- pyenv 환경에서 직접 실행 금지

## 프로젝트 규칙 (Project Rules)

### 1. 패키지 사용 원칙 (Package Usage Principles)

#### 기존 패키지 우선 사용
- **항상 기존 설치된 패키지를 먼저 확인하고 활용**
- 새로운 패키지 설치보다는 이미 존재하는 라이브러리의 기능을 최대한 활용
- 불필요한 래퍼(wrapper) 클래스나 중간 레이어 생성 금지
- **기존 임포트된 패키지로 해결 가능한 기능은 직접 구현하지 말 것**

#### 직접 사용 원칙
- `langchain_ollama.OllamaLLM` 같은 라이브러리는 직접 사용
- 추가 어댑터나 래퍼 클래스 생성하지 않음
- HTTP 클라이언트가 내장된 라이브러리는 별도 HTTP 호출 구현 금지
- **라이브러리의 기본 기능으로 충분한 경우 커스텀 구현 금지**

#### 중복 방지
- 같은 기능을 하는 코드의 중복 구현 방지
- 기존 인스턴스 재사용 우선 (성능 최적화)
- 동일한 라이브러리를 여러 방식으로 임포트하지 않음

### 2. 성능 최적화 원칙

#### 인스턴스 재사용
- 무거운 객체(LLM, 임베딩 모델 등)는 인스턴스 재사용
- 매번 새로운 인스턴스 생성보다는 기존 것 활용
- 설정만 필요시 동적으로 변경

#### 불필요한 레이어 제거
- 단순히 함수 호출을 감싸는 클래스 제거
- 값 추가 없는 중간 변환 과정 제거
- 직접적이고 명확한 코드 구조 선호

### 3. 코드 품질 원칙

#### 명확한 의존성 관리
- 실제 사용하는 라이브러리만 임포트
- 사용하지 않는 어댑터나 헬퍼 클래스 제거
- try-except를 통한 우아한 폴백 구현

#### 실용적 접근
- 이론적 완벽함보다는 실제 동작하는 코드 우선
- 과도한 추상화보다는 직관적이고 이해하기 쉬운 구조
- 성능과 유지보수성의 균형

## 핵심 원칙: "기존 것 먼저, 커스텀은 최후에"

### 🔍 **문제 해결 순서**
1. **기존 임포트 확인**: 이미 설치된 패키지로 해결 가능한지 확인
2. **라이브러리 문서 검토**: 내장 기능이나 파라미터로 요구사항 충족 가능한지 확인
3. **설정 조정**: 기존 인스턴스의 설정만 변경으로 해결 시도
4. **마지막 수단**: 정말 필요한 경우에만 새로운 클래스/함수 생성

### 🚫 **ollama_llm.py 케이스 분석**
```python
# ❌ 문제: langchain_ollama가 이미 있는데 래퍼 클래스 생성
from langchain_ollama import OllamaLLM  # 이미 완전한 기능 제공

class OllamaLLMAdapter:  # 불필요한 중복
    def __init__(self):
        self.llm = OllamaLLM(...)

    async def extract_keywords(self, text):
        # OllamaLLM.ainvoke()로 충분한 기능을 다시 래핑
        return await self.llm.ainvoke(f"Keywords: {text}")

# ✅ 해결: 기존 라이브러리 직접 활용
llm = OllamaLLM(model="llama3.1:8b", ...)
keywords = await llm.ainvoke(f"Keywords: {text}")
```

## 예시 (Examples)

### ❌ 나쁜 예 (Bad Example)
```python
# 불필요한 래퍼 클래스 (ollama_llm.py 케이스)
class OllamaLLMAdapter:
    def __init__(self):
        self.llm = OllamaLLM(...)  # 이미 존재하는 라이브러리

    async def extract_keywords(self, text):
        # 단순히 LLM 호출만 래핑 - 부가가치 없음
        return await self.llm.ainvoke(f"Extract keywords: {text}")

    async def analyze_query(self, query):
        # 기존 라이브러리로 충분한 기능을 다시 구현
        return await self.llm.ainvoke(f"Analyze: {query}")

# 사용
adapter = OllamaLLMAdapter()
result = await adapter.extract_keywords(query)
```

### ✅ 좋은 예 (Good Example)
```python
# 기존 라이브러리 직접 사용
llm = OllamaLLM(model="llama3.1:8b", base_url="...")

# 필요시 인스턴스 재사용 (성능 최적화)
async def extract_keywords(self, query):
    if self.ollama_llm:
        # 기존 인스턴스 활용 + 설정만 조정
        self.ollama_llm.temperature = 0.0
        return await self.ollama_llm.ainvoke(f"Extract keywords: {query}")

# 기존 라이브러리 기능 최대 활용
async def analyze_with_context(self, query, context):
    # 라이브러리의 내장 기능 활용
    prompt = f"Context: {context}\nQuery: {query}\nAnalysis:"
    return await self.ollama_llm.ainvoke(prompt)
```

## 기술 스택 정보 (Tech Stack)

### 현재 사용 중인 주요 패키지
- `langchain_ollama`: LLM 통합
- `sentence_transformers`: 임베딩 생성
- `opensearch-py`: 벡터 검색
- `neo4j`: 그래프 데이터베이스
- `fastapi`: API 서버
- `asyncio`: 비동기 처리

### 프로젝트 특화 모듈
- `api.services.chat_service`: 핵심 채팅 서비스
- `api.services.context_*`: 컨텍스트 처리 모듈들
- `api.adapters.mcp_*`: MCP 프로토콜 어댑터

## 성능 목표 (Performance Goals)

- **A급 품질**: 0.9+ 점수 유지
- **응답 속도**: 1.5초 이내
- **메모리 효율성**: 불필요한 객체 생성 최소화
- **캐시 활용**: 가능한 곳에 적절한 캐싱 적용

## 개발 철학 (Development Philosophy)

1. **실용주의**: 동작하는 코드를 우선으로, 과도한 엔지니어링 방지
2. **성능 우선**: 사용자 경험에 직접 영향을 주는 성능 최적화 우선
3. **단순함**: 복잡한 추상화보다는 직관적이고 이해하기 쉬운 코드
4. **재사용성**: 기존 자원과 코드의 최대한 활용