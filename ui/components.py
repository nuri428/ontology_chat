"""
Enhanced Streamlit UI Components for Context Engineering
향상된 ChatService 메타데이터 표시용 컴포넌트들
"""
import streamlit as st
from typing import Dict, Any, Optional

def display_search_quality(meta: Dict[str, Any]) -> None:
    """검색 품질 및 전략 정보 표시"""
    if not meta:
        return
    
    # 검색 전략 정보 추출
    search_strategy = None
    search_confidence = None
    
    # meta에서 검색 정보 찾기
    for key, value in meta.items():
        if isinstance(value, dict):
            search_strategy = value.get("search_strategy")
            search_confidence = value.get("search_confidence") 
            if search_strategy:
                break
    
    if search_strategy or search_confidence:
        with st.container():
            st.markdown("#### 🔍 검색 품질 정보")
            
            col1, col2 = st.columns(2)
            with col1:
                if search_strategy:
                    st.metric(
                        label="검색 전략", 
                        value=search_strategy.replace("_", " ").title()
                    )
            
            with col2:
                if search_confidence:
                    confidence_pct = f"{search_confidence:.1%}"
                    st.metric(
                        label="검색 신뢰도", 
                        value=confidence_pct,
                        delta="높음" if search_confidence > 0.8 else "보통" if search_confidence > 0.6 else "낮음"
                    )

def display_performance_metrics(meta: Dict[str, Any]) -> None:
    """성능 지표 표시"""
    if not meta:
        return
    
    latencies = meta.get("latency_ms", {})
    total_latency = meta.get("total_latency_ms", 0)
    
    if latencies or total_latency:
        with st.container():
            st.markdown("#### ⚡ 성능 지표")
            
            # 전체 응답시간
            if total_latency:
                st.metric(
                    label="전체 응답시간", 
                    value=f"{total_latency:.0f}ms",
                    delta="빠름" if total_latency < 2000 else "보통" if total_latency < 5000 else "느림"
                )
            
            # 서비스별 응답시간
            if latencies:
                cols = st.columns(len(latencies))
                for i, (service, latency) in enumerate(latencies.items()):
                    with cols[i]:
                        service_name = {
                            "opensearch": "뉴스검색",
                            "neo4j": "그래프",
                            "stock": "주가"
                        }.get(service, service)
                        
                        st.metric(
                            label=service_name,
                            value=f"{latency:.0f}ms"
                        )

def display_system_health(meta: Dict[str, Any]) -> None:
    """시스템 상태 표시"""
    if not meta:
        return
    
    system_health = meta.get("system_health", {})
    if not system_health:
        return
    
    overall_status = system_health.get("overall_status", "UNKNOWN")
    services = system_health.get("services", {})
    
    with st.container():
        st.markdown("#### 🛡️ 시스템 상태")
        
        # 전체 상태
        status_color = {
            "HEALTHY": "🟢",
            "PARTIAL": "🟡", 
            "DEGRADED": "🟠",
            "DOWN": "🔴"
        }.get(overall_status, "⚪")
        
        st.markdown(f"**전체 상태**: {status_color} {overall_status}")
        
        # 서비스별 상태 (Expander로 접을 수 있게)
        if services:
            with st.expander("서비스별 상태 보기", expanded=False):
                for service_name, service_info in services.items():
                    if isinstance(service_info, dict):
                        status = service_info.get("status", "unknown")
                        error_count = service_info.get("error_count", 0)
                        success_count = service_info.get("success_count", 0)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.text(f"{service_name}: {status}")
                        with col2:
                            st.text(f"성공: {success_count}")
                        with col3:
                            st.text(f"오류: {error_count}")

def display_error_info(meta: Dict[str, Any]) -> None:
    """오류 정보 표시"""
    if not meta:
        return
    
    errors = meta.get("errors", {})
    services_attempted = meta.get("services_attempted", [])
    
    if errors or services_attempted:
        # 오류가 있는 경우만 표시
        error_services = [k for k, v in errors.items() if v]
        
        if error_services:
            with st.container():
                st.markdown("#### ⚠️ 서비스 이슈")
                
                for service in error_services:
                    error_msg = errors[service]
                    st.warning(f"**{service}**: {error_msg}")
        
        # 시도된 서비스 (정보용)
        if services_attempted:
            with st.expander("처리된 서비스 보기", expanded=False):
                st.write("다음 서비스들이 처리되었습니다:")
                for service in services_attempted:
                    st.text(f"✓ {service}")

def display_enhanced_meta_info(meta: Dict[str, Any]) -> None:
    """향상된 메타정보 종합 표시"""
    if not meta:
        st.info("메타 정보가 없습니다.")
        return
    
    # 각 컴포넌트를 탭으로 구성
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 검색품질", "⚡ 성능", "🛡️ 시스템", "⚠️ 이슈"])
    
    with tab1:
        display_search_quality(meta)
    
    with tab2:
        display_performance_metrics(meta)
    
    with tab3:
        display_system_health(meta)
    
    with tab4:
        display_error_info(meta)

def display_cache_stats() -> None:
    """캐시 통계 표시 (별도 API 호출 필요)"""
    # 이 기능은 캐시 통계 API가 있을 때 사용
    st.markdown("#### 📊 캐시 통계")
    st.info("캐시 통계 API 구현 필요")

def format_answer_with_quality_indicators(answer: str, meta: Dict[str, Any]) -> str:
    """답변에 품질 지표 추가"""
    if not meta:
        return answer
    
    # 검색 품질 정보가 있으면 답변 상단에 품질 배지 추가
    quality_info = []
    
    # 검색 신뢰도 추출
    search_confidence = None
    for key, value in meta.items():
        if isinstance(value, dict):
            search_confidence = value.get("search_confidence")
            if search_confidence:
                break
    
    if search_confidence:
        if search_confidence > 0.8:
            quality_info.append("🟢 **고품질 검색**")
        elif search_confidence > 0.6:
            quality_info.append("🟡 **보통 품질 검색**") 
        else:
            quality_info.append("🟠 **기본 검색 결과**")
    
    # 시스템 상태 확인
    system_health = meta.get("system_health", {})
    if system_health:
        overall_status = system_health.get("overall_status")
        if overall_status == "DEGRADED":
            quality_info.append("⚠️ **일부 서비스 제한**")
        elif overall_status == "PARTIAL":
            quality_info.append("🟡 **부분 서비스**")
    
    # 품질 정보를 답변 상단에 추가
    if quality_info:
        quality_badge = " | ".join(quality_info)
        return f"{quality_badge}\n\n---\n\n{answer}"
    
    return answer