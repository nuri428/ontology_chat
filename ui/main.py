# app/main.py
import os
# import json
import requests
import streamlit as st
from typing import Any, Dict, List

# Enhanced UI components
try:
    from components import (
        display_enhanced_meta_info,
        format_answer_with_quality_indicators,
        display_cache_stats
    )
    ENHANCED_UI_AVAILABLE = True
except ImportError:
    ENHANCED_UI_AVAILABLE = False

# New schema enhanced components
try:
    from enhanced_components import (
        display_listed_company_info,
        display_financial_summary,
        display_investment_summary,
        display_enhanced_graph_metrics,
        create_financial_dashboard,
        display_quality_indicators
    )
    SCHEMA_ENHANCED_UI_AVAILABLE = True
except ImportError:
    SCHEMA_ENHANCED_UI_AVAILABLE = False

# --------- 기본 설정 ---------
st.set_page_config(
    page_title="Enhanced Ontology Chat", 
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------- 유틸: 고유 key 생성기 ----------
def wkey(name: str, prefix: str) -> str:
    """위젯 키 충돌 방지를 위한 prefix 부여"""
    return f"{prefix}__{name}"

def api_base_default() -> str:
    # Docker 환경에서는 API_BASE_URL, 로컬에서는 API_BASE 사용
    return os.getenv("API_BASE_URL") or os.getenv("API_BASE", "http://localhost:8000")


def call_mcp_query_graph_default(params: dict) -> dict:
    url = f"{API_BASE}/mcp/query_graph_default"
    resp = requests.post(url, json=params, timeout=timeout)
    if resp.status_code >= 400:
        raise requests.HTTPError(f"{resp.status_code} {resp.reason}\n{resp.text}", response=resp)
    return resp.json()

# --------- 사이드바: 공통 설정 ----------
st.sidebar.header("설정")
API_BASE = st.sidebar.text_input("API Base", value=api_base_default(), key=wkey("api_base", "sidebar"))
timeout = st.sidebar.number_input("API Timeout (s)", value=30, min_value=3, max_value=300, step=5, key=wkey("timeout", "sidebar"))

st.sidebar.markdown("---")
st.sidebar.caption("※ 백엔드(FastAPI) URL이 다르면 여기서 바꿔주세요.")
st.sidebar.info("💡 서버 응답 없으면: 타임아웃을 60초 이상으로 설정해보세요")

# --------- 공통: 입력 블록 ----------
def query_block(key_prefix: str, defaults: Dict[str, Any] | None = None) -> Dict[str, Any]:
    defaults = defaults or {}
    q = st.text_input(
        "질의",
        value=defaults.get("q", ""),
        key=wkey("q", key_prefix),
        placeholder="예) 삼성전자 / LG에너지솔루션 / SK하이닉스 / 005930.KS ..."
    )
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        domain = st.text_input(
            "도메인(선택)",
            value=defaults.get("domain", "상장사 투자 실적"),
            key=wkey("domain", key_prefix),
            help="새 스키마: 상장사 중심 분석 지원 - 투자, 실적, 재무지표 등"
        )
    with col2:
        lookback = st.number_input(
            "Lookback(일)",
            value=int(defaults.get("lookback_days", 180)),
            min_value=7, max_value=720, step=7,
            key=wkey("lookback", key_prefix),
        )
    with col3:
        limit = st.number_input(
            "Limit",
            value=int(defaults.get("limit", 30)),
            min_value=1, max_value=200, step=1,
            key=wkey("limit", key_prefix),
        )
    return {"q": q, "domain": domain, "lookback_days": int(lookback), "limit": int(limit)}

# --------- API 호출 헬퍼 ----------
def call_chat(query: str) -> Dict[str, Any]:
    url = f"{API_BASE}/chat"
    resp = requests.post(url, json={"query": query}, timeout=timeout)
    resp.raise_for_status()
    return resp.json()

def call_mcp_query_graph(cypher: str|None, params: dict) -> dict:
    url = f"{API_BASE}/mcp/call"
    if not cypher or not cypher.strip():
        # 빈 cypher는 서버가 거부 → 여기서 예외를 일으켜 UI로 안내
        raise RuntimeError("Cypher가 비어 있습니다. 텍스트 영역에 실행할 Cypher를 입력하세요.")
    payload = {"tool": "query_graph", "args": {"cypher": cypher, "params": params}}
    resp = requests.post(url, json=payload, timeout=timeout)
    # 디버그용: 서버 에러 메시지 표시
    if resp.status_code >= 400:
        raise requests.HTTPError(f"{resp.status_code} {resp.reason}\n{resp.text}", response=resp)
    return resp.json()

def call_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    """기본 리포트 API 호출"""
    url = f"{API_BASE}/report"
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()

def call_comparative_report(queries: List[str], domain: str = None, lookback_days: int = 180) -> Dict[str, Any]:
    """비교 분석 리포트 API 호출"""
    url = f"{API_BASE}/report/comparative"
    payload = {
        "queries": queries,
        "domain": domain,
        "lookback_days": lookback_days
    }
    resp = requests.post(url, json=payload, timeout=timeout*2)  # 비교 분석은 시간이 더 걸림
    resp.raise_for_status()
    return resp.json()

def call_trend_report(query: str, domain: str = None, periods: List[int] = [30, 90, 180]) -> Dict[str, Any]:
    """트렌드 분석 리포트 API 호출"""
    url = f"{API_BASE}/report/trend"
    payload = {
        "query": query,
        "domain": domain,
        "periods": periods
    }
    resp = requests.post(url, json=payload, timeout=timeout*2)  # 트렌드 분석은 시간이 더 걸림
    resp.raise_for_status()
    return resp.json()

def call_executive_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    """경영진 요약 리포트 API 호출"""
    url = f"{API_BASE}/report/executive"
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()

def call_langgraph_report(payload: Dict[str, Any], analysis_depth: str = "standard") -> Dict[str, Any]:
    """LangGraph 기반 고급 리포트 API 호출"""
    url = f"{API_BASE}/report/langgraph"
    payload_with_depth = {**payload, "analysis_depth": analysis_depth}
    resp = requests.post(url, json=payload_with_depth, timeout=timeout*3)  # LangGraph는 시간이 더 걸림
    resp.raise_for_status()
    return resp.json()

def call_langgraph_comparative_report(queries: List[str], domain: str = None, lookback_days: int = 180, analysis_depth: str = "standard") -> Dict[str, Any]:
    """LangGraph 기반 비교 분석 리포트 API 호출"""
    url = f"{API_BASE}/report/langgraph/comparative"
    payload = {
        "queries": queries,
        "domain": domain,
        "lookback_days": lookback_days,
        "analysis_depth": analysis_depth
    }
    resp = requests.post(url, json=payload, timeout=timeout*5)  # 비교 분석은 더 오래 걸림
    resp.raise_for_status()
    return resp.json()

def call_langgraph_trend_report(query: str, domain: str = None, periods: List[int] = [30, 90, 180], analysis_depth: str = "standard") -> Dict[str, Any]:
    """LangGraph 기반 트렌드 분석 리포트 API 호출"""
    url = f"{API_BASE}/report/langgraph/trend"
    payload = {
        "query": query,
        "domain": domain,
        "periods": periods,
        "analysis_depth": analysis_depth
    }
    resp = requests.post(url, json=payload, timeout=timeout*4)  # 트렌드 분석도 오래 걸림
    resp.raise_for_status()
    return resp.json()

def call_forecast_report(params: dict) -> dict:
    """새로운 전망 리포트 API 호출"""
    url = f"{API_BASE}/forecast_report"
    resp = requests.post(url, json=params, timeout=timeout*2)  # 리포트 생성에 시간이 걸릴 수 있음
    resp.raise_for_status()
    return resp.json()

# --------- 그래프 HTML 렌더(pyvis) ----------
def render_pyvis_graph(items: List[Dict[str, Any]], height: str = "680px", key_prefix: str = "graph") -> None:
    """
    items: Neo4j MCP query_graph 결과의 rows(data). 각 원소 예: {'n': {...}, 'labels': [...], 'r': {...}, 'type': '...'}
    노드와 관계를 모두 시각화(라벨/타임스탬프에 따라 그룹/툴팁).
    """
    try:
        from pyvis.network import Network
    except Exception:
        st.warning("pyvis가 설치되어 있지 않습니다. `pip install pyvis` 후 다시 시도해 주세요.")
        return

    # pyvis 네트워크 초기화 (Docker 환경에 최적화)
    net = Network(
        height=height, 
        width="100%", 
        bgcolor="#111111", 
        font_color="#ffffff", 
        notebook=False, 
        directed=False,
        cdn_resources="remote"  # CDN 리소스 사용으로 안정성 향상
    )
    
    # 물리 시뮬레이션 설정 (안정화 개선)
    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "stabilization": {
                "enabled": true,
                "iterations": 200,
                "updateInterval": 50,
                "onlyDynamicEdges": false,
                "fit": true
            },
            "barnesHut": {
                "gravitationalConstant": -2000,
                "centralGravity": 0.3,
                "springLength": 95,
                "springConstant": 0.04,
                "damping": 0.09,
                "avoidOverlap": 0.5
            },
            "maxVelocity": 50,
            "minVelocity": 0.1,
            "solver": "barnesHut",
            "timestep": 0.35
        },
        "nodes": {
            "font": {
                "size": 12,
                "color": "white"
            },
            "borderWidth": 2,
            "borderWidthSelected": 3
        },
        "edges": {
            "font": {
                "size": 10,
                "color": "white"
            },
            "smooth": {
                "type": "continuous"
            }
        }
    }
    """)

    # 노드와 에지 처리
    seen_nodes = set()
    seen_edges = set()
    
    # 1단계: 노드 추가 (최대 20개로 제한하여 안정성 향상)
    max_nodes = 20
    for idx, r in enumerate(items[:max_nodes]):
        # 노드 정보 처리
        n = r.get("n", {})
        if n:  # 노드가 있는 경우
            labels = r.get("labels", [])
            # 고유한 노드 ID 생성 (elementId가 없는 경우)
            nid = n.get("elementId") or n.get("id") or r.get("n_id") or f"node_{idx}"
            if nid in seen_nodes:
                continue
            seen_nodes.add(nid)
            
            # 노드에 고유 ID 저장 (관계 처리용)
            n["_generated_id"] = nid
            
            title = n.get("title") or n.get("name") or n.get("contractId") or n.get("articleId") or f"Node_{idx}"
            # 제목이 너무 길면 잘라내기
            if len(title) > 30:
                title = title[:27] + "..."
            
            group = ",".join(labels) if labels else "Node"
            
            # 노드 색상 설정 (라벨에 따라)
            color = "#97C2FC"  # 기본 파란색
            if "Event" in labels:
                color = "#FFB347"  # 주황색
            elif "Company" in labels:
                color = "#98FB98"  # 연두색
            elif "Contract" in labels:
                color = "#DDA0DD"  # 자주색
            elif "Product" in labels or "WeaponSystem" in labels:
                color = "#F0E68C"  # 카키색
            
            tooltip = f"<b>{title}</b><br/>labels={labels}<br/>" + "<br/>".join(f"{k}: {v}" for k, v in n.items() if k not in ("elementId", "_generated_id"))
            net.add_node(nid, label=title, title=tooltip, group=group, color=color, size=20)
    
    # 2단계: 에지 추가 (관계 정보가 있는 경우) - 제한된 노드에 대해서만
    for r in items[:max_nodes]:
        # 새로운 관계 데이터 구조 처리 (all_relationships)
        all_relationships = r.get("all_relationships", [])
        if all_relationships:
            current_node = r.get("n", {})
            current_node_id = current_node.get("_generated_id") or current_node.get("elementId") or current_node.get("id")
            
            for rel_list in all_relationships:
                if isinstance(rel_list, list):
                    for rel in rel_list:
                        if isinstance(rel, list) and len(rel) >= 3:
                            # [start_node, rel_type, end_node] 형태
                            start_node_obj, rel_type, end_node_obj = rel[0], rel[1], rel[2]
                            
                            # 시작 노드가 비어있고 끝 노드에 이벤트 정보가 있는 경우
                            # 현재 노드에서 이벤트로의 관계로 처리
                            if (not start_node_obj or start_node_obj == {}) and isinstance(end_node_obj, dict) and end_node_obj:
                                # 이벤트 노드 찾기 (같은 이벤트 ID를 가진 노드)
                                event_id = end_node_obj.get("eventId")
                                if event_id:
                                    # 다른 노드들 중에서 같은 eventId를 가진 노드 찾기
                                    for other_r in items:
                                        other_node = other_r.get("n", {})
                                        if (other_node.get("eventId") == event_id and 
                                            other_node.get("_generated_id") != current_node_id):
                                            other_node_id = other_node.get("_generated_id")
                                            if other_node_id:
                                                edge_id = f"{current_node_id}_{other_node_id}_{rel_type}"
                                                if edge_id not in seen_edges:
                                                    seen_edges.add(edge_id)
                                                    net.add_edge(current_node_id, other_node_id, label=rel_type, title=rel_type)
                                                break
        
        # 기존 관계 정보 처리 (하위 호환성)
        rel = r.get("r", {})
        if rel:  # 관계가 있는 경우
            start_node = r.get("start_id") or (r.get("start", {}) or {}).get("elementId") or (r.get("start", {}) or {}).get("id")
            end_node = r.get("end_id") or (r.get("end", {}) or {}).get("elementId") or (r.get("end", {}) or {}).get("id")
            rel_type = r.get("type", "RELATES_TO")
            
            if start_node and end_node and start_node != end_node:
                edge_id = f"{start_node}_{end_node}_{rel_type}"
                if edge_id not in seen_edges:
                    seen_edges.add(edge_id)
                    net.add_edge(start_node, end_node, label=rel_type, title=rel_type)
    
    # 3단계: 관계가 없는 경우, 노드들 간의 가상 연결 생성 (선택적)
    if not seen_edges and len(seen_nodes) > 1:
        st.info("관계 정보가 없어 노드만 표시됩니다. 관계를 보려면 Neo4j 쿼리를 수정하세요.")
        # 디버그 정보 표시
        st.write(f"관계 데이터 샘플: {all_relationships[:2] if all_relationships else 'None'}")
        st.write(f"현재 노드 ID: {[r.get('n', {}).get('_generated_id') for r in items]}")

    # (간단 버전) 관계(edge) 없이 노드만. 관계 시각화가 필요하면 백엔드에서 edges까지 넘겨주세요.
    try:
        # HTML을 직접 생성하여 Streamlit에서 표시
        html_content = net.generate_html()
        st.components.v1.html(html_content, height=int(height.replace("px", "")), scrolling=True)
    except Exception as e:
        st.error(f"그래프 렌더링 오류: {str(e)}")
        st.info("그래프 데이터를 테이블로 표시합니다.")
        # 오류 발생 시 데이터를 테이블로 표시
        if items:
            import pandas as pd
            df_data = []
            for r in items:
                n = r.get("n", {})
                labels = r.get("labels", [])
                row = {
                    "ID": n.get("elementId") or n.get("id", ""),
                    "Title": n.get("title") or n.get("name") or n.get("contractId") or n.get("articleId", ""),
                    "Labels": ", ".join(labels),
                    "Type": n.get("event_type") or n.get("type", ""),
                    "Published": n.get("published_at", ""),
                }
                df_data.append(row)
            if df_data:
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True)

# --------- 메인 헤더 ----------
st.title("🚀 Enhanced Ontology Chat System")
st.markdown("""
**Context Engineering 시스템**이 업그레이드되었습니다! 
🔍 지능형 검색, 💡 LLM 인사이트, ⚡ 캐싱, 🛡️ 안정성이 모두 향상되었습니다.
""")

if ENHANCED_UI_AVAILABLE:
    st.success("✅ Enhanced UI 컴포넌트가 활성화되었습니다.")
else:
    st.info("ℹ️ 기본 UI로 동작합니다. 향상된 기능을 위해 `ui/components.py`를 확인하세요.")

st.divider()

# --------- 탭 구성 ----------
tab_chat, tab_graph, tab_report = st.tabs(["💬 Enhanced Chat", "🔗 그래프 컨텍스트", "📑 리포트"])

# ========== 탭 1: Enhanced Chat ==========
with tab_chat:
    # 향상된 입력 영역
    col1, col2 = st.columns([3, 1])
    with col1:
        c_q = st.text_input(
            "질의",
            value="",
            key=wkey("q", "chat"),
            placeholder="예: SMR 관련 유망 종목은?, 2차전지 최신 동향, 반도체 시장 전망 등"
        )
    with col2:
        # 캐시 통계 버튼 (향후 확장용)
        if ENHANCED_UI_AVAILABLE:
            show_cache = st.button("📊 캐시 통계", key=wkey("cache_stats", "chat"))
            if show_cache:
                display_cache_stats()

    # 실행 옵션
    col_run, col_clear = st.columns([1, 1])
    with col_run:
        c_run = st.button("🚀 질의 실행", key=wkey("run", "chat"), type="primary")
    with col_clear:
        if st.button("🗑️ 결과 초기화", key=wkey("clear", "chat")):
            st.rerun()

    if c_run:
        with st.spinner("Context Engineering 시스템이 답변을 생성하고 있습니다..."):
            try:
                data = call_chat(c_q)

                # 성공적인 응답 처리
                answer = data.get("answer", "")
                meta = data.get("meta", {})
                sources = data.get("sources", [])

                # 향상된 답변 표시 (품질 지표 포함)
                if ENHANCED_UI_AVAILABLE and meta:
                    enhanced_answer = format_answer_with_quality_indicators(answer, meta)
                    st.markdown(enhanced_answer)
                else:
                    st.markdown(answer)

                # 구분선
                st.divider()

                # 향상된 메타정보 표시
                if ENHANCED_UI_AVAILABLE and meta:
                    st.markdown("### 📊 시스템 정보")
                    display_enhanced_meta_info(meta)

                # 소스 정보 표시 개선 - 표 형식 추가
                if sources:
                    st.markdown("### 📰 참고 소스")

                    # 표시 방식 선택
                    col_view, col_export = st.columns([2, 1])
                    with col_view:
                        view_mode = st.radio(
                            "표시 방식",
                            ["표 형식", "리스트 형식"],
                            horizontal=True,
                            key=wkey("view_mode", "chat_sources")
                        )

                    if view_mode == "표 형식":
                        # 표 형식으로 표시 - Streamlit 네이티브 방식
                        import pandas as pd

                        # 데이터프레임 생성
                        news_data = []
                        for i, source in enumerate(sources[:10], 1):  # 최대 10개까지
                            title = source.get("title", "제목 없음")
                            url = source.get("url", "")
                            date = source.get("date", "")
                            score = source.get("score", 0)

                            # 제목 길이 제한
                            if len(title) > 60:
                                title = title[:57] + "..."

                            news_data.append({
                                "순번": i,
                                "제목": title,
                                "날짜": date[:10] if date else "-",
                                "점수": f"{score:.2f}" if score else "-",
                                "URL": url if url else "-"
                            })

                        df = pd.DataFrame(news_data)

                        # Streamlit 데이터프레임으로 표시 (컬럼 설정 포함)
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "순번": st.column_config.NumberColumn(
                                    "순번",
                                    width="small",
                                    format="%d"
                                ),
                                "제목": st.column_config.TextColumn(
                                    "제목",
                                    width="large",
                                    help="뉴스 제목"
                                ),
                                "날짜": st.column_config.DateColumn(
                                    "발행일",
                                    width="medium",
                                    format="YYYY-MM-DD"
                                ),
                                "점수": st.column_config.NumberColumn(
                                    "관련도",
                                    width="small",
                                    format="%.2f"
                                ),
                                "URL": st.column_config.LinkColumn(
                                    "링크",
                                    width="medium",
                                    help="뉴스 원문 링크",
                                    display_text="🔗 원문보기"
                                )
                            }
                        )

                        # CSV 다운로드 버튼
                        csv = df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📄 CSV로 다운로드",
                            data=csv,
                            file_name="news_sources.csv",
                            mime="text/csv",
                            key=wkey("download_csv", "chat_sources")
                        )

                    else:
                        # 기존 리스트 형식
                        for i, source in enumerate(sources[:5], 1):
                            with st.container():
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    title = source.get("title", "제목 없음")
                                    url = source.get("url", "")
                                    if url:
                                        st.markdown(f"**{i}.** [{title}]({url})")
                                    else:
                                        st.markdown(f"**{i}.** {title}")
                                with col2:
                                    date = source.get("date", "")
                                    score = source.get("score", 0)
                                    if date:
                                        st.caption(f"📅 {date[:10]}")
                                    if score:
                                        st.caption(f"⭐ {score:.2f}")

                # 전체 결과 JSON (개발자용)
                with st.expander("🔍 전체 응답 데이터 (개발자용)", expanded=False):
                    st.json(data)

            except requests.exceptions.Timeout:
                st.error("⏰ 요청 시간이 초과되었습니다. 더 간단한 질의로 다시 시도해보세요.")
            except requests.exceptions.ConnectionError:
                st.error("🔌 API 서버에 연결할 수 없습니다. API_BASE 설정을 확인해주세요.")
            except requests.exceptions.HTTPError as he:
                st.error(f"🚨 API 오류: {he}")
                if hasattr(he, 'response') and he.response is not None:
                    st.code(he.response.text)
            except Exception as e:
                st.error(f"⚠️ 예상치 못한 오류가 발생했습니다:")
                st.exception(e)

                # 오류 발생 시 도움말 제공
                with st.expander("💡 문제 해결 도움말", expanded=True):
                    st.markdown("""
                    **일반적인 해결 방법:**
                    1. API 서버가 실행 중인지 확인
                    2. 사이드바에서 API Base URL 확인
                    3. 네트워크 연결 상태 확인
                    4. 질의를 더 간단하게 수정

                    **추천 질의 예시:**
                    - "삼성전자 최근 뉴스"
                    - "2차전지 업계 동향"
                    - "반도체 시장 전망"
                    - "KAI 실적 전망"
                    """)

    # 도움말 섹션
    with st.expander("❓ Context Engineering 시스템 도움말", expanded=False):
        st.markdown("""
        ### 🚀 향상된 기능들

        **🔍 지능형 검색**: 다단계 검색 전략으로 더 정확한 결과
        **💡 동적 인사이트**: LLM 기반 실시간 분석
        **📊 개인화**: 질의 유형별 맞춤 응답
        **⚡ 캐싱**: 빠른 응답 속도
        **🛡️ 안정성**: 서비스 장애 시에도 기본 응답 제공

        ### 💭 질의 팁
        - **구체적인 키워드** 사용 (예: "삼성전자", "SMR", "2차전지")
        - **시간 범위** 포함 (예: "최근", "2024년")
        - **관심 영역** 명시 (예: "투자", "수출", "실적")
        """)

# ========== 탭 2: 그래프 컨텍스트 ==========
with tab_graph:
    st.subheader("그래프 컨텍스트 조회")
    g_input = query_block("graph", defaults={"q": "", "limit": 30, "lookback_days": 180})
    
    # 관계 포함 옵션
    include_relationships = st.checkbox("관계(에지) 포함", value=False, key=wkey("include_rels", "graph"))
    
    cypher_txt = st.text_area(
        "Cypher (환경설정 파일을 쓰지 않고 직접 실행하려면 여기에 붙여넣기)",
        value="",
        height=200,
        key=wkey("cypher", "graph"),
        placeholder="비워두면 서버 설정(config/graph_search.cypher) 사용"
    )
    
    # 관계 포함 쿼리 예시
    if include_relationships and not cypher_txt:
        st.info("관계를 포함한 쿼리 예시:")
        example_cypher = """
