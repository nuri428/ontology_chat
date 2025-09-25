# Langfuse LLM 트레이싱 가이드

## 개요
Langfuse를 사용하여 LLM 호출을 추적, 모니터링, 분석할 수 있습니다.

## 설정

### 1. 환경변수 설정
`.env` 파일에 다음 설정을 추가하세요:

```bash
# Langfuse 트레이싱 설정
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_HOST=https://your-langfuse-instance.com
```

### 2. Docker 환경에서 사용
Docker Compose가 이미 Langfuse 환경변수를 포함하도록 업데이트되었습니다:
- `docker-compose.dev.yml`
- `docker-compose.prod.yml`

## 적용된 트레이싱 지점

### 1. 챗 서비스 (`api/services/chat_service.py`)
- `_generate_llm_insights()`: 주식 인사이트 생성
- `_generate_answer_legacy()`: 레거시 답변 생성

### 2. 키워드 추출 (`api/utils/llm_keyword_extractor.py`)
- `extract_keywords()`: 동기 키워드 추출
- `extract_keywords_async()`: 비동기 키워드 추출

### 3. API 엔드포인트 (`api/main.py`)
- `/report/comparative`: 비교 분석 리포트
- `/report/langgraph/comparative`: LangGraph 비교 분석

## 사용법

### 자동 트레이싱
설정이 완료되면 다음 LLM 호출들이 자동으로 트레이싱됩니다:

```python
# 예시: 챗 서비스 사용
chat_service = ChatService()
result = await chat_service._generate_llm_insights(query, news, graph, stock)
```

### 수동 트레이싱
새로운 LLM 호출에 트레이싱을 적용하려면:

```python
from api.utils.langfuse_tracer import trace_llm, trace_analysis

@trace_llm("my_llm_function")
async def my_llm_call(prompt):
    return await llm.ainvoke(prompt)

@trace_analysis("sentiment_analysis")
def analyze_sentiment(text):
    return llm.invoke(f"Analyze sentiment: {text}")
```

## 모니터링 데이터

Langfuse에서 확인할 수 있는 정보:
- **트레이스**: 전체 LLM 호출 플로우
- **생성**: 개별 LLM 생성 과정
- **입력/출력**: 프롬프트와 응답 내용
- **메타데이터**: 모델 정보, 분석 타입 등
- **성능 지표**: 응답 시간, 토큰 사용량
- **오류 추적**: 실패한 LLM 호출들

## 비활성화
Langfuse 설정이 없거나 불완전하면 트레이싱이 자동으로 비활성화되어 기존 기능에 영향을 주지 않습니다.

## 트러블슈팅

### 1. 트레이싱이 작동하지 않을 때
```bash
# 환경변수 확인
echo $LANGFUSE_HOST
echo $LANGFUSE_PUBLIC_KEY

# 로그에서 Langfuse 초기화 메시지 확인
# "[Langfuse] 트레이싱 초기화 완료" 또는 "[Langfuse] 설정 누락으로 트레이싱 비활성화"
```

### 2. 성능 이슈
트레이싱으로 인한 성능 저하가 우려되는 경우:
- 프로덕션 환경에서 선택적으로 비활성화
- Langfuse 호스트의 응답 시간 확인

## 보안 고려사항
- `LANGFUSE_SECRET_KEY`는 절대 공개하지 마세요
- 프롬프트와 응답이 Langfuse 서버에 저장됩니다
- 민감한 데이터는 트레이싱에서 제외하거나 마스킹하세요