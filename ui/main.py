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
    return os.getenv("API_BASE", "http://greennuri.info:8000")


def call_mcp_query_graph_default(params: dict) -> dict:
    url = f"{API_BASE}/mcp/query_graph_default"
    resp = requests.post(url, json=params, timeout=timeout)
    if resp.status_code >= 400:
        raise requests.HTTPError(f"{resp.status_code} {resp.reason}\n{resp.text}", response=resp)
    return resp.json()

# --------- 사이드바: 공통 설정 ----------
st.sidebar.header("설정")
API_BASE = st.sidebar.text_input("API Base", value=api_base_default(), key=wkey("api_base", "sidebar"))
timeout = st.sidebar.number_input("API Timeout (s)", value=15, min_value=3, max_value=120, step=1, key=wkey("timeout", "sidebar"))

st.sidebar.markdown("---")
st.sidebar.caption("※ 백엔드(FastAPI) URL이 다르면 여기서 바꿔주세요.")

# --------- 공통: 입력 블록 ----------
def query_block(key_prefix: str, defaults: Dict[str, Any] | None = None) -> Dict[str, Any]:
    defaults = defaults or {}
    q = st.text_input(
        "질의",
        value=defaults.get("q", ""),
        key=wkey("q", key_prefix),
        placeholder="예) 한화 지상무기 수주 / KAI 수주 / 005930.KS ..."
    )
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        domain = st.text_input(
            "도메인(선택)",
            value=defaults.get("domain", "지상무기 전차 자주포 장갑차"),
            key=wkey("domain", key_prefix),
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
    """리포트 전용 API가 있다면 사용. 없으면 주석 참고."""
    url = f"{API_BASE}/report"
    resp = requests.post(url, json=payload, timeout=timeout)
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
            elif "Weapon" in labels:
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

    
# 향상된 입력 영역
col1, col2 = st.columns([3, 1])
with col1:
    c_q = st.text_input(
        "질의", 
        value="한화 지상무기 수출 관련 유망 종목은?", 
        key=wkey("q", "chat"),
        placeholder="예: 한화 방산 수출 현황, KAI 최근 실적 등"
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
            
            # 소스 정보 표시 개선
            if sources:
                st.markdown("### 📰 참고 소스")
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
                - "한화 최근 뉴스"
                - "방산 업계 동향" 
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
    - **구체적인 키워드** 사용 (예: "한화", "KAI", "방산")
    - **시간 범위** 포함 (예: "최근", "2024년")  
    - **관심 영역** 명시 (예: "투자", "수출", "실적")
    """)

# ========== 탭 2: 그래프 컨텍스트 ==========
with tab_graph:
    st.subheader("그래프 컨텍스트 조회")
    g_input = query_block("graph", defaults={"q": "한화", "limit": 30, "lookback_days": 180})
    
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
                    st.info("💡 **추천 키워드**: '한화', '회사', '뉴스' 등으로 시도해보세요.")
                
                # API 응답 디버그
                with st.expander("🔍 API 응답 디버그", expanded=False):
                    st.write("API 응답 전체:")
                    st.json(res)
                
                # 데이터 타입별로 분류
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
    st.subheader("자동 리포트 생성")
    # 동일 라벨 위젯들에도 고유 key 부여
    r_input = query_block("report", defaults={"q": "한화 지상무기 수주", "limit": 20, "lookback_days": 180, "domain": "지상무기 전차 자주포 장갑차"})
    r_symbol = st.text_input("관심 종목(선택, 예: 005930.KS)", value="", key=wkey("symbol", "report"))

    # 리포트 구성 옵션(예시)
    colX, colY, colZ = st.columns([1, 1, 1])
    with colX:
        include_news = st.checkbox("뉴스 섹션 포함", value=True, key=wkey("include_news", "report"))
    with colY:
        include_graph = st.checkbox("그래프 섹션 포함", value=True, key=wkey("include_graph", "report"))
    with colZ:
        include_stock = st.checkbox("주가 섹션 포함", value=True, key=wkey("include_stock", "report"))

    payload = {
        "query": r_input["q"],
        "domain": r_input["domain"],
        "lookback_days": r_input["lookback_days"],
        # 보고서 API 스키마에 맞게 전달
        "news_size": int(r_input["limit"]),
        "graph_limit": int(r_input["limit"]),
        "symbol": r_symbol or None,
        # 섹션 토글은 현재 백엔드에서 사용하지 않지만, 확장 대비 유지
        "sections": {
            "news": include_news,
            "graph": include_graph,
            "stock": include_stock,
        },
    }

    r_run = st.button("리포트 생성", key=wkey("run", "report"))
    if r_run:
        try:
            # 백엔드에 /report 가 없다면 일단 /chat 결과를 재활용하거나,
            # 보고서 생성을 위한 별도 엔드포인트를 만들어 주세요.
            # 아래는 /report 사용 예시입니다.
            data = call_report(payload)
            st.markdown("### 리포트")
            st.markdown(data.get("markdown", "보고서 본문이 없습니다."))
            with st.expander("원본 JSON 보기"):
                st.json(data)
        except requests.HTTPError as he:
            if he.response is not None and he.response.status_code == 404:
                st.warning("`/report` 엔드포인트가 없습니다. FastAPI에 리포트 API를 추가하거나, Chat 결과를 조합해 보여주세요.")
            else:
                st.exception(he)
        except Exception as e:
            st.exception(e)
