#!/bin/bash

# Production deployment script for Ontology Chat
# Usage: ./scripts/deploy.sh [deploy|stop|restart|logs|status|clean]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="ontology-chat"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
BACKUP_DIR="./backups"
LOG_DIR="./logs/production"

# Ensure required directories exist
mkdir -p "$BACKUP_DIR" "$LOG_DIR"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Health check function
health_check() {
    local service=$1
    local url=$2
    local timeout=${3:-30}

    log "Health checking $service..."

    for i in $(seq 1 $timeout); do
        if curl -f -s "$url" > /dev/null 2>&1; then
            success "$service is healthy"
            return 0
        fi

        if [ $i -eq $timeout ]; then
            error "$service failed health check after ${timeout}s"
            return 1
        fi

        echo -n "."
        sleep 1
    done
}

# Backup function
backup_data() {
    log "Creating backup..."

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/backup_${timestamp}.tar.gz"

    # Backup volumes
    docker run --rm \
        -v "${PROJECT_NAME}_neo4j_data:/backup/neo4j" \
        -v "${PROJECT_NAME}_opensearch_data:/backup/opensearch" \
        -v "${PROJECT_NAME}_ollama_models:/backup/ollama" \
        -v "$(pwd)/${BACKUP_DIR}:/output" \
        alpine:latest \
        tar czf "/output/backup_${timestamp}.tar.gz" -C /backup .

    if [ -f "$backup_file" ]; then
        success "Backup created: $backup_file"

        # Keep only last 7 backups
        find "$BACKUP_DIR" -name "backup_*.tar.gz" -type f | sort | head -n -7 | xargs rm -f
    else
        error "Backup failed"
        return 1
    fi
}

# Pre-deployment checks
pre_deploy_checks() {
    log "Running pre-deployment checks..."

    # Check if required files exist
    if [ ! -f "$COMPOSE_FILE" ]; then
        error "Compose file $COMPOSE_FILE not found"
        return 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        error "Environment file $ENV_FILE not found"
        return 1
    fi

    # Check Docker
    if ! docker --version > /dev/null 2>&1; then
        error "Docker not installed or not running"
        return 1
    fi

    if ! docker-compose --version > /dev/null 2>&1; then
        error "Docker Compose not installed"
        return 1
    fi

    # Check available disk space (minimum 5GB)
    local available=$(df / | awk 'NR==2 {print $4}')
    if [ "$available" -lt 5242880 ]; then  # 5GB in KB
        warn "Low disk space: $(($available / 1024))MB available"
    fi

    success "Pre-deployment checks passed"
}

# 서비스 시작
start_services() {
    log_info "서비스 시작 중..."
    
    # 기존 컨테이너 정리
    docker-compose -f docker-compose.prod.yml down
    
    # 서비스 시작
    docker-compose -f docker-compose.prod.yml up -d
    
    log_success "서비스 시작 완료"
}

# 헬스체크
health_check() {
    log_info "헬스체크 수행 중..."
    
    # API 헬스체크
    for i in {1..30}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            log_success "API 서버 헬스체크 통과"
            break
        fi
        
        if [ $i -eq 30 ]; then
            log_error "API 서버 헬스체크 실패"
            exit 1
        fi
        
        sleep 2
    done
    
    # UI 헬스체크
    for i in {1..30}; do
        if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
            log_success "UI 서버 헬스체크 통과"
            break
        fi
        
        if [ $i -eq 30 ]; then
            log_error "UI 서버 헬스체크 실패"
            exit 1
        fi
        
        sleep 2
    done
    
    log_success "모든 서비스 헬스체크 통과"
}

# 로그 출력
show_logs() {
    log_info "서비스 로그 확인 중..."
    docker-compose -f docker-compose.prod.yml logs --tail=50
}

# 메인 함수
main() {
    log_info "Ontology Chat 운영 환경 배포 시작"
    
    case "${1:-deploy}" in
        "deploy")
            check_env
            check_ssl
            build_images
            start_services
            health_check
            log_success "배포 완료!"
            log_info "접속 URL:"
            log_info "  - UI: https://localhost"
            log_info "  - API: https://localhost/api"
            log_info "  - API Docs: https://localhost/api/docs"
            log_info "  - Neo4j Browser: http://localhost:7474"
            log_info "  - OpenSearch: http://localhost:9200"
            log_info "  - Grafana: http://localhost:3000"
            ;;
        "stop")
            log_info "서비스 중지 중..."
            docker-compose -f docker-compose.prod.yml down
            log_success "서비스 중지 완료"
            ;;
        "restart")
            log_info "서비스 재시작 중..."
            docker-compose -f docker-compose.prod.yml restart
            log_success "서비스 재시작 완료"
            ;;
        "logs")
            show_logs
            ;;
        "status")
            log_info "서비스 상태 확인 중..."
            docker-compose -f docker-compose.prod.yml ps
            ;;
        "clean")
            log_info "모든 컨테이너 및 볼륨 정리 중..."
            docker-compose -f docker-compose.prod.yml down -v --remove-orphans
            docker system prune -f
            log_success "정리 완료"
            ;;
        *)
            echo "사용법: $0 {deploy|stop|restart|logs|status|clean}"
            echo ""
            echo "명령어:"
            echo "  deploy  - 전체 배포 (기본값)"
            echo "  stop    - 서비스 중지"
            echo "  restart - 서비스 재시작"
            echo "  logs    - 로그 확인"
            echo "  status  - 서비스 상태 확인"
            echo "  clean   - 모든 컨테이너 및 볼륨 정리"
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"
