# Ontology Chat FastAPI-MCP 통합

## 개요
기존 FastAPI 애플리케이션에 `fastapi-mcp` 패키지를 사용하여 MCP(Model Context Protocol) 지원을 추가했습니다. 이 방식은 별도의 MCP 서버를 만들 필요 없이 기존 REST API를 그대로 사용하면서 MCP 도구로도 활용할 수 있습니다.

## 장점
1. **기존 코드 재사용**: 기존 FastAPI 엔드포인트를 그대로 사용
2. **자동 변환**: REST API가 자동으로 MCP 도구로 변환됨
3. **중복 제거**: 별도의 MCP 서버 구현이 불필요
4. **동시 사용**: REST API와 MCP를 동시에 지원

## 설치 및 설정

### 1. 패키지 설치
```bash
pip install fastapi-mcp
```

### 2. FastAPI 앱에 MCP 통합
```python
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

app = FastAPI(title="ontology_chat", version="0.1.0")

# MCP 통합
mcp = FastApiMCP(
    fastapi=app,
    name="ontology-chat",
    description="Ontology Chat API with MCP support"
)
```

### 3. 엔드포인트는 자동으로 MCP 도구가 됨
기존 FastAPI 엔드포인트들이 자동으로 MCP 도구로 변환됩니다:

```python
@app.post("/chat")
async def chat(query: str = Body(..., embed=True)):
    """온톨로지 기반 챗봇과 대화합니다."""
    # 이 엔드포인트가 자동으로 MCP 도구가 됩니다.
    return await chat_service.generate_answer(query)
```

## 실행 방법

### 1. FastAPI-MCP 서버 실행
```bash
./run_fastapi_mcp.sh
```

또는 직접:
```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Claude Desktop 설정

Claude Desktop 설정 파일에 다음을 추가:

```json
{
  "mcpServers": {
    "ontology-chat": {
      "command": "uvicorn",
      "args": [
        "api.main:app",
        "--host", "127.0.0.1",
        "--port", "8000"
      ],
      "env": {
        "PYTHONPATH": "/path/to/ontology_chat"
      }
    }
  }
}
```

## 자동 변환되는 API 엔드포인트들

fastapi-mcp는 다음 엔드포인트들을 자동으로 MCP 도구로 변환합니다:

### 1. 챗봇 대화
- **엔드포인트**: `POST /chat`
- **MCP 도구명**: `chat`
- **기능**: 온톨로지 기반 질의응답

### 2. 리포트 생성
- **엔드포인트**: `POST /report`
- **MCP 도구명**: `create_report`
- **기능**: 도메인별 분석 리포트 생성

### 3. 비교 분석 리포트
- **엔드포인트**: `POST /report/comparative`
- **MCP 도구명**: `create_comparative_report`
- **기능**: 여러 키워드 비교 분석

### 4. 시장 테마 조회
- **엔드포인트**: `GET /api/themes`
- **MCP 도구명**: `get_market_themes`
- **기능**: 시장 주요 테마 목록 조회

### 5. 종목 검색
- **엔드포인트**: `GET /api/stocks/search`
- **MCP 도구명**: `search_stocks`
- **기능**: 종목명/심볼로 종목 검색

### 6. 기타 모든 API 엔드포인트
기존의 모든 FastAPI 엔드포인트가 자동으로 MCP 도구로 변환됩니다.

## 사용 예시

Claude Desktop에서 MCP가 설정되면 다음과 같이 사용할 수 있습니다:

```
"삼성전자의 최근 동향을 분석해줘"
→ chat 도구 자동 호출

"AI 반도체와 배터리 산업을 비교 분석해줘"
→ create_comparative_report 도구 자동 호출

"현재 인기 있는 시장 테마를 보여줘"
→ get_market_themes 도구 자동 호출

"삼성 관련 종목들을 찾아줘"
→ search_stocks 도구 자동 호출
```

## 기술적 장점

### 1. 코드 중복 없음
- 기존 REST API 코드를 그대로 사용
- MCP 전용 코드 작성 불필요

### 2. 자동 스키마 생성
- FastAPI의 OpenAPI 스키마를 활용
- 입력/출력 스키마 자동 생성

### 3. 타입 안정성
- Pydantic 모델 기반 타입 검증
- 자동 문서 생성

### 4. 확장성
- 새로운 FastAPI 엔드포인트 추가 시 자동으로 MCP 도구가 됨
- 설정 변경 없이 기능 확장

## 비교: 독립 MCP 서버 vs FastAPI-MCP

| 특징 | 독립 MCP 서버 | FastAPI-MCP |
|------|-------------|-------------|
| 코드 중복 | 있음 | 없음 |
| 유지보수 | 복잡 | 간단 |
| 성능 | 좋음 | 좋음 |
| 기능 확장 | 수동 | 자동 |
| 설정 복잡도 | 높음 | 낮음 |

## 문제 해결

### MCP 도구가 인식되지 않을 때
1. FastAPI 서버가 정상 실행 중인지 확인
2. Claude Desktop 설정에서 올바른 포트(8000) 사용 확인
3. 환경 변수 설정 확인

### API 호출 오류
1. 데이터베이스 연결 상태 확인 (Neo4j, OpenSearch)
2. API 키 설정 확인 (OpenAI)
3. 로그 파일에서 오류 메시지 확인

## 개발자 정보

### 새로운 API 추가
새로운 FastAPI 엔드포인트를 추가하면 자동으로 MCP 도구가 됩니다:

```python
@app.post("/new-feature")
async def new_feature(data: SomeModel):
    """새로운 기능 설명"""
    # 구현
    return result
```

### MCP 도구 제외
특정 엔드포인트를 MCP 도구에서 제외하려면 `FastApiMCP` 설정에서 제외할 수 있습니다.

### 로그 확인
```bash
# FastAPI 로그
tail -f logs/fastapi.log

# MCP 관련 로그
tail -f ~/.claude/logs/
```

## 권장사항

1. **기존 FastAPI 앱이 있는 경우**: `fastapi-mcp` 사용 (현재 구현)
2. **MCP 전용 서버가 필요한 경우**: 독립 MCP 서버 사용
3. **프로토타이핑**: `fastapi-mcp`로 빠른 구현 후 필요시 독립 서버로 전환

이 구현을 통해 기존 FastAPI 애플리케이션을 최소한의 변경으로 MCP 지원 서비스로 변환할 수 있습니다.