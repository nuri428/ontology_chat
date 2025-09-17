# 기여 가이드

Ontology Chat 프로젝트에 기여해주셔서 감사합니다! 이 문서는 프로젝트에 기여하는 방법을 안내합니다.

## 🚀 빠른 시작

### 1. 저장소 포크
1. GitHub에서 이 저장소를 포크합니다
2. 로컬에 클론합니다:
   ```bash
   git clone https://github.com/yourusername/ontology_chat.git
   cd ontology_chat
   ```

### 2. 개발 환경 설정
```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
uv sync

# 개발 환경 실행
make docker-dev-up
```

## 📝 기여 방법

### 1. 이슈 생성
- 버그 리포트나 기능 요청을 위해 이슈를 생성하세요
- 기존 이슈를 확인하여 중복을 피하세요

### 2. 브랜치 생성
```bash
git checkout -b feature/your-feature-name
# 또는
git checkout -b fix/your-bug-fix
```

### 3. 코드 작성
- 기존 코드 스타일을 따라주세요
- 타입 힌트를 사용해주세요
- 적절한 주석을 작성해주세요

### 4. 테스트
```bash
# API 테스트
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "테스트 질의"}'

# 헬스 체크
curl http://localhost:8000/health/ready
```

### 5. 커밋
```bash
git add .
git commit -m "feat: 새로운 기능 추가"
# 또는
git commit -m "fix: 버그 수정"
```

### 6. 푸시 및 PR 생성
```bash
git push origin feature/your-feature-name
```

## 📋 코딩 스타일

### Python
- **들여쓰기**: 4칸 공백
- **라인 길이**: 100자 이하
- **타입 힌트**: 모든 함수에 타입 힌트 사용
- **문서화**: 모든 public 함수에 docstring 작성

### 예시
```python
def search_news(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    뉴스 검색 함수
    
    Args:
        query: 검색 쿼리
        limit: 결과 개수 제한
        
    Returns:
        검색 결과 리스트
    """
    # 구현...
```

## 🧪 테스트

### 테스트 실행
```bash
# 전체 테스트
make test

# 특정 테스트
uv run pytest tests/test_chat_service.py -v
```

### 테스트 작성 가이드
- 테스트 파일은 `tests/` 디렉토리에 위치
- 파일명은 `test_*.py` 형식
- 함수명은 `test_*` 형식

## 📚 문서화

### README 업데이트
- 새로운 기능 추가 시 README.md 업데이트
- API 변경 시 문서 동기화

### 코드 주석
- 복잡한 로직에 대한 설명 추가
- TODO 주석으로 개선 사항 표시

## 🐛 버그 리포트

버그를 발견하셨나요? 다음 정보를 포함해서 이슈를 생성해주세요:

1. **버그 설명**: 무엇이 잘못되었는지
2. **재현 단계**: 버그를 재현하는 방법
3. **예상 결과**: 무엇이 일어나야 하는지
4. **실제 결과**: 실제로 무엇이 일어났는지
5. **환경 정보**: OS, Python 버전, Docker 버전 등

## ✨ 기능 요청

새로운 기능을 제안하고 싶으신가요?

1. **기능 설명**: 어떤 기능을 원하시는지
2. **사용 사례**: 어떻게 사용될 것인지
3. **대안**: 고려해본 다른 방법이 있는지

## 🔄 Pull Request 프로세스

1. **Fork** 저장소
2. **브랜치** 생성 (`feature/` 또는 `fix/` 접두사)
3. **코드** 작성 및 테스트
4. **커밋** 메시지 작성 (Conventional Commits)
5. **푸시** 및 **PR** 생성
6. **리뷰** 대응 및 수정
7. **머지** 승인 후 삭제

## 📞 도움이 필요하신가요?

- **이슈**: GitHub Issues에서 질문
- **토론**: GitHub Discussions 활용
- **이메일**: [your.email@example.com]

## 📄 라이선스

이 프로젝트에 기여하시면 MIT 라이선스 하에 코드가 배포됩니다.

---

**감사합니다! 함께 더 나은 프로젝트를 만들어가요! 🚀**



