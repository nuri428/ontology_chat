# 🦙 Ollama 모델 설치 및 설정 가이드

## 📋 권장 모델 목록

### 🎯 추천 모델 (성능/효율성 균형)

#### 1. **Llama 3.1 시리즈** ⭐⭐⭐⭐⭐
```bash
# 8B 모델 (권장 - 균형잡힌 성능)
ollama pull llama3.1:8b

# 70B 모델 (고성능 - 32GB+ RAM 필요)
ollama pull llama3.1:70b

# 8B Instruct 모델 (지시사항 특화)
ollama pull llama3.1:8b-instruct
```

#### 2. **Qwen 2.5 시리즈** ⭐⭐⭐⭐⭐
```bash
# 7B 모델 (한국어/중국어/영어 우수)
ollama pull qwen2.5:7b

# 14B 모델 (더 나은 성능)
ollama pull qwen2.5:14b

# 32B 모델 (최고 성능)
ollama pull qwen2.5:32b
```

#### 3. **Mistral 시리즈** ⭐⭐⭐⭐
```bash
# 7B 모델 (효율적)
ollama pull mistral:7b

# Nemo 모델 (최신)
ollama pull mistral-nemo:12b
```

### 🇰🇷 한국어 특화 모델

#### 1. **EEVE-Korean** ⭐⭐⭐⭐⭐
```bash
# 한국어 특화 10.8B 모델
ollama pull eeve-korean:10.8b

# 2.8B 경량 버전
ollama pull eeve-korean:2.8b
```

#### 2. **Korean-LLaMA** ⭐⭐⭐⭐
```bash
# 한국어 파인튜닝된 LLaMA
ollama pull korean-llama:13b
```

### ⚡ 경량 모델 (리소스 제한 환경)

#### 1. **Gemma 2 시리즈** ⭐⭐⭐⭐
```bash
# 2B 모델 (매우 빠름)
ollama pull gemma2:2b

# 9B 모델 (좋은 균형)
ollama pull gemma2:9b
```

#### 2. **Phi-3 시리즈** ⭐⭐⭐
```bash
# 3.8B 모델 (작고 빠름)
ollama pull phi3:3.8b

# 14B 모델
ollama pull phi3:14b
```

## 🛠 Ollama 설치

### Linux/macOS
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Windows
1. https://ollama.com/download 에서 다운로드
2. 설치 프로그램 실행

### Docker
```bash
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

## ⚙️ 환경 설정

### .env 파일 설정
```env
# Ollama LLM 설정
OLLAMA_HOST=localhost
OLLAMA_MODEL=llama3.1:8b

# 원격 Ollama 서버 사용시
# OLLAMA_HOST=192.168.1.100
```

### config/__init__.py 확인
현재 설정된 모델:
- `ollama_model: str = "gpt-oss:latest"`

권장 변경:
```python
ollama_model: str = "llama3.1:8b"  # 또는 선호하는 모델
```

## 🚀 성능별 모델 선택 가이드

### 🏆 고성능 (32GB+ RAM)
```bash
ollama pull llama3.1:70b        # 최고 성능
ollama pull qwen2.5:32b         # 한국어 우수
```

### ⚖️ 균형형 (16GB+ RAM)
```bash
ollama pull llama3.1:8b         # 권장
ollama pull qwen2.5:14b         # 한국어 중점
ollama pull eeve-korean:10.8b   # 한국어 특화
```

### ⚡ 경량형 (8GB+ RAM)
```bash
ollama pull qwen2.5:7b          # 권장
ollama pull gemma2:9b           # 빠른 응답
ollama pull mistral:7b          # 효율적
```

### 💨 초경량 (4GB+ RAM)
```bash
ollama pull gemma2:2b           # 가장 빠름
ollama pull phi3:3.8b           # 작고 효율적
ollama pull eeve-korean:2.8b    # 한국어 경량
```

## 🔧 성능 최적화

### GPU 사용 (NVIDIA)
```bash
# CUDA 지원 확인
nvidia-smi

# GPU 메모리 확인 후 큰 모델 사용
ollama pull llama3.1:70b
```

### CPU 최적화
```bash
# CPU 코어 수 설정
export OLLAMA_NUM_PARALLEL=4

# 메모리 제한 설정
export OLLAMA_MAX_LOADED_MODELS=2
```

## 📊 모델 비교표

| 모델 | 크기 | RAM 필요 | 한국어 | 성능 | 속도 | 추천도 |
|------|------|----------|--------|------|------|--------|
| llama3.1:8b | 4.7GB | 8GB+ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| qwen2.5:7b | 4.4GB | 8GB+ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| eeve-korean:10.8b | 6.2GB | 12GB+ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| gemma2:2b | 1.6GB | 4GB+ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| llama3.1:70b | 40GB | 64GB+ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |

## 🧪 테스트 실행

### 설치 후 테스트
```bash
# 모델 다운로드
ollama pull llama3.1:8b

# 서비스 시작 확인
ollama serve

# 통합 테스트 실행
python3 test_ollama_integration.py
```

### 응답 속도 벤치마크
```bash
# 간단한 테스트
ollama run llama3.1:8b "안녕하세요"

# 키워드 추출 테스트
ollama run llama3.1:8b "삼성전자 반도체 투자에서 핵심 키워드 5개 추출해주세요"
```

## 🛡️ 문제 해결

### 1. 모델 다운로드 실패
```bash
# 네트워크 확인
curl -I https://ollama.com

# 공간 확인
df -h

# 재시도
ollama pull llama3.1:8b
```

### 2. 메모리 부족
```bash
# 작은 모델 사용
ollama pull gemma2:2b

# 기존 모델 제거
ollama rm unused_model
```

### 3. 연결 오류
```bash
# 서비스 상태 확인
systemctl status ollama

# 포트 확인
netstat -tulpn | grep 11434

# 재시작
ollama serve
```

## 💡 사용 팁

1. **첫 설치시 권장**: `llama3.1:8b` 또는 `qwen2.5:7b`
2. **한국어 중요시**: `eeve-korean:10.8b` 또는 `qwen2.5:14b`
3. **빠른 응답 필요**: `gemma2:2b` 또는 `phi3:3.8b`
4. **최고 품질**: `llama3.1:70b` (충분한 RAM 필요)
5. **개발/테스트**: 작은 모델로 시작 후 점진적 업그레이드

이 가이드를 따라 설치하면 온톨로지 챗 시스템에서 Ollama를 최적으로 활용할 수 있습니다! 🚀