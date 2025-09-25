#!/bin/bash
# 프로덕션환경 모니터링 시작 스크립트

set -e

echo "🚀 Ontology Chat 프로덕션환경 모니터링 시작..."

# 환경변수 파일 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다. 프로덕션 환경에서는 필수입니다."
    exit 1
fi

if [ ! -f .env.monitoring ]; then
    echo "❌ .env.monitoring 파일이 없습니다. 프로덕션 환경에서는 필수입니다."
    exit 1
fi

# 필수 환경변수 확인
required_vars=("GRAFANA_ADMIN_PASSWORD" "NEO4J_PASSWORD" "OPENSEARCH_PASSWORD" "OPENAI_API_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ 다음 필수 환경변수가 설정되지 않았습니다:"
    printf '  • %s\n' "${missing_vars[@]}"
    exit 1
fi

# Grafana 데이터소스 설정을 프로덕션환경용으로 복사
echo "📊 Grafana 프로덕션환경 설정 적용..."
cp monitoring/grafana/datasources/prod.yml monitoring/grafana/datasources/prometheus.yml

# SSL 인증서 확인 (있는 경우)
if [ -d "nginx/ssl" ]; then
    echo "🔒 SSL 인증서가 설정되어 있습니다."
else
    echo "⚠️  SSL 인증서가 설정되지 않았습니다. HTTP로 실행됩니다."
fi

# 기존 컨테이너 정리 (안전을 위해)
echo "🧹 기존 컨테이너 정리..."
docker compose -f docker-compose.prod.yml down

# Docker Compose로 프로덕션환경 실행
echo "🐳 Docker Compose 프로덕션환경 시작..."
docker compose -f docker-compose.prod.yml --env-file .env --env-file .env.monitoring up -d

# 헬스체크 대기
echo "⏳ 서비스 헬스체크 대기 중..."
sleep 30

# 서비스 상태 확인
echo "🔍 서비스 상태 확인..."
docker compose -f docker-compose.prod.yml ps

echo "✅ 프로덕션 모니터링 서비스가 시작되었습니다!"
echo ""
echo "📊 서비스 접근 URL:"
echo "  • API: http://localhost:8000"
echo "  • UI: http://localhost:8501"
echo "  • Grafana: http://localhost:3000"
echo "  • Prometheus: http://localhost:9090"
echo "  • Alertmanager: http://localhost:9093"
echo "  • Node Exporter: http://localhost:9100"
echo "  • Redis Exporter: http://localhost:9121"
if [ -d "nginx/ssl" ]; then
    echo "  • HTTPS Proxy: https://localhost"
fi
echo ""
echo "📋 로그 확인: docker compose -f docker-compose.prod.yml logs -f"
echo "🛑 중지: docker compose -f docker-compose.prod.yml down"
echo "📊 상태 확인: docker compose -f docker-compose.prod.yml ps"