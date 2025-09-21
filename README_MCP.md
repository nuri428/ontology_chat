# Ontology Chat MCP Server

## 개요
Ontology Chat API를 MCP(Model Context Protocol)로 제공하여 외부 애플리케이션(예: Claude Desktop, Cursor 등)에서 사용할 수 있도록 합니다.

## 설치

### 1. 의존성 설치
```bash
pip install mcp
# 또는
pip install -e .
```

### 2. 환경 변수 설정
`.env` 파일에 필요한 환경 변수를 설정합니다:
```bash
OPENAI_API_KEY=your_openai_api_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
# 기타 필요한 환경 변수들...
```

## MCP 서버 실행

### 직접 실행
```bash
python mcp_server.py
```

### Claude Desktop 설정

1. Claude Desktop 설정 파일을 엽니다:
   - Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/claude/claude_desktop_config.json`

2. 다음 설정을 추가합니다:
```json
{
  "mcpServers": {
    "ontology-chat": {
      "command": "python",
      "args": ["-u", "/path/to/ontology_chat/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/ontology_chat"
      }
    }
  }
}
```

## 사용 가능한 도구들

### 1. chat
온톨로지 기반 챗봇 대화
```
입력:
- query: 사용자 질문

출력:
- 답변 및 관련 정보
```

### 2. generate_report
도메인별 분석 리포트 생성
```
입력:
- query: 분석할 질의
- domain: 도메인 (optional)
- lookback_days: 분석 기간 (기본값: 180)
- news_size: 뉴스 검색 수 (기본값: 20)
- graph_limit: 그래프 검색 수 (기본값: 30)
- symbol: 종목 심볼 (optional)

출력:
- markdown: 마크다운 형식의 리포트
- metrics: 분석 메트릭
```

### 3. generate_comparative_report
여러 키워드 비교 분석
```
입력:
- queries: 비교할 질의들 (2-5개)
- domain: 도메인 (optional)
- lookback_days: 분석 기간 (기본값: 180)

출력:
- 비교 분석 결과
```

### 4. generate_trend_report
시계열 트렌드 분석
```
입력:
- query: 분석할 질의
- domain: 도메인 (optional)
- periods: 분석 기간들 (예: [30, 90, 180])

출력:
- 트렌드 분석 결과
```

### 5. generate_langgraph_report
LangGraph 기반 고급 분석
```
입력:
- query: 분석할 질의
- domain: 도메인 (optional)
- lookback_days: 분석 기간 (기본값: 180)
- analysis_depth: 분석 깊이 (shallow/standard/deep/comprehensive)
- symbol: 종목 심볼 (optional)

출력:
- 고급 분석 리포트
```

### 6. search_stocks
종목 검색
```
입력:
- query: 검색어
- limit: 결과 수 제한 (기본값: 10)

출력:
- 종목 목록
```

### 7. get_market_themes
시장 테마 조회
```
출력:
- 테마별 종목 정보
```

### 8. get_theme_stocks
특정 테마 종목 조회
```
입력:
- theme: 테마명

출력:
- 해당 테마의 종목 목록
```

### 9. get_top_stocks
상승률 상위 종목 조회
```
입력:
- theme: 테마명 (optional)

출력:
- 상위 종목 목록
```

### 10. generate_forecast_report
테마/종목별 전망 리포트
```
입력:
- query: 분석 질의
- keywords: 키워드 목록
- companies: 관련 기업 목록
- lookback_days: 분석 기간 (기본값: 30)
- include_news: 뉴스 포함 여부 (기본값: true)
- include_ontology: 온톨로지 포함 여부 (기본값: true)
- include_financial: 재무 정보 포함 여부 (기본값: true)
- report_mode: 리포트 모드 (기본값: "테마별 분석")

출력:
- 전망 리포트
```

## 사용 예시

Claude Desktop에서 MCP 서버가 설정되면 다음과 같이 사용할 수 있습니다:

```
"삼성전자의 최근 동향을 분석해줘"
→ chat 도구가 호출되어 답변 생성

"AI 반도체 관련 종목들을 비교 분석해줘"
→ generate_comparative_report 도구가 호출되어 비교 리포트 생성

"최근 6개월간 배터리 관련 트렌드를 분석해줘"
→ generate_trend_report 도구가 호출되어 트렌드 분석

"현재 인기 있는 테마 종목들을 보여줘"
→ get_market_themes 도구가 호출되어 테마 정보 제공
```

## 문제 해결

### MCP 서버가 연결되지 않을 때
1. Python 경로가 올바른지 확인
2. 환경 변수가 제대로 설정되었는지 확인
3. 로그 파일 확인: `~/.claude/logs/`

### 도구 실행 오류
1. API 서비스가 정상적으로 실행 중인지 확인
2. 데이터베이스 연결 상태 확인 (Neo4j, OpenSearch 등)
3. 필요한 API 키 설정 확인

## 개발자 정보

### MCP 서버 테스트
```bash
# MCP 서버 테스트
python -m mcp_server

# 특정 도구 테스트
python -c "
import asyncio
from mcp_server import call_tool
from mcp.types import ToolCall

async def test():
    tool_call = ToolCall(
        id='test',
        name='chat',
        arguments={'query': '삼성전자 주가 전망'}
    )
    result = await call_tool(tool_call)
    print(result)

asyncio.run(test())
"
```

### 새로운 도구 추가
`mcp_server.py`의 `list_tools()`와 `call_tool()` 함수에 새로운 도구를 추가합니다.

## 라이선스
[프로젝트 라이선스 정보]