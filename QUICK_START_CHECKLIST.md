# 🚀 Quick Start Checklist - 모니터링 시스템

내일이나 이후 작업 시 빠른 시작을 위한 체크리스트입니다.

---

## ✅ 시스템 상태 확인 (30초)

### **1. 서비스 실행 상태**
```bash
# 모든 컨테이너 상태 확인
docker ps | grep -E "(grafana|prometheus|ontology)"

# 예상 결과: 3개 컨테이너 모두 "Up" 상태
```

### **2. 핵심 서비스 접속 테스트**
```bash
# API 서버 상태
curl -s http://localhost:8000/monitoring/health/detailed

# Grafana 접속 확인
curl -s http://localhost:3001 | head -5

# Langfuse 연결 확인
docker exec ontology-chat-api-dev python -c "from api.utils.langfuse_tracer import tracer; print(f'Enabled: {tracer.is_enabled}')"
```

---

## 🔧 문제 해결 (필요시)

### **서비스 재시작**
```bash
# 모니터링 스택 재시작
docker-compose -f docker-compose.monitoring.yml up -d

# API 서버 재시작
docker-compose -f docker-compose.dev.yml restart api

# 네트워크 재연결 (필요시)
docker network connect ontology_chat_ontology-network ontology_prometheus
docker network connect ontology_chat_ontology-network ontology_grafana
```

### **의존성 재설치 (필요시)**
```bash
# Langfuse 재설치 (컨테이너 새로 생성된 경우)
docker exec ontology-chat-api-dev pip install langfuse pydantic-settings
```

---

## 📊 대시보드 접속 정보

### **모니터링 대시보드**
- 🌐 **Grafana**: http://localhost:3001
  - ID: `admin`
  - PW: `ontology_admin_2024`
  - 대시보드: "Query-Response Tracing Dashboard"

### **트레이싱 대시보드**
- 🔍 **Langfuse**: http://192.168.0.10:3000
  - LLM 호출 추적 및 성능 분석

### **메트릭 API**
- 📈 **Prometheus**: http://localhost:9092
- 🔍 **API 메트릭**: http://localhost:8000/monitoring/metrics

---

## 🧪 빠른 테스트

### **데이터 생성 테스트**
```bash
# 테스트 질의 실행
curl -X POST -H "Content-Type: application/json" \
  -d '{"query":"삼성전자 전망은?","user_id":"test","session_id":"session1"}' \
  http://localhost:8000/chat
```

### **결과 확인**
1. **Grafana**: 질의 수 증가 확인
2. **Langfuse**: 새 트레이스 생성 확인
3. **메트릭**: `curl http://localhost:8000/monitoring/metrics | grep ontology_total`

---

## 📋 다음 작업 우선순위

### **즉시 가능한 작업**
- [ ] 알림 규칙 설정 (Alertmanager)
- [ ] 대시보드 패널 커스터마이징
- [ ] 성능 임계값 설정

### **단기 개발 계획**
- [ ] 사용자 행동 패턴 분석 대시보드
- [ ] 자동화된 성능 리포트
- [ ] 이상 탐지 시스템

---

## 📞 참고 문서

- 📋 **상세 가이드**: `TASKMASTER_AI_MONITORING_REPORT.md`
- 🎯 **완료 보고서**: `TODAY_COMPLETION_REPORT.md`
- 🔧 **기술 문서**: `api/monitoring/` 디렉토리

---

**🚀 Ready to go!** 모든 시스템이 준비되었습니다!