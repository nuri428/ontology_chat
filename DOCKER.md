# Docker Compose 가이드

## 📋 개요

이 프로젝트는 API와 UI를 분리한 마이크로서비스 아키텍처로 구성되어 있으며, Docker Compose를 통해 전체 스택을 쉽게 실행할 수 있습니다.

## 🏗️ 아키텍처

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│     UI      │    │     API     │    │   Neo4j     │
│ (Streamlit) │───▶│  (FastAPI)  │───▶│ (Graph DB)  │
│   :8501     │    │   :8000     │    │   :7687     │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │ OpenSearch  │
                   │ (Vector DB) │
                   │   :9200     │
                   └─────────────┘
```

## 🚀 빠른 시작

### 1. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일에서 OPENAI_API_KEY 등 필요한 값들을 설정
```

### 2. 프로덕션 환경 실행
```bash
# 전체 스택 빌드 및 실행
make docker-build
make docker-up

# 또는 직접 실행
docker-compose up -d
```

### 3. 개발 환경 실행 (핫 리로드)
```bash
# 개발용 스택 실행
make docker-dev-up

# 또는 직접 실행
docker-compose -f docker-compose.dev.yml up -d
```

## 📦 서비스 구성

### API 서버 (`api`)
- **포트**: 8000
- **기술**: FastAPI + Python 3.12
- **기능**: REST API 엔드포인트, 채팅 서비스, MCP 어댑터

### UI 서버 (`ui`)
- **포트**: 8501
- **기술**: Streamlit + Python 3.12
- **기능**: 웹 인터페이스, 채팅 UI

### Neo4j (`neo4j`)
- **포트**: 7474 (웹), 7687 (Bolt)
- **기능**: 그래프 데이터베이스, 온톨로지 저장

### OpenSearch (`opensearch`)
- **포트**: 9200 (REST), 9600 (Performance Analyzer)
- **기능**: 벡터 검색, 뉴스/문서 인덱싱

### OpenSearch Dashboards (`opensearch-dashboards`)
- **포트**: 5601
- **기능**: OpenSearch 관리 및 모니터링

## 🛠️ Makefile 명령어

```bash
# Docker 빌드
make docker-build

# 프로덕션 환경 실행
make docker-up
make docker-down

# 개발 환경 실행 (핫 리로드)
make docker-dev-up
make docker-dev-down

# 로그 확인
make docker-logs          # 프로덕션
make docker-dev-logs      # 개발
```

## 🔧 개발 환경 vs 프로덕션 환경

### 개발 환경 (`docker-compose.dev.yml`)
- **핫 리로드**: 코드 변경 시 자동 재시작
- **볼륨 마운트**: 로컬 코드 변경이 즉시 반영
- **디버깅**: 상세한 로그 출력

### 프로덕션 환경 (`docker-compose.yml`)
- **최적화**: 멀티스테이지 빌드
- **보안**: 최소한의 권한
- **안정성**: 재시작 정책 적용

## 📊 서비스 접근 URL

### 개발 환경
| 서비스 | URL | 설명 |
|--------|-----|------|
| UI | http://localhost:8501 | Streamlit 웹 인터페이스 |
| API | http://localhost:8000 | FastAPI REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Neo4j Browser | http://localhost:7474 | 그래프 데이터베이스 관리 |
| OpenSearch | http://localhost:9200 | 벡터 검색 엔진 |
| OpenSearch Dashboards | http://localhost:5601 | OpenSearch 관리 |

### 운영 환경
| 서비스 | URL | 설명 |
|--------|-----|------|
| UI | https://localhost | Streamlit 웹 인터페이스 (HTTPS) |
| API | https://localhost/api | FastAPI REST API (HTTPS) |
| API Docs | https://localhost/api/docs | Swagger UI (HTTPS) |
| Neo4j Browser | http://localhost:7474 | 그래프 데이터베이스 관리 |
| OpenSearch | http://localhost:9200 | 벡터 검색 엔진 |
| OpenSearch Dashboards | http://localhost:5601 | OpenSearch 관리 |
| Grafana | http://localhost:3000 | 모니터링 대시보드 |
| Prometheus | http://localhost:9090 | 메트릭 수집 |

## 🐛 문제 해결

### 1. 포트 충돌
```bash
# 사용 중인 포트 확인
netstat -tulpn | grep :8000
netstat -tulpn | grep :8501

# 다른 포트로 변경
# docker-compose.yml에서 ports 섹션 수정
```

### 2. 메모리 부족
```bash
# OpenSearch 메모리 설정 조정
# docker-compose.yml에서 OPENSEARCH_JAVA_OPTS 수정
- "OPENSEARCH_JAVA_OPTS=-Xms256m -Xmx256m"
```

### 3. 볼륨 권한 문제
```bash
# 볼륨 권한 재설정
sudo chown -R $USER:$USER ./data
```

### 4. 컨테이너 재시작
```bash
# 특정 서비스만 재시작
docker-compose restart api
docker-compose restart ui

# 전체 스택 재시작
docker-compose down && docker-compose up -d
```

## 📝 로그 확인

```bash
# 전체 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f api
docker-compose logs -f ui
docker-compose logs -f neo4j

# 마지막 N줄만 확인
docker-compose logs --tail=100 api
```

## 🔄 데이터 백업 및 복원

### Neo4j 백업
```bash
# 백업
docker exec ontology-chat-neo4j neo4j-admin dump --database=neo4j --to=/tmp/backup.dump
docker cp ontology-chat-neo4j:/tmp/backup.dump ./backup.dump

# 복원
docker cp ./backup.dump ontology-chat-neo4j:/tmp/backup.dump
docker exec ontology-chat-neo4j neo4j-admin load --database=neo4j --from=/tmp/backup.dump
```

### OpenSearch 백업
```bash
# 인덱스 백업 (스냅샷)
curl -X PUT "localhost:9200/_snapshot/backup_repo" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/usr/share/opensearch/backup"
  }
}'
```

## 🚀 배포

### 개발 환경 배포
```bash
# 1. 환경 변수 설정
cp .env.example .env
# .env 파일에서 개발용 값들 설정

# 2. 개발 환경 실행 (핫 리로드)
make docker-dev-up

# 3. 헬스 체크
curl http://localhost:8000/health
curl http://localhost:8501
```

### 운영 환경 배포
```bash
# 1. 운영 환경 변수 설정
cp .env.prod.example .env.prod
# .env.prod 파일에서 운영용 값들 설정 (보안 강화)

# 2. 자동 배포 (권장)
make docker-prod-deploy

# 또는 수동 배포
make docker-prod-build
make docker-prod-up

# 3. 헬스 체크
curl https://localhost/health
curl https://localhost
```

### 운영 환경 관리
```bash
# 서비스 상태 확인
make docker-prod-status

# 로그 확인
make docker-prod-logs

# 서비스 재시작
make docker-prod-restart

# 서비스 중지
make docker-prod-stop

# 완전 정리 (주의!)
make docker-prod-clean
```

### 스케일링
```bash
# API 서버 스케일링
docker-compose up -d --scale api=3

# 로드 밸런서 설정 (nginx 등) 필요
```

---

*이 가이드는 ontology-chat 프로젝트의 Docker Compose 설정을 다룹니다.*
