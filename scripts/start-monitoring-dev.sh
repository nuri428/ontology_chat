#!/bin/bash
# 개발환경 모니터링 시작 스크립트

set -e

echo "🚀 Ontology Chat 개발환경 모니터링 시작..."

# 환경변수 파일 확인
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다. .env.example을 참고하여 생성해주세요."
    exit 1
fi

if [ ! -f .env.monitoring ]; then
    echo "⚠️  .env.monitoring 파일이 없습니다. 기본값으로 생성합니다."
    cp .env.monitoring .env.monitoring.local
fi

# Grafana 데이터소스 설정을 개발환경용으로 복사
echo "📊 Grafana 개발환경 설정 적용..."
cp monitoring/grafana/datasources/dev.yml monitoring/grafana/datasources/prometheus.yml

# Docker Compose로 개발환경 실행
echo "🐳 Docker Compose 개발환경 시작..."
docker compose -f docker-compose.dev.yml --env-file .env --env-file .env.monitoring up -d

echo "✅ 모니터링 서비스가 시작되었습니다!"
echo ""
echo "📊 서비스 접근 URL:"
echo "  • API: http://localhost:8000"
echo "  • UI: http://localhost:8501"
echo "  • Grafana: http://localhost:3000 (admin / dev_admin_2024)"
echo "  • Prometheus: http://localhost:9090"
echo "  • Alertmanager: http://localhost:9093"
echo "  • Jaeger: http://localhost:16686"
echo "  • Node Exporter: http://localhost:9100"
echo "  • Redis Exporter: http://localhost:9121"
echo ""
echo "📋 로그 확인: docker compose -f docker-compose.dev.yml logs -f"
echo "🛑 중지: docker compose -f docker-compose.dev.yml down"