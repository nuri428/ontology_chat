// Params: $q, $limit, $lookback_days, $domain (optional)
WITH $q AS q,
     coalesce($domain, "")         AS d,
     coalesce($lookback_days, 180) AS lb_days
WITH [t IN split(toLower(q), " ") WHERE size(t) >= 2] AS toks,
     [t IN split(toLower(d), " ") WHERE size(t) >= 2] AS domain_toks,
     datetime() - duration({days: lb_days})          AS lookback_ts,
     ['ContractAward','Order','Export','Delivery','Production','MOU','Certification'] AS desired_types

// A) 시드
UNWIND ['Company','Weapon','Program'] AS L
MATCH (s)
WHERE L IN labels(s)
  AND (
    ANY(t IN toks WHERE ANY(k IN keys(s) WHERE s[k] IS NOT NULL AND toLower(toString(s[k])) CONTAINS t))
    OR (size(domain_toks) > 0 AND ANY(t IN domain_toks WHERE ANY(k IN keys(s) WHERE s[k] IS NOT NULL AND toLower(toString(s[k])) CONTAINS t)))
  )
WITH collect(DISTINCT s) AS seeds, lookback_ts, desired_types

// B) 이벤트
UNWIND seeds AS s
MATCH (s)-[*1..2]-(e:Event)
WHERE e.event_type IN desired_types
WITH DISTINCT e, lookback_ts
WITH e,
     CASE
       WHEN e.published_at IS NOT NULL AND toString(e.published_at) =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}.*' THEN datetime(toString(e.published_at))
       ELSE datetime('1970-01-01T00:00:00Z')
     END AS ts_e,
     lookback_ts
WHERE ts_e >= lookback_ts
WITH collect(DISTINCT e) AS events

// C) 계약
UNWIND events AS e1
OPTIONAL MATCH (e1)-[*0..1]-(ct:Contract)
WITH collect(DISTINCT ct) AS contracts, collect(DISTINCT e1) AS events

// D) 컨텍스트 회사
UNWIND events AS e2
OPTIONAL MATCH (e2)-[]-(c1:Company)
WITH events, contracts, collect(DISTINCT c1) AS companies_e
UNWIND contracts AS ct2
OPTIONAL MATCH (ct2)-[]-(c2:Company)
WITH events, contracts, companies_e, collect(DISTINCT c2) AS companies_from_ct
WITH events, contracts, companies_e + companies_from_ct AS companies

// E) 뉴스
UNWIND events AS e3
OPTIONAL MATCH (n1:News)-[]-(e3)
WITH events, contracts, companies, collect(DISTINCT n1) AS news_e
UNWIND contracts AS ct3
OPTIONAL MATCH (n2:News)-[]-(ct3)
WITH events, contracts, companies, news_e, collect(DISTINCT n2) AS news_from_ct
WITH events, contracts, companies, news_e + news_from_ct AS news_ec
UNWIND companies AS c3
OPTIONAL MATCH (n3:News)-[]-(c3)
WITH events, contracts, companies, news_ec, collect(DISTINCT n3) AS news_from_co
WITH events, contracts, companies, news_ec + news_from_co AS news

// F) 합치기 — 스코프 유지용 서브쿼리
CALL {
  // Events
  WITH events
  UNWIND events AS ev
  WITH ev, labels(ev) AS labels
  WITH ev AS n, labels
  WITH n, labels,
       CASE
         WHEN n.published_at IS NOT NULL AND toString(n.published_at) =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}.*'
           THEN datetime(toString(n.published_at))
         ELSE datetime('1970-01-01T00:00:00Z')
       END AS ts
  RETURN n, labels, ts

  UNION

  // Contracts
  WITH contracts
  UNWIND contracts AS ct
  WITH ct, labels(ct) AS labels
  WITH ct AS n, labels
  WITH n, labels,
       CASE
         WHEN n.award_date IS NOT NULL AND toString(n.award_date) =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}.*'
           THEN datetime(toString(n.award_date))
         ELSE datetime('1970-01-01T00:00:00Z')
       END AS ts
  RETURN n, labels, ts

  UNION

  // Companies
  WITH companies
  UNWIND companies AS co
  WITH co, labels(co) AS labels
  WITH co AS n, labels
  WITH n, labels,
       CASE
         WHEN n.lastSeenAt IS NOT NULL AND toString(n.lastSeenAt) =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}.*'
           THEN datetime(toString(n.lastSeenAt))
         ELSE datetime('1970-01-01T00:00:00Z')
       END AS ts
  RETURN n, labels, ts

  UNION

  // News
  WITH news
  UNWIND news AS nw
  WITH nw, labels(nw) AS labels
  WITH nw AS n, labels
  WITH n, labels,
       CASE
         WHEN n.lastSeenAt IS NOT NULL AND toString(n.lastSeenAt) =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}.*'
           THEN datetime(toString(n.lastSeenAt))
         ELSE datetime('1970-01-01T00:00:00Z')
       END AS ts
  RETURN n, labels, ts
}
RETURN n, labels, ts
ORDER BY ts DESC
LIMIT $limit