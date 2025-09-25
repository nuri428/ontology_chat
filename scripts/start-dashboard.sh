#!/bin/bash

# Ontology Chat Performance Dashboard Startup Script
# Streamlit 기반 성능 분석 대시보드 실행

set -e

echo "🚀 Starting Ontology Chat Performance Dashboard..."

# 현재 디렉토리 확인
if [ ! -f "dashboard/performance_dashboard.py" ]; then
    echo "❌ Dashboard script not found. Please run this script from the project root directory."
    exit 1
fi

# Python 의존성 확인
echo "📦 Checking dependencies..."

# Streamlit 설치 확인
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "⚠️  Streamlit not found. Installing..."
    pip install streamlit plotly
fi

# Plotly 설치 확인
if ! python3 -c "import plotly" 2>/dev/null; then
    echo "⚠️  Plotly not found. Installing..."
    pip install plotly
fi

# API 서버 상태 확인
echo "🔍 Checking API server status..."

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API server is running at http://localhost:8000"
else
    echo "⚠️  API server is not responding. Please start the API server first:"
    echo "   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    echo "🔄 Proceeding with dashboard startup (dashboard will show connection errors until API is available)..."
fi

# Streamlit 설정 생성
mkdir -p .streamlit

cat > .streamlit/config.toml << EOF
[server]
port = 8501
address = "0.0.0.0"
headless = false
enableWebsocketCompression = true
enableXsrfProtection = false

[browser]
gatherUsageStats = false
serverAddress = "localhost"
serverPort = 8501

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[global]
developmentMode = false
logLevel = "info"
EOF

echo ""
echo "📊 Starting Streamlit Dashboard..."
echo "   Dashboard URL: http://localhost:8501"
echo "   API Server: http://localhost:8000"
echo ""
echo "🔧 Dashboard Features:"
echo "   - Real-time performance monitoring"
echo "   - A-grade quality tracking"
echo "   - Multi-level cache analytics"
echo "   - System health monitoring"
echo "   - Historical trend analysis"
echo ""
echo "⚡ Dashboard will auto-refresh every 30 seconds"
echo "🛑 Press Ctrl+C to stop the dashboard"
echo ""

# Streamlit 실행
cd dashboard
streamlit run performance_dashboard.py --server.address 0.0.0.0 --server.port 8501

echo ""
echo "✨ Dashboard stopped successfully!"