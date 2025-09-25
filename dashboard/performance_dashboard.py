"""
Ontology Chat - Performance Analytics Dashboard

실시간 성능 모니터링 및 분석을 위한 Streamlit 기반 웹 대시보드
A-grade 품질 유지 및 시스템 성능 최적화를 위한 종합적인 시각화 제공
"""

import asyncio
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import time
import json

# 페이지 설정
st.set_page_config(
    page_title="Ontology Chat Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일링
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }

    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }

    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }

    .status-healthy { color: #28a745; font-weight: bold; }
    .status-warning { color: #ffc107; font-weight: bold; }
    .status-critical { color: #dc3545; font-weight: bold; }

    .cache-level {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# API 엔드포인트 설정
API_BASE = "http://localhost:8000"

class DashboardAPI:
    """Dashboard API client"""

    @staticmethod
    def get_dashboard_data():
        """대시보드 데이터 가져오기"""
        try:
            response = requests.get(f"{API_BASE}/analytics/dashboard", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            st.error(f"API 연결 실패: {str(e)}")
            return None

    @staticmethod
    def get_performance_history(period="24h"):
        """성능 히스토리 데이터 가져오기"""
        try:
            response = requests.get(f"{API_BASE}/analytics/performance/history?period={period}", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            st.error(f"히스토리 데이터 가져오기 실패: {str(e)}")
            return None

    @staticmethod
    def get_cache_analysis():
        """캐시 분석 데이터 가져오기"""
        try:
            response = requests.get(f"{API_BASE}/analytics/cache/analysis", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            st.error(f"캐시 분석 데이터 가져오기 실패: {str(e)}")
            return None


def main():
    """메인 대시보드"""

    # 헤더
    st.markdown('<h1 class="main-header">🚀 Ontology Chat Performance Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("**A-Grade Quality Monitoring & System Performance Analytics**")

    # 사이드바 설정
    st.sidebar.header("⚙️ Dashboard Settings")

    # 자동 새로고침 설정
    auto_refresh = st.sidebar.checkbox("Auto Refresh (30s)", value=True)
    if auto_refresh:
        time.sleep(30)
        st.rerun()

    # 시간 범위 설정
    time_range = st.sidebar.selectbox(
        "📅 Time Range",
        ["1h", "6h", "24h", "7d", "30d"],
        index=2
    )

    # 새로고침 버튼
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # 대시보드 데이터 로드
    dashboard_data = load_dashboard_data()

    if dashboard_data is None:
        st.error("⚠️ Unable to load dashboard data. Please check if the API server is running.")
        st.info("Start the API server: `uvicorn api.main:app --reload`")
        return

    # 메인 메트릭 표시
    render_main_metrics(dashboard_data)

    # 탭 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Real-time Overview",
        "🏎️ Performance Trends",
        "💾 Cache Analytics",
        "⭐ Quality Analysis",
        "🚨 System Health"
    ])

    with tab1:
        render_realtime_overview(dashboard_data)

    with tab2:
        render_performance_trends(time_range)

    with tab3:
        render_cache_analytics()

    with tab4:
        render_quality_analysis(dashboard_data)

    with tab5:
        render_system_health(dashboard_data)


@st.cache_data(ttl=30)
def load_dashboard_data():
    """대시보드 데이터 로드 (30초 캐시)"""
    return DashboardAPI.get_dashboard_data()


def render_main_metrics(data):
    """메인 메트릭 카드 렌더링"""
    summary = data.get("summary", {})
    real_time = data.get("real_time_metrics", {})

    # 4개 컬럼으로 주요 메트릭 표시
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        quality_score = real_time.get("quality_score", 0)
        quality_status = "🟢" if quality_score >= 0.900 else "🟡" if quality_score >= 0.850 else "🔴"
        st.metric(
            label="A-Grade Quality Score",
            value=f"{quality_score:.3f}",
            delta=f"{quality_status} {'A-Grade' if quality_score >= 0.900 else 'Below A-Grade'}"
        )

    with col2:
        response_time = real_time.get("response_time_ms", 0)
        response_status = "🟢" if response_time < 100 else "🟡" if response_time < 200 else "🔴"
        st.metric(
            label="Avg Response Time",
            value=f"{response_time:.1f}ms",
            delta=f"{response_status} {'Excellent' if response_time < 100 else 'Good' if response_time < 200 else 'Needs Attention'}"
        )

    with col3:
        cache_hit_rate = real_time.get("cache_hit_rate", 0)
        cache_status = "🟢" if cache_hit_rate > 0.8 else "🟡" if cache_hit_rate > 0.6 else "🔴"
        st.metric(
            label="Cache Hit Rate",
            value=f"{cache_hit_rate:.1%}",
            delta=f"{cache_status} {'Excellent' if cache_hit_rate > 0.8 else 'Good' if cache_hit_rate > 0.6 else 'Suboptimal'}"
        )

    with col4:
        requests_per_min = real_time.get("requests_per_minute", 0)
        throughput_status = "🟢" if requests_per_min > 10 else "🟡" if requests_per_min > 5 else "🔴"
        st.metric(
            label="Requests/Minute",
            value=f"{requests_per_min:.1f}",
            delta=f"{throughput_status} {'High Traffic' if requests_per_min > 10 else 'Normal' if requests_per_min > 5 else 'Low Traffic'}"
        )


def render_realtime_overview(data):
    """실시간 개요 렌더링"""
    st.header("📊 Real-time System Overview")

    real_time = data.get("real_time_metrics", {})

    # 실시간 차트 생성
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 Quality & Performance")

        # 게이지 차트 - 품질 점수
        quality_score = real_time.get("quality_score", 0)

        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = quality_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Quality Score"},
            delta = {'reference': 0.900},
            gauge = {
                'axis': {'range': [0, 1.0]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 0.850], 'color': "lightgray"},
                    {'range': [0.850, 0.900], 'color': "yellow"},
                    {'range': [0.900, 1.0], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0.900
                }
            }
        ))
        fig_gauge.update_layout(height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        st.subheader("⚡ Response Time Distribution")

        # 히스토그램 - 응답 시간 분포 (모킹 데이터)
        response_times = [
            real_time.get("response_time_ms", 50) + (i * 5) for i in range(-10, 11)
        ]

        fig_hist = px.histogram(
            x=response_times,
            nbins=20,
            title="Response Time Distribution",
            labels={'x': 'Response Time (ms)', 'y': 'Frequency'}
        )
        fig_hist.update_layout(height=300)
        st.plotly_chart(fig_hist, use_container_width=True)

    # 시스템 상태 요약
    st.subheader("🖥️ System Status Summary")

    status_cols = st.columns(4)

    with status_cols[0]:
        st.info(f"**Active Connections**\n{real_time.get('active_connections', 0)}")

    with status_cols[1]:
        error_rate = real_time.get('error_rate', 0)
        error_color = "success" if error_rate < 0.01 else "warning" if error_rate < 0.05 else "error"
        if error_color == "success":
            st.success(f"**Error Rate**\n{error_rate:.3%}")
        elif error_color == "warning":
            st.warning(f"**Error Rate**\n{error_rate:.3%}")
        else:
            st.error(f"**Error Rate**\n{error_rate:.3%}")

    with status_cols[2]:
        cache_eff = real_time.get('cache_effectiveness', 0)
        st.info(f"**Cache Effectiveness**\n{cache_eff:.1%}")

    with status_cols[3]:
        uptime_hours = data.get("summary", {}).get("uptime_hours", 0)
        st.success(f"**System Uptime**\n{uptime_hours:.1f} hours")


def render_performance_trends(time_range):
    """성능 트렌드 렌더링"""
    st.header("🏎️ Performance Trends")

    # 성능 히스토리 데이터 로드
    history_data = DashboardAPI.get_performance_history(time_range)

    if history_data is None:
        st.error("Failed to load performance history data")
        return

    data_points = history_data.get("data_points", [])

    if not data_points:
        st.warning("No historical data available")
        return

    # DataFrame 생성
    df = pd.DataFrame(data_points)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 트렌드 차트
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Quality Score Trend")
        fig_quality = px.line(
            df, x='timestamp', y='quality_score',
            title=f"Quality Score - Last {time_range}",
            labels={'quality_score': 'Quality Score', 'timestamp': 'Time'}
        )
        fig_quality.add_hline(y=0.900, line_dash="dash", line_color="red", annotation_text="A-Grade Threshold")
        fig_quality.update_layout(height=400)
        st.plotly_chart(fig_quality, use_container_width=True)

    with col2:
        st.subheader("⚡ Response Time Trend")
        fig_response = px.line(
            df, x='timestamp', y='response_time_ms',
            title=f"Response Time - Last {time_range}",
            labels={'response_time_ms': 'Response Time (ms)', 'timestamp': 'Time'}
        )
        fig_response.update_layout(height=400)
        st.plotly_chart(fig_response, use_container_width=True)

    # 캐시 및 에러율 트렌드
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("💾 Cache Hit Rate Trend")
        fig_cache = px.line(
            df, x='timestamp', y='cache_hit_rate',
            title=f"Cache Hit Rate - Last {time_range}",
            labels={'cache_hit_rate': 'Cache Hit Rate', 'timestamp': 'Time'}
        )
        fig_cache.update_layout(height=400)
        st.plotly_chart(fig_cache, use_container_width=True)

    with col4:
        st.subheader("🚨 Error Rate Trend")
        fig_error = px.line(
            df, x='timestamp', y='error_rate',
            title=f"Error Rate - Last {time_range}",
            labels={'error_rate': 'Error Rate', 'timestamp': 'Time'}
        )
        fig_error.update_layout(height=400)
        st.plotly_chart(fig_error, use_container_width=True)

    # 요약 통계
    st.subheader("📊 Period Summary")
    summary = history_data.get("summary", {})

    summary_cols = st.columns(3)
    with summary_cols[0]:
        st.metric("Avg Quality Score", f"{summary.get('avg_quality_score', 0):.3f}")
    with summary_cols[1]:
        st.metric("Avg Response Time", f"{summary.get('avg_response_time', 0):.1f}ms")
    with summary_cols[2]:
        st.metric("Avg Cache Hit Rate", f"{summary.get('avg_cache_hit_rate', 0):.1%}")


def render_cache_analytics():
    """캐시 분석 렌더링"""
    st.header("💾 Cache Performance Analytics")

    cache_data = DashboardAPI.get_cache_analysis()

    if cache_data is None:
        st.error("Failed to load cache analysis data")
        return

    # 전체 캐시 성능
    overall = cache_data.get("overall_performance", {})

    st.subheader("🏆 Overall Cache Performance")

    perf_cols = st.columns(4)
    with perf_cols[0]:
        hit_rate = overall.get("hit_rate", 0)
        st.metric("Overall Hit Rate", f"{hit_rate:.1%}")

    with perf_cols[1]:
        effectiveness = overall.get("effectiveness_score", 0)
        st.metric("Effectiveness Score", f"{effectiveness:.3f}")

    with perf_cols[2]:
        improvement = overall.get("response_time_improvement", "0%")
        st.metric("Response Time Improvement", improvement)

    with perf_cols[3]:
        quality_contrib = overall.get("quality_contribution", 0)
        st.metric("Quality Contribution", f"{quality_contrib:.3f}")

    # 레벨별 분석
    st.subheader("🏗️ Multi-Level Cache Analysis")

    level_analysis = cache_data.get("level_analysis", {})

    # L1, L2, L3 탭
    l1_tab, l2_tab, l3_tab = st.tabs(["🚀 L1 Memory", "🌐 L2 Redis", "💽 L3 Disk"])

    with l1_tab:
        render_cache_level_analysis("L1 Memory Cache", level_analysis.get("l1_memory", {}))

    with l2_tab:
        render_cache_level_analysis("L2 Redis Cache", level_analysis.get("l2_redis", {}))

    with l3_tab:
        render_cache_level_analysis("L3 Disk Cache", level_analysis.get("l3_disk", {}))

    # 캐시 패턴 분석
    st.subheader("📈 Cache Usage Patterns")

    patterns = cache_data.get("cache_patterns", {})
    hot_queries = patterns.get("hot_queries", [])

    if hot_queries:
        st.write("**🔥 Hot Queries:**")
        hot_df = pd.DataFrame(hot_queries)
        st.dataframe(hot_df, use_container_width=True)

    # 최적화 제안
    suggestions = cache_data.get("optimization_suggestions", [])
    if suggestions:
        st.subheader("💡 Optimization Suggestions")
        for i, suggestion in enumerate(suggestions, 1):
            st.info(f"**{i}.** {suggestion}")


def render_cache_level_analysis(level_name, data):
    """캐시 레벨별 분석 렌더링"""
    st.write(f"### {level_name}")

    if not data:
        st.warning(f"{level_name} data not available")
        return

    cols = st.columns(3)

    with cols[0]:
        hit_rate = data.get("hit_rate", 0)
        hit_color = "success" if hit_rate > 0.6 else "warning" if hit_rate > 0.3 else "error"
        if hit_color == "success":
            st.success(f"**Hit Rate**: {hit_rate:.1%}")
        elif hit_color == "warning":
            st.warning(f"**Hit Rate**: {hit_rate:.1%}")
        else:
            st.error(f"**Hit Rate**: {hit_rate:.1%}")

    with cols[1]:
        efficiency = data.get("efficiency_score", 0)
        st.metric("Efficiency Score", f"{efficiency:.2f}")

    with cols[2]:
        access_time = data.get("avg_access_time_ms", 0)
        st.metric("Avg Access Time", f"{access_time:.1f}ms")

    # 추가 메트릭
    if "memory_utilization" in data:
        st.progress(data["memory_utilization"] / 100.0)
        st.caption(f"Memory Utilization: {data['memory_utilization']:.1f}%")

    if "disk_utilization" in data:
        st.progress(data["disk_utilization"] / 100.0)
        st.caption(f"Disk Utilization: {data['disk_utilization']:.1f}%")

    if "connection_status" in data:
        status = data["connection_status"]
        if status:
            st.success("✅ Connected")
        else:
            st.error("❌ Disconnected")

    # 권장사항
    recommendation = data.get("recommendation", "")
    if recommendation:
        st.info(f"**💡 Recommendation:** {recommendation}")


def render_quality_analysis(data):
    """품질 분석 렌더링"""
    st.header("⭐ A-Grade Quality Analysis")

    # 현재 품질 상태
    quality_analysis = data.get("quality_analysis", {})
    current_score = quality_analysis.get("current_score", 0.949)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 Quality Status")

        grade = "A" if current_score >= 0.900 else "B" if current_score >= 0.800 else "C"
        grade_color = "success" if grade == "A" else "warning" if grade == "B" else "error"

        if grade_color == "success":
            st.success(f"**Current Grade: {grade}**")
        elif grade_color == "warning":
            st.warning(f"**Current Grade: {grade}**")
        else:
            st.error(f"**Current Grade: {grade}**")

        st.metric("Quality Score", f"{current_score:.3f}")
        st.metric("Threshold Margin", f"+{current_score - 0.900:.3f}")

    with col2:
        st.subheader("📊 Contributing Factors")

        factors = quality_analysis.get("contributing_factors", {})

        # 기여 요소 차트
        if factors:
            factor_names = []
            factor_values = []

            for name, info in factors.items():
                factor_names.append(name.replace("_", " ").title())
                factor_values.append(info.get("score", 0) if isinstance(info, dict) else info)

            fig_factors = px.bar(
                x=factor_names,
                y=factor_values,
                title="Quality Contributing Factors",
                labels={'x': 'Factors', 'y': 'Contribution Score'}
            )
            st.plotly_chart(fig_factors, use_container_width=True)

    # 품질 히스토리
    st.subheader("📈 Quality History")

    # Mock quality history data
    quality_history = [
        {"date": datetime.now() - timedelta(days=i), "score": 0.949 + (i * 0.001)}
        for i in range(30, 0, -1)
    ]

    df_quality = pd.DataFrame(quality_history)

    fig_quality_history = px.line(
        df_quality, x='date', y='score',
        title="Quality Score - Last 30 Days",
        labels={'score': 'Quality Score', 'date': 'Date'}
    )
    fig_quality_history.add_hline(y=0.900, line_dash="dash", line_color="red", annotation_text="A-Grade Threshold")
    st.plotly_chart(fig_quality_history, use_container_width=True)


def render_system_health(data):
    """시스템 헬스 렌더링"""
    st.header("🚨 System Health & Alerts")

    system_health = data.get("system_health", {})
    components = system_health.get("components", {})

    st.subheader("🔧 Component Status")

    # 컴포넌트 상태
    for component_name, component_info in components.items():
        with st.expander(f"{component_name.replace('_', ' ').title()}", expanded=True):

            if isinstance(component_info, dict):
                status = component_info.get("status", "unknown")

                if status == "healthy":
                    st.success(f"✅ {component_name} is healthy")
                elif status == "degraded":
                    st.warning(f"⚠️ {component_name} is degraded")
                else:
                    st.error(f"❌ {component_name} has issues")

                # 상세 정보 표시
                for key, value in component_info.items():
                    if key != "status":
                        st.text(f"{key}: {value}")

    # 활성 알림
    alerts = system_health.get("alerts", [])

    if alerts:
        st.subheader("🚨 Active Alerts")

        for alert in alerts:
            severity = alert.get("severity", "info")
            message = alert.get("message", "No message")

            if severity == "critical":
                st.error(f"🔴 **CRITICAL**: {message}")
            elif severity == "warning":
                st.warning(f"🟡 **WARNING**: {message}")
            else:
                st.info(f"🔵 **INFO**: {message}")
    else:
        st.success("✅ No active alerts")

    # 권장사항
    recommendations = system_health.get("recommendations", [])

    if recommendations:
        st.subheader("💡 System Recommendations")
        for i, rec in enumerate(recommendations, 1):
            st.info(f"**{i}.** {rec}")


if __name__ == "__main__":
    main()