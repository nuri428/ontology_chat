// Params: $q, $limit, $lookback_days, $domain (optional)
WITH $q AS q,
     coalesce($domain, "")         AS d,
     coalesce($lookback_days, 180) AS lb_days
WITH [t IN split(toLower(q), " ") WHERE size(t) >= 2] AS toks,
     [t IN split(toLower(d), " ") WHERE size(t) >= 2] AS domain_toks,
     datetime() - duration({days: lb_days})          AS lookback_ts,
     ['ContractAward','Order','Export','Delivery','Production','MOU','Certification'] AS desired_types

// A) 시드 노드 찾기
UNWIND ['Company','Weapon','Program'] AS L
MATCH (s)
WHERE L IN labels(s)
  AND (
    ANY(t IN toks WHERE ANY(k IN keys(s) WHERE s[k] IS NOT NULL AND toLower(toString(s[k])) CONTAINS t))
    OR (size(domain_toks) > 0 AND ANY(t IN domain_toks WHERE ANY(k IN keys(s) WHERE s[k] IS NOT NULL AND toLower(toString(s[k])) CONTAINS t)))
  )
WITH collect(DISTINCT s) AS seeds, lookback_ts, desired_types

// B) 시드 노드와 연결된 모든 노드와 관계 찾기
UNWIND seeds AS seed
MATCH path = (seed)-[*1..2]-(connected)
WHERE connected IS NOT NULL
WITH seed, connected, relationships(path) AS rels, lookback_ts, desired_types

// C) 이벤트 필터링
OPTIONAL MATCH (connected:Event)
WHERE connected.event_type IN desired_types
WITH seed, connected, rels, lookback_ts,
     CASE
       WHEN connected.published_at IS NOT NULL AND toString(connected.published_at) =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}.*' 
         THEN datetime(toString(connected.published_at))
       ELSE datetime('1970-01-01T00:00:00Z')
     END AS ts_connected
WHERE ts_connected >= lookback_ts OR connected IS NULL

// D) 모든 노드와 관계 수집
WITH collect(DISTINCT seed) + collect(DISTINCT connected) AS all_nodes,
     collect(DISTINCT rels) AS all_relationships

// E) 노드와 관계 반환
UNWIND all_nodes AS n
WITH n, labels(n) AS labels, all_relationships,
     CASE
       WHEN n.published_at IS NOT NULL AND toString(n.published_at) =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}.*'
         THEN datetime(toString(n.published_at))
       WHEN n.award_date IS NOT NULL AND toString(n.award_date) =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}.*'
         THEN datetime(toString(n.award_date))
       WHEN n.lastSeenAt IS NOT NULL AND toString(n.lastSeenAt) =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}.*'
         THEN datetime(toString(n.lastSeenAt))
       ELSE datetime('1970-01-01T00:00:00Z')
     END AS ts
WHERE n IS NOT NULL
RETURN n, labels, ts, all_relationships
ORDER BY ts DESC
LIMIT $limit