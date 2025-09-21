#!/bin/bash

# FastAPI-MCP 서버 실행 스크립트

echo "🚀 Ontology Chat FastAPI-MCP 서버 시작..."

# 환경 변수 확인
echo "환경 변수 확인 중..."

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY가 설정되지 않았습니다."
fi

if [ -z "$NEO4J_URI" ]; then
    echo "⚠️  NEO4J_URI가 설정되지 않았습니다."
fi

if [ -z "$OPENSEARCH_HOST" ]; then
    echo "⚠️  OPENSEARCH_HOST가 설정되지 않았습니다."
fi

# Python 경로 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd):/home/nuri/.local/lib/python3.10/site-packages"

echo "Python 경로: $PYTHONPATH"
echo "작업 디렉터리: $(pwd)"

# FastAPI 서버 실행 (MCP 지원 포함)
echo "FastAPI-MCP 서버를 시작합니다..."
echo "API 문서: http://127.0.0.1:8000/docs"
echo "MCP 엔드포인트가 자동으로 추가됩니다."
echo "종료하려면 Ctrl+C를 누르세요."
echo ""

uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload