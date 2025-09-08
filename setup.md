# ontolog_chat 프로젝트 요약 문서

## 1. 프로젝트 개요
- 프로젝트명: **ontolog_chat**  
- 목적: 뉴스 기반 온톨로지 및 주식 데이터를 활용한 **컨텍스트 엔지니어링 기반 질의응답 챗봇** 개발  
- 주요 기능:
  - FastAPI 기반 REST API 서버 (`/chat`, `/health`)  
  - Neo4j, OpenSearch, 주식 API를 MCP 어댑터로 연결  
  - LangGraph/LangChain을 통한 파이프라인 기반 답변 생성  
  - 주식, 뉴스, 온톨로지 데이터를 결합하여 전망/리포트 제공  

---

## 2. 기술 스택
- **언어/런타임**: Python 3.12 (uv venv 사용)  
- **프레임워크**: FastAPI, Typer CLI  
- **설정 관리**: pydantic-settings, python-dotenv  
- **로깅**: loguru  
- **테스트**: pytest, pytest-asyncio  
- **외부 연동**:  
  - Neo4j (그래프 데이터베이스)  
  - OpenSearch (뉴스/문서 벡터 검색)  
  - 증권 API (주가 조회)  
- **추가 AI 구성 요소**: LangGraph, LangChain-core  

---

## 3. 디렉토리 구조
ontolog_chat/
├─ src/
│  └─ ontolog_chat/
│     ├─ init.py
│     ├─ config.py         # 환경 변수/설정
│     ├─ logging.py        # 로깅 세팅
│     ├─ main.py           # FastAPI 엔트리포인트
│     ├─ cli.py            # Typer CLI
│     ├─ routers/
│     │  └─ health.py      # 헬스 체크
│     ├─ services/
│     │  └─ chat_service.py # 채팅 서비스 로직
│     ├─ adapters/         # MCP 어댑터
│     │  ├─ mcp_neo4j.py
│     │  ├─ mcp_opensearch.py
│     │  └─ mcp_stock.py
│     └─ graph/
│        └─ pipeline.py    # LangGraph 파이프라인 뼈대
├─ tests/
│  └─ test_health.py
├─ .env.example
├─ .gitignore
├─ Makefile
└─ pyproject.toml

---

## 4. 실행 방법

### 1) 의존성 설치
```bash
uv init --package
uv add fastapi "uvicorn[standard]" typer pydantic-settings python-dotenv httpx
uv add langgraph langchain-core
uv add neo4j opensearch-py pandas
uv add loguru
uv add pytest pytest-asyncio httpx