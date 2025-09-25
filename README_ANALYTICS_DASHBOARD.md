# Performance Analytics Dashboard

## Overview
실시간 성능 모니터링 및 분석을 위한 **Streamlit 기반 웹 대시보드**입니다. A-grade 품질(0.900+) 유지 및 시스템 성능 최적화를 위한 종합적인 시각화를 제공합니다.

## Features

### 🎯 **Real-time Monitoring**
- **A-Grade Quality Score**: 실시간 품질 점수 추적 (0.900+ 목표)
- **Response Time**: 평균 응답 시간 모니터링
- **Cache Hit Rate**: 멀티레벨 캐시 성능 지표
- **Request Throughput**: 분당 요청 처리량

### 📊 **Performance Analytics**
- **Historical Trends**: 1시간~30일 범위의 성능 트렌드
- **Quality Analysis**: 품질 점수 기여 요소 분석
- **Cache Analytics**: L1/L2/L3 캐시 레벨별 성능 분석
- **System Health**: 컴포넌트별 헬스 체크

### 🚨 **Alert & Monitoring**
- **Active Alerts**: 실시간 경고 및 알림
- **Component Status**: 시스템 구성요소 상태
- **Performance Recommendations**: 최적화 제안

## Quick Start

### 1. Prerequisites
```bash
# API 서버가 실행 중이어야 함
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 필수 의존성 확인
pip install streamlit plotly pandas requests
```

### 2. Start Dashboard
```bash
# 간단한 실행
./scripts/start-dashboard.sh

# 또는 직접 실행
cd dashboard
streamlit run performance_dashboard.py --server.port 8501
```

### 3. Access Dashboard
- **Dashboard URL**: http://localhost:8501
- **API Server**: http://localhost:8000

## Dashboard Sections

### 📊 **Real-time Overview**
현재 시스템 상태의 실시간 개요

**Key Metrics:**
- Quality Score (게이지 차트)
- Response Time Distribution
- Active Connections
- Error Rate
- Cache Effectiveness
- System Uptime

### 🏎️ **Performance Trends**
시간대별 성능 트렌드 분석

**Available Periods:**
- 1 hour (5-minute intervals)
- 6 hours (15-minute intervals)
- 24 hours (1-hour intervals)
- 7 days (6-hour intervals)
- 30 days (1-day intervals)

**Trend Charts:**
- Quality Score Timeline
- Response Time Timeline
- Cache Hit Rate Timeline
- Error Rate Timeline

### 💾 **Cache Analytics**
멀티레벨 캐시 시스템 성능 분석

**Cache Levels:**
- **L1 Memory**: 메모리 캐시 (0.5ms 평균)
- **L2 Redis**: 분산 캐시 (8.5ms 평균)
- **L3 Disk**: 디스크 캐시 (45ms 평균)

**Metrics per Level:**
- Hit Rate
- Efficiency Score
- Access Time
- Utilization
- Recommendations

### ⭐ **Quality Analysis**
A-grade 품질 유지를 위한 상세 분석

**Quality Breakdown:**
- Current Grade (A/B/C)
- Contributing Factors
- Quality History (30 days)
- Risk Assessment

**Contributing Factors:**
- Cache Performance (25% weight)
- Response Speed (15% weight)
- Content Relevance (30% weight)
- System Reliability (30% weight)

### 🚨 **System Health**
시스템 컴포넌트 헬스 모니터링

**Components:**
- Cache System (L1/L2/L3)
- LLM Service (Ollama)
- Databases (Neo4j, OpenSearch, Redis)

**Alert Levels:**
- 🔴 **Critical**: Immediate attention required
- 🟡 **Warning**: Performance degradation
- 🔵 **Info**: Informational notices

## API Endpoints

대시보드는 다음 API 엔드포인트를 사용합니다:

### Dashboard Data
```bash
GET /analytics/dashboard
# 종합 대시보드 데이터

GET /analytics/performance/snapshot
# 현재 성능 스냅샷

GET /analytics/performance/history?period=24h
# 성능 히스토리 데이터
```

### Cache Analytics
```bash
GET /analytics/cache/analysis
# 캐시 성능 분석

GET /cache/stats
# 캐시 통계 (기존)
```

