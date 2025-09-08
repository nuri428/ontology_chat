# src/ontology_chat/services/formatters.py
from __future__ import annotations
from datetime import datetime, timezone
from collections import defaultdict

EPOCH_FALLBACK = datetime(1970,1,1,tzinfo=timezone.utc)

def _ts_to_dt(ts_obj: dict | None) -> datetime:
    # neo4j 드라이버가 리턴한 ts를 datetime으로 안전 변환
    if not ts_obj:
        return EPOCH_FALLBACK
    try:
        d = ts_obj.get("_DateTime__date", {})
        t = ts_obj.get("_DateTime__time", {})
        year = d.get("_Date__year", 1970)
        month = d.get("_Date__month", 1)
        day = d.get("_Date__day", 1)
        hour = t.get("_Time__hour", 0)
        minute = t.get("_Time__minute", 0)
        second = t.get("_Time__second", 0)
        # ns는 무시
        return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    except Exception:
        return EPOCH_FALLBACK

def _label(labels: list[str]) -> str:
    # 다중 라벨 대비: 가장 의미 있는 것 우선
    priority = ["Event","Contract","Company","News","Weapon","Program","Agency","Country","Evidence"]
    for p in priority:
        if p in labels:
            return p
    return labels[0] if labels else "Node"

def summarize_graph_rows(rows: list[dict], max_each: int = 5) -> dict:
    """
    rows: [{ "n": {...}, "labels": [...], "ts": {...} }]
    return: {
      "events": [...], "contracts":[...], "companies":[...], "news":[...],
      "topline": {...}
    }
    """
    buckets = defaultdict(list)
    for r in rows:
        lbl = _label(r.get("labels", []))
        n = r.get("n", {})
        ts = _ts_to_dt(r.get("ts"))
        buckets[lbl].append({"node": n, "ts": ts})

    # 최신순 정렬
    for k in list(buckets.keys()):
        buckets[k].sort(key=lambda x: x["ts"], reverse=True)

    # 간단 요약 스냅샷
    contracts = [{
        "contractId": c["node"].get("contractId"),
        "amount": c["node"].get("amount"),
        "ccy": c["node"].get("value_ccy"),
        "award_date": c["node"].get("award_date"),
        "ts": c["ts"].isoformat(),
    } for c in buckets.get("Contract", [])[:max_each]]

    events = [{
        "event_type": e["node"].get("event_type"),
        "title": e["node"].get("title"),
        "published_at": e["node"].get("published_at"),
        "ts": e["ts"].isoformat(),
    } for e in buckets.get("Event", [])[:max_each]]

    companies = [{
        "name": co["node"].get("name"),
        "ticker": co["node"].get("ticker"),
        "ts": co["ts"].isoformat(),
    } for co in buckets.get("Company", [])[:max_each]]

    news = [{
        "url": nw["node"].get("url"),
        "articleId": nw["node"].get("articleId"),
        "ts": nw["ts"].isoformat(),
    } for nw in buckets.get("News", [])[:max_each]]

    topline = {
        "counts": {k: len(v) for k, v in buckets.items()},
        "latest_contract_award_date": contracts[0]["award_date"] if contracts else None,
        "latest_event_type": events[0]["event_type"] if events else None,
    }

    return {
        "events": events,
        "contracts": contracts,
        "companies": companies,
        "news": news,
        "topline": topline,
    }