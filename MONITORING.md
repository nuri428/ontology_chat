# Ontology Chat 모니터링 가이드

## 📊 모니터링 스택 개요

Ontology Chat 프로젝트는 다음과 같은 종합적인 모니터링 스택을 제공합니다:

### 핵심 구성요소
- **Grafana**: 대시보드와 시각화
- **Prometheus**: 메트릭 수집 및 저장
- **Alertmanager**: 알림 관리
- **Node Exporter**: 시스템 메트릭
- **Redis Exporter**: Redis 성능 메트릭
- **Jaeger**: 분산 추적 (개발환경)

## 🚀 빠른 시작

### 개발 환경
```bash
# 개발 환경 모니터링 시작
./scripts/start-monitoring-dev.sh

# 또는 수동으로
docker compose -f docker-compose.dev.yml up -d
```

### 프로덕션 환경
```bash
# 프로덕션 환경 모니터링 시작
./scripts/start-monitoring-prod.sh

# 또는 수동으로
docker compose -f docker-compose.prod.yml up -d
```

## 🔧 설정

### 환경변수
모니터링 관련 환경변수는 `.env.monitoring` 파일에서 관리됩니다:

```bash
# 기본 설정 복사
cp .env.monitoring .env.monitoring.local

# 필요에 따라 편집
nano .env.monitoring.local
```

### 주요 환경변수
- `GRAFANA_ADMIN_PASSWORD`: Grafana 관리자 비밀번호
- `GRAFANA_DOMAIN`: Grafana 도메인 설정
- `REDIS_PASSWORD`: Redis 비밀번호 (프로덕션)
- `SLACK_WEBHOOK_URL`: Slack 알림용 웹훅 URL

## 📈 접근 URL

### 개발 환경
| 서비스 | URL | 설명 |
|--------|-----|------|
| Grafana | http://localhost:3000 | 대시보드 (admin / dev_admin_2024) |
| Prometheus | http://localhost:9090 | 메트릭 쿼리 |
| Alertmanager | http://localhost:9093 | 알림 관리 |
| Jaeger | http://localhost:16686 | 분산 추적 |
| Node Exporter | http://localhost:9100 | 시스템 메트릭 |
| Redis Exporter | http://localhost:9121 | Redis 메트릭 |

### 프로덕션 환경
동일한 포트를 사용하지만 보안 설정이 강화됩니다.

## 📊 대시보드

### 1. 시스템 개요 (System Overview)
- CPU 및 메모리 사용률
- API 요청 속도
- 응답 시간
- Redis 성능

### 2. API 성능 (API Performance)
- 엔드포인트별 요청률
- LLM 응답 시간
- HTTP 상태 코드 분포
- 캐시 성능
- 활성 연결

### 3. 기존 대시보드
- Cache Performance
- LLM Observability
- Query Response Tracing
- Langfuse Analytics

## 🔔 알림 설정

### Slack 알림
`.env.monitoring`에서 Slack 웹훅 URL을 설정:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_CHANNEL=#monitoring
```

### 이메일 알림
이메일 SMTP 설정:
```bash
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=alerts@ontology-chat.com
EMAIL_TO=admin@ontology-chat.com
```

## 🐳 Docker Compose 구조

### 개발 환경 (`docker-compose.dev.yml`)
- 모든 서비스가 로컬에서 실행
- Jaeger 트레이싱 포함
- 개발용 설정 (더 많은 로그, 빈번한 업데이트)

### 프로덕션 환경 (`docker-compose.prod.yml`)
- 리소스 제한 설정
- 헬스체크 포함
- 외부 서비스 연결 지원
- 보안 강화

## 🔍 메트릭 이해하기

### API 메트릭
- `fastapi_requests_total`: 총 요청 수
- `fastapi_request_duration_seconds`: 요청 처리 시간
- `fastapi_inprogress_requests`: 진행 중인 요청

### 시스템 메트릭
- `node_cpu_seconds_total`: CPU 사용 시간
- `node_memory_*`: 메모리 사용량
- `node_filesystem_*`: 디스크 사용량

### Redis 메트릭
- `redis_commands_processed_total`: 처리된 명령 수
- `redis_keyspace_hits_total`: 캐시 히트
- `redis_memory_used_bytes`: 메모리 사용량

### 커스텀 메트릭
- `llm_response_duration_seconds`: LLM 응답 시간
- `opensearch_query_duration_seconds`: OpenSearch 쿼리 시간
- `neo4j_query_duration_seconds`: Neo4j 쿼리 시간

## 🛠️ 문제 해결

### 일반적인 문제

#### 1. Grafana 접속 불가
```bash
# 컨테이너 상태 확인
docker compose ps grafana

# 로그 확인
docker compose logs grafana

# 포트 충돌 확인
netstat -tlnp | grep :3000
```

#### 2. 메트릭이 보이지 않음
```bash
# Prometheus 타겟 상태 확인
curl http://localhost:9090/api/v1/targets

# Node Exporter 메트릭 확인
curl http://localhost:9100/metrics
```

#### 3. 알림이 작동하지 않음
```bash
# Alertmanager 설정 확인
curl http://localhost:9093/api/v1/status

# Alertmanager 로그 확인
docker compose logs alertmanager
```

### 성능 최적화

#### 메트릭 보존 기간 조정
```bash
# Prometheus 설정에서
--storage.tsdb.retention.time=30d  # 30일 보존
```

#### 메모리 사용량 최적화
```bash
# Docker Compose에서 메모리 제한 설정
deploy:
  resources:
    limits:
      memory: 1G
```

## 📚 추가 자료

- [Grafana 공식 문서](https://grafana.com/docs/)
- [Prometheus 공식 문서](https://prometheus.io/docs/)
- [Node Exporter](https://github.com/prometheus/node_exporter)
- [Redis Exporter](https://github.com/oliver006/redis_exporter)

## 🤝 기여하기

새로운 메트릭이나 대시보드를 추가하려면:

1. `monitoring/grafana/dashboards/`에 JSON 파일 추가
2. 필요한 경우 `monitoring/prometheus/prometheus.yml`에 새 타겟 추가
3. 문서 업데이트
4. PR 생성

---

💡 **팁**: 개발 중에는 `docker compose logs -f`로 실시간 로그를 모니터링하고, Grafana에서 실시간 메트릭을 확인하세요!