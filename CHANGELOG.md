# Changelog

모든 주요 변경사항은 이 파일에 기록됩니다.

## [0.1.0] - 2025-09-16

### Added
- ✅ FastAPI 기반 RESTful API 서버 구축
- ✅ Streamlit 기반 웹 UI 구현
- ✅ Neo4j 그래프 데이터베이스 연동
- ✅ OpenSearch 벡터 검색 엔진 연동
- ✅ MCP (Model Context Protocol) 어댑터 시스템
- ✅ 실시간 뉴스 검색 및 분석 기능
- ✅ 인터랙티브 그래프 시각화 (pyvis)
- ✅ Docker 개발/운영 환경 구축
- ✅ 강력한 오류 처리 및 재시도 메커니즘
- ✅ 캐싱 시스템으로 성능 최적화
- ✅ 컨텍스트 엔지니어링 기반 키워드 추출
- ✅ 다단계 검색 전략 구현

### Fixed
- 🔧 OpenSearch UTF-8 인코딩 문제 해결
- 🔧 Neo4j 쿼리 관계 데이터 포함 개선
- 🔧 pyvis 그래프 안정화 문제 해결
- 🔧 시스템 장애 메시지 원인 파악 및 해결
- 🔧 Docker 환경 의존성 문제 해결

### Performance
- ⚡ 뉴스 검색: 3ms (60만+ 문서)
- ⚡ 그래프 검색: 5ms (관계 포함)
- ⚡ API 응답: < 1.5초
- ⚡ 캐싱으로 반복 요청 최적화

### Technical Details
- **Backend**: Python 3.12+, FastAPI, Pydantic, Loguru
- **Frontend**: Streamlit, pyvis, Pandas
- **Database**: Neo4j (60만+ 뉴스), OpenSearch (30만+ 문서)
- **Infrastructure**: Docker, Docker Compose, Nginx
- **Code**: 31개 Python 파일, 8,500+ 라인

### Known Issues
- ⏳ LangGraph 파이프라인 미구현 (10% 진행)
- ⏳ CLI 인터페이스 기본 구조만 존재 (30% 진행)
- ⏳ 테스트 환경 미구축 (0% 진행)

---

## [Unreleased]

### Planned
- 🔮 LangGraph 파이프라인 완전 구현
- 🔮 CLI 인터페이스 확장
- 🔮 포괄적인 테스트 환경 구축
- 🔮 성능 모니터링 대시보드
- 🔮 사용자 인증 및 권한 관리



