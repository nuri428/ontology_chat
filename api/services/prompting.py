from __future__ import annotations
from typing import List, Dict
from pathlib import Path
from textwrap import shorten

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

def _read(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")

_SYSTEM = _read("system.kr.md")
_USER = _read("user.kr.md")
_STYLE = _read("style.kr.md")

def build_news_bullets(hits: List[Dict], max_items: int = 5) -> str:
    lines = []
    for h in hits[:max_items]:
        src = h.get("_source", {}) or {}
        title = src.get("title") or "(제목 없음)"
        url = src.get("url") or ""
        date = src.get("created_datetime") or src.get("created_date") or ""
        bullet = f"- {shorten(title, width=120, placeholder='…')} ({date}) [{url}]"
        lines.append(bullet)
    return "\n".join(lines) if lines else "(뉴스 없음)"

def build_graph_summary(graph_summary: Dict | None) -> str:
    if not graph_summary:
        return "(그래프 컨텍스트 없음)"
    # summarize_graph_rows에서 만들어준 구조를 그대로 문자열화
    # 예: {"Event":[...], "Company":[...]} 등
    out = []
    for k, items in graph_summary.items():
        rows = [f"- {shorten(str(it), 140)}" for it in items[:5]]
        out.append(f"[{k}]\n" + "\n".join(rows))
    return "\n\n".join(out)

def build_stock_snapshot(stock: Dict | None) -> str:
    if not stock:
        return "(시세 없음)"
    symbol = stock.get("symbol")
    price = stock.get("price")
    return f"{symbol}: {price}"

def build_messages(
    query: str,
    news_hits: List[Dict],
    graph_summary: Dict | None,
    stock: Dict | None,
) -> List[Dict[str, str]]:
    news_bullets = build_news_bullets(news_hits)
    graph_text = build_graph_summary(graph_summary)
    stock_text = build_stock_snapshot(stock)

    user_filled = (
        _USER
        .replace("{{query}}", query)
        .replace("{{news_bullets}}", news_bullets)
        .replace("{{graph_summary}}", graph_text)
        .replace("{{stock_snapshot}}", stock_text)
    )

    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "system", "content": _STYLE},
        {"role": "user", "content": user_filled},
    ]