### Quality & Health
```bash
GET /analytics/quality/analysis
# 품질 분석

GET /analytics/alerts
# 활성 알림

GET /metrics/health
# 시스템 헬스 체크
```

## Configuration

### Streamlit Configuration
```toml
# .streamlit/config.toml
[server]
port = 8501
address = "0.0.0.0"
headless = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
```

### Dashboard Settings
- **Auto Refresh**: 30초 자동 새로고침
- **Time Ranges**: 1h, 6h, 24h, 7d, 30d 선택 가능
- **Real-time Updates**: 실시간 메트릭 업데이트

## Visual Components

### Charts & Visualizations
- **Gauge Charts**: 품질 점수, 임계값 표시
- **Line Charts**: 시간대별 트렌드
- **Bar Charts**: 기여 요소, 비교 분석
- **Histograms**: 응답 시간 분포
- **Progress Bars**: 리소스 사용률

### Status Indicators
- **Color Coding**: 성능 상태별 색상 구분
- **Threshold Lines**: A-grade 임계값 표시
- **Status Icons**: 컴포넌트 상태 아이콘
- **Metric Cards**: 주요 지표 카드

## Troubleshooting

### Common Issues

#### Dashboard Won't Start
```bash
# 의존성 설치
pip install streamlit plotly pandas requests

# 포트 충돌 확인
lsof -i :8501

# 권한 확인
chmod +x scripts/start-dashboard.sh
```

#### API Connection Failed
```bash
# API 서버 상태 확인
curl http://localhost:8000/health

# API 서버 시작
uvicorn api.main:app --reload --port 8000
```

#### Data Loading Errors
```bash
# 캐시 지우기
rm -rf ~/.streamlit/cache/

# 브라우저 캐시 새로고침
Ctrl+Shift+R (or Cmd+Shift+R on Mac)
```

### Performance Optimization
```bash
# 대시보드 성능 향상을 위한 설정
export STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION=true
export STREAMLIT_SERVER_MAX_UPLOAD_SIZE=50

# 메모리 사용량 확인
streamlit config show
```

## Development

### Adding New Metrics
1. **API 엔드포인트 추가** (analytics_router.py)
2. **대시보드 컴포넌트 추가** (performance_dashboard.py)
3. **차트 렌더링 함수 작성**

### Custom Visualizations
```python
# 새로운 차트 추가 예시
def render_custom_chart(data):
    fig = px.scatter(
        data, x='timestamp', y='metric',
        title="Custom Metric Analysis"
    )
    st.plotly_chart(fig, use_container_width=True)
```

### Theme Customization
```css
/* .streamlit/style.css */
.main-header {
    color: #1f77b4;
    text-align: center;
}

.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 10px;
}
```

## Production Deployment

### Docker Configuration
```dockerfile
# Dockerfile.dashboard
FROM python:3.10-slim

WORKDIR /app
COPY dashboard/ ./dashboard/
COPY requirements.txt .

RUN pip install -r requirements.txt
EXPOSE 8501

CMD ["streamlit", "run", "dashboard/performance_dashboard.py", "--server.address", "0.0.0.0"]
```

### Load Balancing
- **Reverse Proxy**: Nginx/Apache 설정
- **SSL Termination**: HTTPS 인증서 설정
- **Caching**: CDN 또는 캐시 레이어

### Monitoring
- **Dashboard Metrics**: Streamlit 자체 메트릭 수집
- **User Analytics**: 사용자 접근 패턴 분석
- **Performance Monitoring**: 대시보드 렌더링 성능

## Security

### Access Control
- **Authentication**: Streamlit 인증 모듈
- **Authorization**: 역할 기반 접근 제어
- **Network Security**: VPN 또는 방화벽 설정

### Data Protection
- **API Key Management**: 환경 변수 사용
- **Sensitive Data**: 마스킹 처리
- **Audit Logging**: 접근 로그 기록

이 대시보드를 통해 Ontology Chat의 A-grade 품질을 실시간으로 모니터링하고, 성능 최적화를 위한 인사이트를 얻을 수 있습니다.