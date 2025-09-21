"""
Enhanced UI components for the new listed company schema
새로운 상장사 스키마에 맞춘 향상된 UI 컴포넌트들
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Any, Dict, List, Optional

def display_listed_company_info(companies: List[Dict[str, Any]]) -> None:
    """상장사 정보 표시"""
    if not companies:
        st.info("상장사 정보가 없습니다.")
        return

    st.subheader("📈 주요 상장사")

    # 테이블 형식으로 표시
    company_data = []
    for company in companies:
        name = company.get("name", "")
        ticker = company.get("ticker", "")
        market = company.get("market", "")
        sector = company.get("sector", "")
        market_cap = company.get("market_cap", 0)

        company_data.append({
            "기업명": name,
            "티커": ticker,
            "거래소": market,
            "업종": sector,
            "시가총액(억원)": f"{market_cap:,.0f}" if market_cap else "-"
        })

    df = pd.DataFrame(company_data)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "기업명": st.column_config.TextColumn("기업명", width="large"),
            "티커": st.column_config.TextColumn("티커", width="small"),
            "거래소": st.column_config.TextColumn("거래소", width="small"),
            "업종": st.column_config.TextColumn("업종", width="medium"),
            "시가총액(억원)": st.column_config.TextColumn("시가총액", width="medium")
        }
    )

def display_financial_summary(financial_summary: Dict[str, Any]) -> None:
    """재무 요약 정보 표시"""
    if not financial_summary or not any(financial_summary.values()):
        return

    st.subheader("💰 재무 정보")

    col1, col2, col3 = st.columns(3)

    with col1:
        total_revenue = financial_summary.get("total_revenue", 0)
        if total_revenue > 0:
            st.metric("총 매출", f"{total_revenue:,.0f}억원")

    with col2:
        total_operating_profit = financial_summary.get("total_operating_profit", 0)
        if total_operating_profit > 0:
            st.metric("총 영업이익", f"{total_operating_profit:,.0f}억원")

    with col3:
        revenue_companies = financial_summary.get("revenue_companies", 0)
        if revenue_companies > 0:
            st.metric("실적 발표 기업", f"{revenue_companies}개사")

def display_investment_summary(investment_summary: Dict[str, Any]) -> None:
    """투자 요약 정보 표시"""
    if not investment_summary or not any(investment_summary.values()):
        return

    st.subheader("💼 투자 정보")

    col1, col2, col3 = st.columns(3)

    with col1:
        total_amount = investment_summary.get("total_amount", 0)
        if total_amount > 0:
            st.metric("총 투자 규모", f"{total_amount:,.0f}억원")

    with col2:
        count = investment_summary.get("count", 0)
        if count > 0:
            st.metric("투자 건수", f"{count}건")

    with col3:
        types = investment_summary.get("types", [])
        if types:
            st.metric("투자 유형", f"{len(types)}가지")
            st.caption(f"유형: {', '.join(types)}")

def display_enhanced_graph_metrics(graph_metrics: Dict[str, Any]) -> None:
    """향상된 그래프 메트릭 표시"""
    st.subheader("🔍 그래프 분석 결과")

    # 라벨 분포 차트
    if graph_metrics.get("label_distribution"):
        st.markdown("#### 📊 데이터 타입 분포")

        label_data = graph_metrics["label_distribution"][:8]  # 상위 8개만
        labels = [item[0] for item in label_data]
        counts = [item[1] for item in label_data]

        # 파이 차트로 표시
        fig = px.pie(
            values=counts,
            names=labels,
            title="데이터 타입별 분포",
            hole=0.3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

    # 상장사 정보
    if graph_metrics.get("listed_companies"):
        display_listed_company_info(graph_metrics["listed_companies"])

    # 재무 정보
    if graph_metrics.get("financial_summary"):
        display_financial_summary(graph_metrics["financial_summary"])

    # 투자 정보
    if graph_metrics.get("investment_summary"):
        display_investment_summary(graph_metrics["investment_summary"])

    # 기타 엔터티 정보
    st.markdown("#### 🏢 연관 엔터티")

    col1, col2 = st.columns(2)

    with col1:
        if graph_metrics.get("companies_top"):
            st.markdown("**주요 기업**")
            for i, company in enumerate(graph_metrics["companies_top"][:5], 1):
                st.text(f"{i}. {company}")

        if graph_metrics.get("products_top"):
            st.markdown("**관련 제품**")
            for i, product in enumerate(graph_metrics["products_top"][:5], 1):
                st.text(f"{i}. {product}")

    with col2:
        if graph_metrics.get("programs_top"):
            st.markdown("**연관 프로그램**")
            for i, program in enumerate(graph_metrics["programs_top"][:5], 1):
                st.text(f"{i}. {program}")

        if graph_metrics.get("products_top"):
            st.markdown("**관련 제품/시스템**")
            for i, product in enumerate(graph_metrics["products_top"][:5], 1):
                st.text(f"{i}. {product}")
        elif graph_metrics.get("weapons_top"):  # 호환성 유지
            st.markdown("**관련 시스템**")
            for i, weapon in enumerate(graph_metrics["weapons_top"][:5], 1):
                st.text(f"{i}. {weapon}")

def display_event_analysis(events_sample: List[Dict[str, Any]]) -> None:
    """이벤트 분석 표시"""
    if not events_sample:
        return

    st.subheader("📅 주요 이벤트")

    # 이벤트 타입별 분포
    event_types = [event.get("event_type", "Unknown") for event in events_sample]
    event_type_counts = pd.Series(event_types).value_counts()

    if len(event_type_counts) > 1:
        fig = px.bar(
            x=event_type_counts.values,
            y=event_type_counts.index,
            orientation='h',
            title="이벤트 타입별 분포",
            labels={'x': '건수', 'y': '이벤트 타입'}
        )
        st.plotly_chart(fig, use_container_width=True)

    # 감정 분석
    sentiments = [event.get("sentiment", "Unknown") for event in events_sample if event.get("sentiment")]
    if sentiments:
        sentiment_counts = pd.Series(sentiments).value_counts()

        col1, col2 = st.columns(2)
        with col1:
            # 감정 분포 파이 차트
            fig = px.pie(
                values=sentiment_counts.values,
                names=sentiment_counts.index,
                title="감정 분석 결과",
                color_discrete_map={
                    'positive': '#28a745',
                    'neutral': '#6c757d',
                    'negative': '#dc3545'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # 신뢰도 분포
            confidences = [event.get("confidence", 0) for event in events_sample if event.get("confidence")]
            if confidences:
                fig = px.histogram(
                    x=confidences,
                    nbins=10,
                    title="신뢰도 분포",
                    labels={'x': '신뢰도', 'y': '빈도'}
                )
                st.plotly_chart(fig, use_container_width=True)

def display_comparative_analysis_chart(comparisons: List[Dict[str, Any]]) -> None:
    """비교 분석 차트 표시"""
    if not comparisons:
        return

    st.subheader("📊 비교 분석 차트")

    # 데이터 준비
    companies = [comp.get("query", "") for comp in comparisons]
    contract_totals = [comp.get("contract_total", 0) for comp in comparisons]
    news_counts = [comp.get("news_count", 0) for comp in comparisons]

    # 이중 축 차트
    fig = go.Figure()

    # 계약 규모 (첫 번째 y축)
    fig.add_trace(go.Bar(
        name='계약 규모 (억원)',
        x=companies,
        y=contract_totals,
        yaxis='y',
        offsetgroup=1,
        marker_color='lightblue'
    ))

    # 뉴스 건수 (두 번째 y축)
    fig.add_trace(go.Bar(
        name='뉴스 건수',
        x=companies,
        y=news_counts,
        yaxis='y2',
        offsetgroup=2,
        marker_color='lightcoral'
    ))

    # 레이아웃 설정
    fig.update_layout(
        title='기업별 계약 규모 vs 뉴스 활동',
        xaxis=dict(title='기업'),
        yaxis=dict(
            title='계약 규모 (억원)',
            side='left'
        ),
        yaxis2=dict(
            title='뉴스 건수',
            side='right',
            overlaying='y'
        ),
        barmode='group'
    )

    st.plotly_chart(fig, use_container_width=True)

def display_trend_analysis_chart(trend_data: List[Dict[str, Any]]) -> None:
    """트렌드 분석 차트 표시"""
    if not trend_data:
        return

    st.subheader("📈 트렌드 분석 차트")

    # 데이터 준비
    periods = [f"{trend.get('period', 0)}일" for trend in trend_data]
    contract_totals = [trend.get("contract_total", 0) for trend in trend_data]
    news_counts = [trend.get("news_count", 0) for trend in trend_data]
    graph_nodes = [trend.get("graph_nodes", 0) for trend in trend_data]

    # 멀티 메트릭 트렌드 차트
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=periods,
        y=contract_totals,
        mode='lines+markers',
        name='계약 규모 (억원)',
        yaxis='y'
    ))

    fig.add_trace(go.Scatter(
        x=periods,
        y=news_counts,
        mode='lines+markers',
        name='뉴스 건수',
        yaxis='y2'
    ))

    fig.add_trace(go.Scatter(
        x=periods,
        y=graph_nodes,
        mode='lines+markers',
        name='그래프 노드 수',
        yaxis='y3'
    ))

    # 레이아웃 설정
    fig.update_layout(
        title='기간별 트렌드 분석',
        xaxis=dict(title='분석 기간'),
        yaxis=dict(
            title='계약 규모 (억원)',
            side='left'
        ),
        yaxis2=dict(
            title='뉴스 건수',
            side='right',
            overlaying='y'
        ),
        yaxis3=dict(
            title='그래프 노드 수',
            side='right',
            overlaying='y',
            position=0.95
        )
    )

    st.plotly_chart(fig, use_container_width=True)

def display_sector_analysis(companies: List[Dict[str, Any]]) -> None:
    """업종별 분석 표시"""
    if not companies:
        return

    # 업종별 시가총액 분포
    sector_data = {}
    for company in companies:
        sector = company.get("sector", "기타")
        market_cap = company.get("market_cap", 0)

        if sector not in sector_data:
            sector_data[sector] = {"count": 0, "total_market_cap": 0}

        sector_data[sector]["count"] += 1
        sector_data[sector]["total_market_cap"] += market_cap

    if len(sector_data) > 1:
        st.subheader("🏭 업종별 분석")

        sectors = list(sector_data.keys())
        counts = [data["count"] for data in sector_data.values()]
        market_caps = [data["total_market_cap"] for data in sector_data.values()]

        col1, col2 = st.columns(2)

        with col1:
            # 업종별 기업 수
            fig = px.pie(
                values=counts,
                names=sectors,
                title="업종별 기업 수 분포"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # 업종별 시가총액
            fig = px.bar(
                x=sectors,
                y=market_caps,
                title="업종별 시가총액 합계",
                labels={'x': '업종', 'y': '시가총액 (억원)'}
            )
            st.plotly_chart(fig, use_container_width=True)

def create_financial_dashboard(graph_metrics: Dict[str, Any]) -> None:
    """종합 재무 대시보드 생성"""
    st.header("📊 종합 재무 대시보드")

    # 메트릭 카드들
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        financial_summary = graph_metrics.get("financial_summary", {})
        total_revenue = financial_summary.get("total_revenue", 0)
        st.metric("총 매출", f"{total_revenue:,.0f}억원" if total_revenue > 0 else "N/A")

    with col2:
        total_operating_profit = financial_summary.get("total_operating_profit", 0)
        st.metric("총 영업이익", f"{total_operating_profit:,.0f}억원" if total_operating_profit > 0 else "N/A")

    with col3:
        investment_summary = graph_metrics.get("investment_summary", {})
        total_investment = investment_summary.get("total_amount", 0)
        st.metric("총 투자", f"{total_investment:,.0f}억원" if total_investment > 0 else "N/A")

    with col4:
        contract_total = graph_metrics.get("contract_total_amount", 0)
        st.metric("총 계약", f"{contract_total:,.0f}억원" if contract_total > 0 else "N/A")

    st.divider()

    # 상장사 정보
    if graph_metrics.get("listed_companies"):
        display_listed_company_info(graph_metrics["listed_companies"])
        st.divider()

    # 업종별 분석
    if graph_metrics.get("listed_companies"):
        display_sector_analysis(graph_metrics["listed_companies"])
        st.divider()

    # 이벤트 분석
    if graph_metrics.get("events_sample"):
        display_event_analysis(graph_metrics["events_sample"])

def display_quality_indicators(data: Dict[str, Any]) -> None:
    """품질 지표 표시 (LangGraph용)"""
    if "quality_score" not in data:
        return

    st.subheader("🎯 분석 품질 지표")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        quality_score = data.get("quality_score", 0)
        quality_level = data.get("quality_level", "unknown")

        # 품질 점수에 따른 색상
        if quality_score >= 0.8:
            delta_color = "normal"
        elif quality_score >= 0.6:
            delta_color = "off"
        else:
            delta_color = "inverse"

        st.metric(
            "품질 점수",
            f"{quality_score:.2f}",
            delta=f"등급: {quality_level}",
            delta_color=delta_color
        )

    with col2:
        contexts_count = data.get("contexts_count", 0)
        st.metric("수집 컨텍스트", f"{contexts_count}개")

    with col3:
        insights_count = data.get("insights_count", 0)
        st.metric("생성 인사이트", f"{insights_count}개")

    with col4:
        processing_time = data.get("processing_time", 0)
        st.metric("처리 시간", f"{processing_time:.1f}초")

    # 품질 점수 게이지 차트
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = quality_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "분석 품질 점수"},
        gauge = {
            'axis': {'range': [None, 1]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 0.5], 'color': "lightgray"},
                {'range': [0.5, 0.8], 'color': "yellow"},
                {'range': [0.8, 1], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 0.9
            }
        }
    ))

    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)