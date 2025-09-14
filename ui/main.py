# app/main.py
import os
# import json
import requests
import streamlit as st
from typing import Any, Dict, List

# --------- 기본 설정 ---------
st.set_page_config(page_title="Ontology Chat Stream", layout="wide")

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
    net.toggle_physics(True)  # 물리 엔진 on (드래그/움직임)

    # 노드와 에지 처리
    seen_nodes = set()
    seen_edges = set()
    
    # 1단계: 노드 추가
    for idx, r in enumerate(items):
        # 노드 정보 처리
        n = r.get("n", {})
        if n:  # 노드가 있는 경우
            labels = r.get("labels", [])
            # 서버가 elementId를 별도로 내려주는 경우 대비(n_id)
            nid = n.get("elementId") or n.get("id") or r.get("n_id") or f"node_{idx}"
            if nid in seen_nodes:
                continue
            seen_nodes.add(nid)
            
            title = n.get("title") or n.get("name") or n.get("contractId") or n.get("articleId") or "(node)"
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
            
            tooltip = f"<b>{title}</b><br/>labels={labels}<br/>" + "<br/>".join(f"{k}: {v}" for k, v in n.items() if k not in ("elementId",))
            net.add_node(nid, label=title, title=tooltip, group=group, color=color)
    
    # 2단계: 에지 추가 (관계 정보가 있는 경우)
    for r in items:
        # 관계 정보 처리
        rel = r.get("r", {})
        if rel:  # 관계가 있는 경우
            # Cypher에서 elementId(startNode) / elementId(endNode)를 start_id/end_id로 반환하도록 권장
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

# --------- 탭 구성 ----------
tab_graph, tab_chat, tab_report = st.tabs(["🔗 그래프 컨텍스트", "💬 Chat", "📑 리포트"])

# ========== 탭 1: 그래프 컨텍스트 ==========
with tab_graph:
    st.subheader("그래프 컨텍스트 조회")
    g_input = query_block("graph", defaults={"q": "한화 지상무기 수주", "limit": 30, "lookback_days": 180})
    
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
            if cypher_txt.strip():
                res = call_mcp_query_graph(cypher_txt, params)
            else:
                res = call_mcp_query_graph_default(params)
            if not res or not res.get("ok") or not res.get("data"):
                st.error(f"MCP query_graph 실패: {res}")
            else:
                rows = res.get("data", [])
                st.success(f"노드 {len(rows)}개 수신")
                colA, colB = st.columns([1, 1])
                with colA:
                    st.json(rows[:5])
                with colB:
                    render_pyvis_graph(rows, key_prefix="graph")
        except Exception as e:
            st.exception(e)

# ========== 탭 2: Chat ==========
with tab_chat:
    st.subheader("질의 → 뉴스/그래프/주가 스냅샷")
    c_q = st.text_input("질의", value="KAI 방산 수주 컨텍스트 알려줘 005930.KS", key=wkey("q", "chat"))
    c_run = st.button("질의 실행", key=wkey("run", "chat"))
    if c_run:
        try:
            data = call_chat(c_q)
            st.markdown(data.get("answer", ""))
            with st.expander("메타/소스 보기"):
                st.json(data)
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
