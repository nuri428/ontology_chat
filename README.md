# Ontology Chat

> 뉴스 기반 온톨로지 및 주식 데이터를 활용한 **컨텍스트 엔지니어링 기반 질의응답 챗봇**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.49+-red.svg)](https://streamlit.io)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.15+-orange.svg)](https://neo4j.com)
[![OpenSearch](https://img.shields.io/badge/OpenSearch-2.11+-yellow.svg)](https://opensearch.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)

## 📋 프로젝트 개요

**Ontology Chat**은 뉴스 데이터, 주식 정보, 그리고 온톨로지 그래프를 결합하여 지능적인 질의응답을 제공하는 AI 챗봇 시스템입니다. FastAPI 기반의 RESTful API와 Streamlit 기반의 웹 UI를 제공하며, 실시간 데이터 분석과 전망 리포트를 제공합니다.

### 🚀 현재 상태 (2025.09.16)

- ✅ **API 서버**: 정상 작동 중 (포트 8000)
- ✅ **웹 UI**: 정상 작동 중 (포트 8501)  
- ✅ **데이터베이스**: Neo4j, OpenSearch 연결 정상
- ✅ **핵심 기능**: 뉴스 검색, 그래프 검색, 답변 생성 완료
- ✅ **Docker 환경**: 개발/운영 환경 구축 완료

### 🎯 주요 기능

- **🔍 지능형 검색**: Neo4j 그래프 데이터베이스와 OpenSearch 벡터 검색을 통한 다차원 검색
- **📊 실시간 분석**: 주식 데이터와 뉴스 정보를 결합한 실시간 분석
- **📈 전망 리포트**: AI 기반 종합 분석 리포트 자동 생성
- **🎨 인터랙티브 시각화**: pyvis를 활용한 그래프 네트워크 시각화
- **🐳 컨테이너화**: Docker Compose를 통한 쉬운 배포 및 관리
- **🔧 MCP 어댑터**: Model Context Protocol 기반 모듈화된 데이터 소스 연결
- **⚡ 고성능**: 비동기 처리 및 캐싱을 통한 빠른 응답
- **🛡️ 오류 처리**: 강력한 오류 처리 및 재시도 메커니즘

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   FastAPI API   │    │   MCP Adapters  │
│   (Port: 8501)  │◄──►│   (Port: 8000)  │◄──►│                 │
│  - 질의 입력     │    │  - RESTful API  │    │  - Neo4j MCP    │
│  - pyvis 그래프  │    │  - 오류 처리    │    │  - OpenSearch   │
└─────────────────┘    └─────────────────┘    │  - Stock API    │
         │                       │            └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Neo4j DB      │    │   OpenSearch    │    │   Stock API     │
│   (Port: 7687)  │    │   (Port: 9200)  │    │   (External)    │
│  - 60만+ 뉴스   │    │  - 30만+ 문서   │    │  - yfinance     │
│  - 그래프 관계  │    │  - 벡터 검색    │    │  - 실시간 주가  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 프로젝트 구조

```
ontology_chat/
├── api/                          # FastAPI 백엔드 (31개 Python 파일)
│   ├── adapters/                 # MCP 어댑터들
│   │   ├── mcp_neo4j.py         # Neo4j 연결
│   │   ├── mcp_opensearch.py    # OpenSearch 연결
│   │   └── mcp_stock.py         # 주식 API 연결
│   ├── config/                   # 설정 관리
│   │   ├── __init__.py          # 환경 변수 로딩
│   │   └── keyword_mappings.py  # 키워드 매핑
│   ├── services/                 # 비즈니스 로직
│   │   ├── chat_service.py      # 채팅 서비스 (핵심)
│   │   ├── error_handler.py     # 오류 처리
│   │   └── cache_manager.py     # 캐시 관리
│   ├── mcp/                      # MCP 도구들
│   │   ├── tools.py             # 검색 도구들
│   │   └── router.py            # MCP 라우터
│   └── main.py                   # FastAPI 앱
├── ui/                          # Streamlit 프론트엔드
│   └── main.py                  # 웹 UI
├── docker-compose.dev.yml       # 개발 환경
├── docker-compose.prod.yml      # 운영 환경
└── Makefile                     # 자동화 스크립트
```

## 💡 사용 예시

### 1. 기본 질의
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "한화 관련 최근 뉴스는?"}'
```

### 2. 복잡한 분석 질의
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "최근 지상무기 관련 수출 기사로 유망한 종목은?"}'
```

### 3. 그래프 검색
```bash
curl -X POST "http://localhost:8000/mcp/query_graph_default" \
  -H "Content-Type: application/json" \
  -d '{"q": "한화", "limit": 10}'
```

## 🔧 트러블슈팅

### 자주 발생하는 문제들

#### 1. Docker 컨테이너 시작 실패
```bash
# 로그 확인
docker logs ontology-chat-api-dev
docker logs ontology-chat-ui-dev

# 컨테이너 재시작
make docker-dev-down
make docker-dev-up
```

#### 2. 데이터베이스 연결 오류
```bash
# 헬스 체크
curl http://localhost:8000/health/ready

# Neo4j 연결 확인
curl http://localhost:7474

# OpenSearch 연결 확인
curl http://localhost:9200/_cluster/health
```

#### 3. 의존성 오류
```bash
# 가상환경 재생성
rm -rf venv
python -m venv venv
source venv/bin/activate
uv sync
```

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 연락처

- **프로젝트 관리자**: [Your Name]
- **이메일**: [your.email@example.com]
- **프로젝트 링크**: [https://github.com/yourusername/ontology_chat](https://github.com/yourusername/ontology_chat)

## 🙏 감사의 말

- [FastAPI](https://fastapi.tiangolo.com/) - 고성능 웹 프레임워크
- [Streamlit](https://streamlit.io/) - 빠른 웹 UI 개발
- [Neo4j](https://neo4j.com/) - 그래프 데이터베이스
- [OpenSearch](https://opensearch.org/) - 벡터 검색 엔진
- [pyvis](https://pyvis.readthedocs.io/) - 네트워크 시각화

---

**⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!**

## 🚀 빠른 시작

### 1. 사전 요구사항

- **Docker & Docker Compose**: 최신 버전
- **외부 서비스**: Neo4j, OpenSearch (이미 실행 중이어야 함)
- **API 키**: OpenAI API 키 (선택사항)

### 2. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd ontology_chat

# 환경 변수 설정
cp .env.example .env
# .env 파일에서 필요한 값들을 설정
```

### 3. 개발 환경 실행

```bash
# Docker Compose로 전체 스택 실행
make docker-dev-up

# 또는 직접 실행
docker-compose -f docker-compose.dev.yml up -d
```

### 4. 서비스 접근

- **UI**: http://localhost:8501
- **API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health/live

## 📚 API 문서

### 주요 엔드포인트

#### 1. 채팅 API
```http
POST /chat
Content-Type: application/json

{
  "query": "최근 지상무기 관련 수출 기사로 유망한 종목은?"
}
```

**응답 예시:**
```json
{
  "query": "최근 지상무기 관련 수출 기사로 유망한 종목은?",
  "answer": "## 🔍 질의 분석\n**원본 질의**: 최근 지상무기 관련 수출 기사로 유망한 종목은?\n...",
  "sources": [...],
  "graph_samples": [...],
  "meta": {
    "total_latency_ms": 1250.5,
    "services_attempted": ["opensearch", "neo4j", "stock_api"]
  }
}
```

#### 2. MCP 도구 API
```http
# 뉴스 검색
POST /mcp/call
{
  "tool": "search_news",
  "args": {"query": "한화", "limit": 5}
}

# 그래프 검색
POST /mcp/query_graph_default
{
  "q": "한화",
  "limit": 10
}
```

#### 3. 헬스 체크
```http
GET /health/live    # 기본 상태 확인
GET /health/ready   # 서비스 준비 상태 확인
```

## 🛠️ 기술 스택

## 📊 구현 상태 및 성능

### ✅ 완료된 기능 (2025.09.16)

| 기능 | 상태 | 성능 |
|------|------|------|
| **API 서버** | ✅ 완료 | 응답시간 < 1.5초 |
| **웹 UI** | ✅ 완료 | 실시간 업데이트 |
| **뉴스 검색** | ✅ 완료 | 3ms, 60만+ 문서 |
| **그래프 검색** | ✅ 완료 | 5ms, 관계 포함 |
| **답변 생성** | ✅ 완료 | 구조화된 응답 |
| **시각화** | ✅ 완료 | pyvis 인터랙티브 |
| **Docker 환경** | ✅ 완료 | 개발/운영 분리 |
| **오류 처리** | ✅ 완료 | 강력한 재시도 |

### ⏳ 진행 중인 기능

| 기능 | 진행률 | 예상 완료 |
|------|--------|-----------|
| **LangGraph 파이프라인** | 10% | TBD |
| **CLI 인터페이스** | 30% | 1주 |
| **테스트 환경** | 0% | 2주 |
| **문서화** | 80% | 완료 |

### Backend
- **Python 3.12+**: 메인 개발 언어
- **FastAPI**: 고성능 웹 API 프레임워크
- **Pydantic**: 데이터 검증 및 설정 관리
- **Loguru**: 고급 로깅 시스템
- **anyio**: 비동기 처리

### Frontend
- **Streamlit**: 빠른 웹 UI 개발
- **pyvis**: 인터랙티브 네트워크 시각화
- **Pandas**: 데이터 처리 및 분석

### 데이터베이스
- **Neo4j**: 그래프 데이터베이스 (60만+ 뉴스)
- **OpenSearch**: 벡터 검색 (30만+ 문서)

### 인프라
- **Docker**: 컨테이너화
- **Docker Compose**: 멀티 컨테이너 오케스트레이션
- **uv**: 빠른 Python 패키지 관리

## 📁 프로젝트 구조

```
ontology_chat/
├── api/                          # FastAPI 백엔드
│   ├── adapters/                 # MCP 어댑터들
│   │   ├── mcp_neo4j.py         # Neo4j 연결
│   │   ├── mcp_opensearch.py    # OpenSearch 연결
│   │   └── mcp_stock.py         # 주식 API 연결
│   ├── config/                   # 설정 파일들
│   │   └── graph_search.cypher  # 기본 그래프 검색 쿼리
│   ├── graph/                    # LangGraph 파이프라인
│   │   └── pipeline.py
│   ├── mcp/                      # MCP 라우터 및 도구들
│   ├── routers/                  # API 라우터들
│   │   └── health.py            # 헬스체크
│   ├── services/                 # 비즈니스 로직
│   │   ├── chat_service.py      # 채팅 서비스
│   │   └── report_service.py    # 리포트 생성
│   ├── config.py                # 환경 설정
│   ├── logging.py               # 로깅 설정
│   └── main.py                  # FastAPI 앱
├── ui/                          # Streamlit 프론트엔드
│   └── main.py                  # 메인 UI
├── monitoring/                  # 모니터링 설정
│   ├── prometheus.yml
│   └── grafana/
├── nginx/                       # Nginx 설정 (운영용)
│   └── nginx.conf
├── scripts/                     # 배포 스크립트
│   └── deploy.sh
├── docker-compose.yml           # 기본 Docker Compose
├── docker-compose.dev.yml       # 개발용 Docker Compose
├── docker-compose.prod.yml      # 운영용 Docker Compose
├── Dockerfile.api               # API 컨테이너
├── Dockerfile.ui                # UI 컨테이너
├── Dockerfile.api.prod          # API 운영 컨테이너
├── Dockerfile.ui.prod           # UI 운영 컨테이너
├── Makefile                     # 편의 명령어들
├── pyproject.toml               # Python 프로젝트 설정
└── README.md                    # 이 파일
```

## 🔧 환경 변수

### 필수 설정

```bash
# OpenAI API (선택사항)
OPENAI_API_KEY=your_openai_api_key_here

# Neo4j 연결 정보
NEO4J_URI=neo4j://192.168.0.10:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=news-def-topology

# OpenSearch 연결 정보
OPENSEARCH_HOST=http://192.168.0.10:9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=your_password
```

### 선택적 설정

```bash
# API 서버 설정
APP_HOST=0.0.0.0
APP_PORT=8000

# 검색 설정
NEO4J_SEARCH_LOOKBACK_DAYS=180
NEO4J_SEARCH_DEFAULT_DOMAIN=
NEO4J_SEARCH_CYPHER_FILE=api/config/graph_search.cypher

# 그래프 검색 키 매핑 (JSON)
GRAPH_SEARCH_KEYS='{"Company": ["name","ticker"], "Event": ["title","event_type"]}'
```

## 🎮 사용 방법

### 1. 그래프 컨텍스트 조회

1. **UI 접속**: http://localhost:8501
2. **"🔗 그래프 컨텍스트"** 탭 선택
3. **검색어 입력**: 예) "한화 지상무기 수주"
4. **옵션 설정**: 제한 개수, 기간 등
5. **"관계(에지) 포함"** 체크박스로 관계 시각화 선택
6. **"그래프 질의 실행"** 클릭

### 2. 채팅 기능

1. **"💬 Chat"** 탭 선택
2. **질문 입력**: 자연어로 질문
3. **AI 답변 확인**: 컨텍스트 기반 답변

### 3. 리포트 생성

1. **"📑 리포트"** 탭 선택
2. **리포트 옵션 설정**: 도메인, 기간, 뉴스 크기 등
3. **"리포트 생성"** 클릭
4. **마크다운 리포트 확인**

## 🐳 Docker 명령어

### 개발 환경

```bash
# 개발 환경 실행
make docker-dev-up

# 개발 환경 중지
make docker-dev-down

# 로그 확인
make docker-dev-logs

# 상태 확인
docker-compose -f docker-compose.dev.yml ps
```

### 운영 환경

```bash
# 운영 환경 배포
make docker-prod-deploy

# 운영 환경 중지
make docker-prod-stop

# 운영 환경 재시작
make docker-prod-restart

# 운영 환경 로그
make docker-prod-logs
```

### 기타 명령어

```bash
# 이미지 빌드
make docker-build

# 컨테이너 정리
make docker-prod-clean

# 테스트 실행
make test

# 코드 포맷팅
make fmt

# 타입 체크
make typecheck
```

## 🔍 API 엔드포인트

### 헬스체크
- `GET /health/live` - 서비스 생존 확인
- `GET /health/ready` - 서비스 준비 상태 확인

### 그래프 검색
- `POST /mcp/query_graph_default` - 기본 그래프 검색
- `POST /mcp/call` - MCP 도구 호출

### 채팅
- `POST /chat` - 채팅 메시지 처리

### 리포트
- `POST /report` - 리포트 생성

### MCP 도구
- `GET /mcp/describe` - 사용 가능한 도구 목록
- `POST /mcp/call` - 특정 도구 실행

## 📊 모니터링

### 개발 환경
- **API 로그**: `docker logs ontology-chat-api-dev`
- **UI 로그**: `docker logs ontology-chat-ui-dev`

### 운영 환경
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Nginx**: 리버스 프록시 및 로드 밸런싱

## 🧪 테스트

```bash
# 전체 테스트 실행
make test

# 특정 테스트 실행
uv run pytest tests/test_health.py -v

# 커버리지 포함 테스트
uv run pytest --cov=api tests/
```

## 🚀 배포

### 개발 환경 배포
```bash
# 환경 변수 설정
cp .env.example .env
# .env 파일 수정

# 개발 환경 실행
make docker-dev-up
```

### 운영 환경 배포
```bash
# 운영 환경 변수 설정
cp .env.prod.example .env.prod
# .env.prod 파일 수정

# 자동 배포
make docker-prod-deploy
```

## 🔧 문제 해결

### 일반적인 문제들

1. **포트 충돌**
   ```bash
   # 사용 중인 포트 확인
   netstat -tulpn | grep :8000
   netstat -tulpn | grep :8501
   ```

2. **환경변수 문제**
   ```bash
   # 컨테이너 내부 환경변수 확인
   docker exec ontology-chat-api-dev env | grep NEO4J
   ```

3. **의존성 문제**
   ```bash
   # 의존성 재설치
   uv sync --reinstall
   ```

4. **Docker 이미지 문제**
   ```bash
   # 이미지 재빌드
   make docker-build --no-cache
   ```

### 로그 확인

```bash
# API 서버 로그
docker logs ontology-chat-api-dev -f

# UI 서버 로그
docker logs ontology-chat-ui-dev -f

# 전체 로그
make docker-dev-logs
```

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 지원

- **이슈 리포트**: [GitHub Issues](https://github.com/your-repo/issues)
- **문서**: [Wiki](https://github.com/your-repo/wiki)
- **이메일**: your-email@example.com

## 🙏 감사의 말

- [FastAPI](https://fastapi.tiangolo.com/) - 고성능 웹 프레임워크
- [Streamlit](https://streamlit.io/) - 빠른 웹 앱 개발
- [Neo4j](https://neo4j.com/) - 그래프 데이터베이스
- [OpenSearch](https://opensearch.org/) - 검색 및 분석 엔진
- [LangChain](https://langchain.com/) - LLM 애플리케이션 프레임워크

---

**Ontology Chat** - 지능형 데이터 분석의 새로운 차원을 경험하세요! 🚀
