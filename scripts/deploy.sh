#!/bin/bash

# 운영 환경 배포 스크립트
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 환경 변수 확인
check_env() {
    log_info "환경 변수 확인 중..."
    
    if [ ! -f ".env.prod" ]; then
        log_error ".env.prod 파일이 없습니다. .env.prod.example을 참조하여 생성하세요."
        exit 1
    fi
    
    # 필수 환경 변수 확인
    source .env.prod
    
    if [ -z "$OPENAI_API_KEY" ]; then
        log_error "OPENAI_API_KEY가 설정되지 않았습니다."
        exit 1
    fi
    
    if [ -z "$NEO4J_PASSWORD" ]; then
        log_error "NEO4J_PASSWORD가 설정되지 않았습니다."
        exit 1
    fi
    
    if [ -z "$OPENSEARCH_PASSWORD" ]; then
        log_error "OPENSEARCH_PASSWORD가 설정되지 않았습니다."
        exit 1
    fi
    
    log_success "환경 변수 확인 완료"
}

# SSL 인증서 확인
check_ssl() {
    log_info "SSL 인증서 확인 중..."
    
    if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
        log_warning "SSL 인증서가 없습니다. 자체 서명된 인증서를 생성합니다..."
        
        mkdir -p nginx/ssl
        
        # 자체 서명된 인증서 생성
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=KR/ST=Seoul/L=Seoul/O=OntologyChat/CN=localhost"
        
        log_success "자체 서명된 SSL 인증서 생성 완료"
    else
        log_success "SSL 인증서 확인 완료"
    fi
}

# Docker 이미지 빌드
build_images() {
    log_info "Docker 이미지 빌드 중..."
    
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    log_success "Docker 이미지 빌드 완료"
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