MATCH (n)-[r]-(m)
WHERE toLower(n.title) CONTAINS toLower($q) OR toLower(m.title) CONTAINS toLower($q)
RETURN n, labels(n) AS labels,
       r, type(r) AS type,
       m AS end, labels(m) AS end_labels,
       elementId(n) AS start_id, elementId(m) AS end_id
LIMIT $limit
        """.strip()
        st.code(example_cypher, language="cypher")
    run = st.button("그래프 질의 실행", key=wkey("run", "graph"))
    if run:
        try:
            res = None
            params = {
                "q": g_input["q"],
                "domain": g_input["domain"],
                "lookback_days": g_input["lookback_days"],
                "limit": g_input["limit"],
            }
            
            # API 호출 전 디버그
            st.info(f"API 호출 파라미터: {params}")
            
            if cypher_txt.strip():
                st.info("사용자 정의 Cypher 쿼리 사용")
                res = call_mcp_query_graph(cypher_txt, params)
            else:
                st.info("기본 그래프 검색 쿼리 사용")
                res = call_mcp_query_graph_default(params)
            if not res or not res.get("ok"):
                st.error(f"MCP query_graph 실패: {res}")
            else:
                rows = res.get("data", [])
                if rows:
                    st.success(f"노드 {len(rows)}개 수신")
                else:
                    st.warning("검색 결과가 없습니다. 다른 키워드로 시도해보세요.")
                    st.info("💡 **추천 키워드**: '삼성전자', 'LG에너지솔루션', 'SK하이닉스', '005930.KS' 등으로 시도해보세요.")
                
                # API 응답 디버그
                with st.expander("🔍 API 응답 디버그", expanded=False):
                    st.write("API 응답 전체:")
                    st.json(res)
                
                # 데이터 타입별로 분류 - 새 스키마 노드 포함
                news_data = [r for r in rows if "News" in r.get("labels", [])]
                event_data = [r for r in rows if "Event" in r.get("labels", [])]
                company_data = [r for r in rows if "Company" in r.get("labels", [])]
                other_data = [r for r in rows if not any(label in ["News", "Event", "Company"] for label in r.get("labels", []))]
                
                # 디버그 정보 표시
                with st.expander("🔍 디버그 정보", expanded=False):
                    st.write(f"전체 데이터 개수: {len(rows)}")
                    st.write(f"뉴스 데이터 개수: {len(news_data)}")
                    st.write(f"이벤트 데이터 개수: {len(event_data)}")
                    st.write(f"회사 데이터 개수: {len(company_data)}")
                    st.write(f"기타 데이터 개수: {len(other_data)}")
                    if rows:
                        st.write("첫 번째 데이터 샘플:")
                        st.json(rows[0])
                
                # 탭으로 데이터 분류 표시
                tab_news, tab_events, tab_companies, tab_others, tab_graph_viz = st.tabs([
                    f"📰 뉴스 ({len(news_data)})", 
                    f"📅 이벤트 ({len(event_data)})", 
                    f"🏢 회사 ({len(company_data)})", 
                    f"🔗 기타 ({len(other_data)})",
                    "🎨 그래프"
                ])
                
                # 뉴스 탭
                with tab_news:
                    if news_data:
                        st.subheader("연관 뉴스")

                        # 표시 방식 선택
                        news_view_mode = st.radio(
                            "표시 방식",
                            ["표 형식", "리스트 형식"],
                            horizontal=True,
                            key=wkey("news_view_mode", "graph")
                        )

                        if news_view_mode == "표 형식":
                            # 표 형식으로 표시
                            import pandas as pd

                            # 뉴스 데이터프레임 생성
                            news_table_data = []
                            for i, news in enumerate(news_data[:10], 1):
                                n = news.get("n", {})
                                url = n.get("url", "")
                                article_id = n.get("articleId", "")
                                last_seen = n.get("lastSeenAt", "")
                                title = n.get("title", "") or f"Article {article_id}"

                                # 제목 길이 제한
                                if len(title) > 50:
                                    title = title[:47] + "..."

                                news_table_data.append({
                                    "순번": i,
                                    "제목": title,
                                    "Article ID": article_id,
                                    "발견일": last_seen[:10] if last_seen else "-",
                                    "URL": url if url else "-"
                                })

                            news_df = pd.DataFrame(news_table_data)

                            # Streamlit 데이터프레임으로 표시
                            st.dataframe(
                                news_df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "순번": st.column_config.NumberColumn(
                                        "순번",
                                        width="small",
                                        format="%d"
                                    ),
                                    "제목": st.column_config.TextColumn(
                                        "제목",
                                        width="large",
                                        help="뉴스 제목"
                                    ),
                                    "Article ID": st.column_config.TextColumn(
                                        "기사 ID",
                                        width="medium",
                                        help="기사 고유 식별자"
                                    ),
                                    "발견일": st.column_config.DateColumn(
                                        "발견일",
                                        width="medium",
                                        format="YYYY-MM-DD"
                                    ),
                                    "URL": st.column_config.LinkColumn(
                                        "링크",
                                        width="medium",
                                        help="뉴스 원문 링크",
                                        display_text="🔗 원문보기"
                                    )
                                }
                            )

                            # CSV 다운로드 버튼
                            news_csv = news_df.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label="📄 뉴스 CSV 다운로드",
                                data=news_csv,
                                file_name="graph_news.csv",
                                mime="text/csv",
                                key=wkey("download_news_csv", "graph")
                            )

                        else:
                            # 기존 리스트 형식
                            for i, news in enumerate(news_data[:10]):  # 최대 10개 표시
                                n = news.get("n", {})
                                url = n.get("url", "")
                                article_id = n.get("articleId", "")
                                last_seen = n.get("lastSeenAt", "")

                                with st.container():
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        if url:
                                            st.markdown(f"**뉴스 {i+1}**: [{url}]({url})")
                                        else:
                                            st.markdown(f"**뉴스 {i+1}**: Article ID {article_id}")
                                    with col2:
                                        if last_seen:
                                            st.caption(f"발견: {last_seen[:10]}")
                                    st.divider()
                    else:
                        st.info("연관 뉴스가 없습니다.")
                
                # 이벤트 탭
                with tab_events:
                    if event_data:
                        st.subheader("관련 이벤트")
                        for i, event in enumerate(event_data[:10]):
                            n = event.get("n", {})
                            title = n.get("title", "제목 없음")
                            event_type = n.get("event_type", "")
                            published_at = n.get("published_at", "")
                            
                            with st.container():
                                st.markdown(f"**{i+1}. {title}**")
                                if event_type:
                                    st.caption(f"유형: {event_type}")
                                if published_at:
                                    st.caption(f"발행일: {published_at}")
                                st.divider()
                    else:
                        st.info("관련 이벤트가 없습니다.")
                
                # 회사 탭
                with tab_companies:
                    if company_data:
                        st.subheader("관련 회사")
                        for i, company in enumerate(company_data[:10]):
                            n = company.get("n", {})
                            name = n.get("name", "이름 없음")
                            ticker = n.get("ticker", "")
                            
                            with st.container():
                                st.markdown(f"**{i+1}. {name}**")
                                if ticker:
                                    st.caption(f"티커: {ticker}")
                                st.divider()
                    else:
                        st.info("관련 회사가 없습니다.")
                
                # 기타 탭
                with tab_others:
                    if other_data:
                        st.subheader("기타 데이터")
                        for i, item in enumerate(other_data[:10]):
                            n = item.get("n", {})
                            labels = item.get("labels", [])
                            title = n.get("title") or n.get("name") or n.get("contractId") or "제목 없음"
                            
                            with st.container():
                                st.markdown(f"**{i+1}. {title}**")
                                st.caption(f"타입: {', '.join(labels)}")
                                st.divider()
                    else:
                        st.info("기타 데이터가 없습니다.")
                
                # 그래프 탭
                with tab_graph_viz:
                    render_pyvis_graph(rows, key_prefix="graph")
        except Exception as e:
            st.exception(e)

# ========== 탭 3: 리포트 ==========
with tab_report:
    st.header("📊 테마별 종목 전망 리포트")
    st.markdown("**테마 또는 개별 종목을 선택하여 뉴스, 온톨로지, 재무정보 기반 전망 보고서를 생성합니다**")

    # 리포트 모드 선택
    report_mode = st.radio(
        "리포트 생성 모드",
        ["🎯 테마별 분석", "🏢 개별 종목 분석"],
        horizontal=True,
        key=wkey("report_mode", "report"),
        help="테마별 분석: 2차전지, 반도체, 원자력 등 / 개별 종목: 특정 상장사 중심 분석"
    )

    # 테마별 종목 데이터 구성
    THEME_SECTORS = {
        "🔋 2차전지/에너지": {
            "keywords": ["배터리", "2차전지", "리튬", "전기차", "ESS"],
            "companies": [
                {"name": "LG에너지솔루션", "code": "373220", "sector": "배터리"},
                {"name": "삼성SDI", "code": "006400", "sector": "배터리"},
                {"name": "SK온", "code": "096770", "sector": "배터리"},
                {"name": "포스코케미칼", "code": "003670", "sector": "배터리 소재"},
                {"name": "에코프로", "code": "086520", "sector": "양극재"},
                {"name": "L&F", "code": "066970", "sector": "양극재"}
            ]
        },
        "💾 반도체/IT": {
            "keywords": ["반도체", "메모리", "시스템반도체", "AI칩", "HBM"],
            "companies": [
                {"name": "삼성전자", "code": "005930", "sector": "종합 반도체"},
                {"name": "SK하이닉스", "code": "000660", "sector": "메모리 반도체"},
                {"name": "카카오", "code": "035720", "sector": "IT 플랫폼"},
                {"name": "네이버", "code": "035420", "sector": "IT 플랫폼"},
                {"name": "LG이노텍", "code": "011070", "sector": "전자부품"}
            ]
        },
        "🚗 모빌리티/자동차": {
            "keywords": ["자동차", "전기차", "자율주행", "모빌리티"],
            "companies": [
                {"name": "현대차", "code": "005380", "sector": "완성차"},
                {"name": "기아", "code": "000270", "sector": "완성차"},
                {"name": "현대모비스", "code": "012330", "sector": "자동차 부품"},
                {"name": "LG전자", "code": "066570", "sector": "전장 부품"},
                {"name": "삼성전기", "code": "009150", "sector": "전자부품"}
            ]
        },
        "🏗️ 건설/인프라": {
            "keywords": ["건설", "인프라", "스마트시티", "해외수주"],
            "companies": [
                {"name": "현대건설", "code": "000720", "sector": "건설"},
                {"name": "삼성물산", "code": "028260", "sector": "건설/상사"},
                {"name": "GS건설", "code": "006360", "sector": "건설"},
                {"name": "대우건설", "code": "047040", "sector": "건설"}
            ]
        },
        "💻 IT/소프트웨어": {
            "keywords": ["IT", "소프트웨어", "클라우드", "인공지능", "AI", "빅데이터"],
            "companies": [
                {"name": "삼성SDS", "code": "018260", "sector": "IT 서비스"},
                {"name": "LG CNS", "code": "251270", "sector": "IT 서비스"},
                {"name": "네이버", "code": "035420", "sector": "인터넷 서비스"},
                {"name": "카카오", "code": "035720", "sector": "인터넷 서비스"},
                {"name": "엔씨소프트", "code": "036550", "sector": "소프트웨어"},
                {"name": "두산범비계", "code": "018880", "sector": "ERP 소프트웨어"}
            ]
        },
        "🧬 바이오/의료": {
            "keywords": ["바이오", "제약", "의료", "헬스케어", "신약", "진단"],
            "companies": [
                {"name": "삼성바이오로직스", "code": "207940", "sector": "바이오의약품"},
                {"name": "셀트리온", "code": "068270", "sector": "제약"},
                {"name": "바이오니아", "code": "064550", "sector": "바이오의약품"},
                {"name": "대웅제약", "code": "069620", "sector": "제약"},
                {"name": "버텍생명과학", "code": "036010", "sector": "제약"},
                {"name": "유한양행", "code": "000210", "sector": "의료기기"}
            ]
        },
        "⚡ 에너지/배터리": {
            "keywords": ["에너지", "신재생", "태양광", "풍력", "배터리", "전기차"],
            "companies": [
                {"name": "LG에너지솔루션", "code": "373220", "sector": "배터리"},
                {"name": "삼성SDI", "code": "006400", "sector": "배터리"},
                {"name": "한화솔루션", "code": "009830", "sector": "태양광/에너지"},
                {"name": "OCI", "code": "010060", "sector": "태양광 소재"},
                {"name": "원진그린", "code": "143540", "sector": "태양광"},
                {"name": "두산에너빌", "code": "069730", "sector": "풍력"}
            ]
        }
    }

    # 모드별 UI 구성
    if report_mode == "🎯 테마별 분석":
        st.subheader("🎯 테마별 분석 설정")

        # 테마 선택
        selected_theme = st.selectbox(
            "분석할 테마 선택",
            list(THEME_SECTORS.keys()),
            key=wkey("theme_select", "report"),
            help="각 테마별로 관련 종목들과 키워드가 자동 설정됩니다"
        )

        # 선택된 테마 정보 표시
        theme_data = THEME_SECTORS[selected_theme]

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**🔍 분석 키워드**")
            st.info(" • ".join(theme_data["keywords"]))

        with col2:
            st.markdown("**🏢 포함 종목**")
            company_list = [f"{comp['name']}({comp['code']})" for comp in theme_data["companies"]]
            st.info(" • ".join(company_list[:3]) + f" 외 {len(company_list)-3}개")

        # 분석 기간 설정
        analysis_period = st.select_slider(
            "분석 기간",
            ["1주일", "2주일", "1개월", "3개월", "6개월"],
            value="1개월",
            key=wkey("period", "theme_report")
        )

    else:  # 개별 종목 분석
        st.subheader("🏢 개별 종목 분석 설정")

        # 직접 입력 또는 테마에서 선택
        input_method = st.radio(
            "종목 선택 방법",
            ["📝 직접 입력", "📋 테마별 선택"],
            horizontal=True,
            key=wkey("input_method", "report")
        )

        if input_method == "📝 직접 입력":
            col1, col2 = st.columns([2, 1])
            with col1:
                company_input = st.text_input(
                    "회사명 또는 종목코드",
                    placeholder="예: 삼성전자, 005930, LG에너지솔루션",
                    key=wkey("company_input", "report")
                )
            with col2:
                analysis_period = st.selectbox(
                    "분석 기간",
                    ["1주일", "2주일", "1개월", "3개월", "6개월"],
                    index=2,
                    key=wkey("period", "individual_report")
                )
        else:
            col1, col2 = st.columns([1, 1])
            with col1:
                theme_for_company = st.selectbox(
                    "테마 선택",
                    list(THEME_SECTORS.keys()),
                    key=wkey("theme_for_company", "report")
                )
            with col2:
                companies_in_theme = THEME_SECTORS[theme_for_company]["companies"]
                selected_company = st.selectbox(
                    "종목 선택",
                    [f"{comp['name']} ({comp['code']})" for comp in companies_in_theme],
                    key=wkey("company_from_theme", "report")
                )

    st.divider()

    # 리포트 생성 설정
    st.subheader("⚙️ 리포트 생성 설정")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        include_news = st.checkbox("📰 최신 뉴스 분석", value=True, key=wkey("include_news", "report"))
    with col2:
        include_ontology = st.checkbox("🕸️ 온톨로지 그래프", value=True, key=wkey("include_ontology", "report"))
    with col3:
        include_financial = st.checkbox("💰 재무 정보", value=True, key=wkey("include_financial", "report"))

    # 리포트 생성 버튼
    st.markdown("---")
    generate_report = st.button(
        "🚀 전망 리포트 생성",
        type="primary",
        key=wkey("generate_report", "report"),
        help="선택된 설정에 따라 종합 전망 보고서를 생성합니다"
    )

    # 리포트 생성 로직
    if generate_report:
        # 쿼리 구성
        if report_mode == "🎯 테마별 분석":
            # 테마별 분석용 쿼리 생성
            query_text = f"{selected_theme.replace('🚀 ', '').replace('🔋 ', '').replace('💾 ', '').replace('🚗 ', '').replace('🏗️ ', '')} 관련 최신 동향 전망"
            keywords = theme_data["keywords"]
            companies = [comp["name"] for comp in theme_data["companies"]]

            st.info(f"**분석 대상**: {selected_theme} | **기간**: {analysis_period} | **종목 수**: {len(companies)}개")

        else:
            # 개별 종목 분석용 쿼리 생성
            if input_method == "📝 직접 입력":
                if not company_input:
                    st.warning("회사명 또는 종목코드를 입력해주세요.")
                    st.stop()
                query_text = f"{company_input} 최신 뉴스 전망 분석"
                keywords = [company_input]
                companies = [company_input]
            else:
                # 테마에서 선택한 종목
                company_name = selected_company.split(" (")[0]  # "삼성전자 (005930)" -> "삼성전자"
                query_text = f"{company_name} 최신 뉴스 전망 분석"
                keywords = [company_name]
                companies = [company_name]

            st.info(f"**분석 대상**: {companies[0]} | **기간**: {analysis_period}")

        # 기간을 일수로 변환
        period_days = {"1주일": 7, "2주일": 14, "1개월": 30, "3개월": 90, "6개월": 180}
        lookback_days = period_days.get(analysis_period, 30)

        with st.spinner("🔍 데이터 수집 및 분석 중..."):
            try:
                # 새로운 전망 리포트 API 호출
                report_data = call_forecast_report({
                    "query": query_text,
                    "keywords": keywords,
                    "companies": companies,
                    "lookback_days": lookback_days,
                    "include_news": include_news,
                    "include_ontology": include_ontology,
                    "include_financial": include_financial,
                    "report_mode": report_mode
                })

                # 리포트 표시
                st.success("✅ 전망 리포트가 완성되었습니다!")

                # 리포트 헤더
                st.markdown(f"# 📊 {query_text}")
                st.markdown(f"**생성일시**: {report_data.get('generated_at', '알 수 없음')} | **분석 기간**: {analysis_period}")

                # 리포트 내용 표시
                if "executive_summary" in report_data:
                    st.markdown("## 🎯 핵심 요약")
                    st.markdown(report_data["executive_summary"])

                if "news_analysis" in report_data:
                    st.markdown("## 📰 뉴스 분석")
                    st.markdown(report_data["news_analysis"])

                if "ontology_insights" in report_data:
                    st.markdown("## 🕸️ 관계 분석")
                    st.markdown(report_data["ontology_insights"])

                if "financial_outlook" in report_data:
                    st.markdown("## 💰 재무 전망")
                    st.markdown(report_data["financial_outlook"])

                if "conclusion" in report_data:
                    st.markdown("## 📈 투자 전망")
                    st.markdown(report_data["conclusion"])

                # 참고 자료
                if "sources" in report_data and report_data["sources"]:
                    st.markdown("## 📑 참고 자료")
                    for i, source in enumerate(report_data["sources"][:5], 1):
                        st.markdown(f"{i}. [{source.get('title', '제목없음')}]({source.get('url', '#')}) - {source.get('date', '')}")

            except Exception as e:
                st.error(f"⚠️ 리포트 생성 중 오류 발생: {e}")
                st.info("💡 대안: Enhanced Chat 탭에서 개별 질의를 시도해보세요.")
