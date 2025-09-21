# Neo4j 분석용 Cypher 쿼리 예시

## 🔍 기본 조회 쿼리

### 1. 전체 노드 수 확인
```cypher
MATCH (n)
RETURN labels(n) as NodeType, count(n) as Count
ORDER BY Count DESC
```

### 2. 최근 뉴스 이벤트 조회
```cypher
MATCH (n:News)-[:MENTIONS]->(e:Event)
WHERE e.published_at IS NOT NULL
RETURN n.articleId, n.url, e.title, e.event_type, e.published_at
ORDER BY e.published_at DESC
LIMIT 10
```

### 3. 특정 기업의 모든 이벤트 조회
```cypher
MATCH (c:Company {name: "현대차"})-[:PARTY_TO]->(e:Event)
RETURN c.name, c.ticker, e.title, e.event_type, e.sentiment, e.confidence
ORDER BY e.published_at DESC
```

## 📊 상장사 분석 쿼리

### 4. 상장사별 이벤트 수 통계
```cypher
MATCH (c:Company)-[:PARTY_TO]->(e:Event)
WHERE c.is_listed = true
RETURN c.name, c.ticker, c.market, count(e) as EventCount
ORDER BY EventCount DESC
LIMIT 20
```

### 5. 실적 발표 이벤트 조회
```cypher
MATCH (c:Company)-[:PARTY_TO]->(e:Event {event_type: "Earnings"})-[:HAS_FINANCIAL_DATA]->(f:FinancialMetric)
RETURN c.name, c.ticker, e.title, f.metric_type, f.amount, f.currency, f.period
ORDER BY e.published_at DESC
```

### 6. 투자/인수합병 이벤트 조회
```cypher
MATCH (c:Company)-[:PARTY_TO]->(e:Event)-[:INVOLVES_INVESTMENT]->(i:Investment)
WHERE e.event_type IN ["Investment", "Acquisition"]
RETURN c.name, e.title, i.investment_type, i.amount, i.currency, i.stake_percentage
ORDER BY i.amount DESC
```

## 🏭 업종별 분석 쿼리

### 7. 업종별 이벤트 분포
```cypher
MATCH (c:Company)-[:PARTY_TO]->(e:Event)
WHERE c.sector IS NOT NULL
RETURN c.sector, e.event_type, count(*) as Count
ORDER BY c.sector, Count DESC
```

### 8. 방산 관련 제품 이벤트
```cypher
MATCH (p:Product {is_defense_related: true})-[:INVOLVED_IN]->(e:Event)<-[:PARTY_TO]-(c:Company)
RETURN c.name, p.name, p.category, e.title, e.event_type
ORDER BY e.published_at DESC
```

## 💰 재무 분석 쿼리

### 9. 매출 상위 기업 (최근 실적 기준)
```cypher
MATCH (c:Company)-[:PARTY_TO]->(e:Event)-[:HAS_FINANCIAL_DATA]->(f:FinancialMetric {metric_type: "revenue"})
WHERE f.amount IS NOT NULL AND f.period CONTAINS "2024"
RETURN c.name, c.ticker, f.amount, f.currency, f.period, f.year_over_year
ORDER BY f.amount DESC
LIMIT 10
```

### 10. 영업이익률 분석
```cypher
MATCH (c:Company)-[:PARTY_TO]->(e:Event)-[:HAS_FINANCIAL_DATA]->(revenue:FinancialMetric {metric_type: "revenue"})
MATCH (c)-[:PARTY_TO]->(e)-[:HAS_FINANCIAL_DATA]->(profit:FinancialMetric {metric_type: "operating_profit"})
WHERE revenue.period = profit.period AND revenue.amount > 0
RETURN c.name, c.ticker, revenue.period,
       revenue.amount as Revenue,
       profit.amount as OperatingProfit,
       round(100.0 * profit.amount / revenue.amount, 2) as OperatingMargin
ORDER BY OperatingMargin DESC
```

## 🌐 글로벌 분석 쿼리

### 11. 해외 진출 기업 분석
```cypher
MATCH (c:Company)-[:PARTY_TO]->(e:Event)<-[:INVOLVED_IN]-(country:Country)
WHERE country.code <> "KR"
RETURN c.name, c.sector, country.name, count(e) as EventCount
ORDER BY EventCount DESC
```

### 12. 수출 계약 분석
```cypher
MATCH (c:Company)-[:PARTY_TO]->(e:Event {event_type: "Export"})-[:HAS_CONTRACT]->(contract:Contract)
MATCH (e)<-[:INVOLVED_IN]-(country:Country)
RETURN c.name, country.name, contract.amount, contract.value_ccy, e.title
ORDER BY contract.amount DESC
```

## 🔗 네트워크 분석 쿼리

### 13. 기업간 협력 네트워크
```cypher
MATCH (c1:Company)-[:PARTY_TO]->(e:Event {event_type: "Partnership"})<-[:PARTY_TO]-(c2:Company)
WHERE c1.name < c2.name  // 중복 제거
RETURN c1.name, c2.name, e.title, e.published_at
ORDER BY e.published_at DESC
```

### 14. 뉴스 기사별 연관 기업 수
```cypher
MATCH (n:News)-[:MENTIONS]->(e:Event)<-[:PARTY_TO]-(c:Company)
RETURN n.articleId, n.url, count(DISTINCT c) as CompanyCount
ORDER BY CompanyCount DESC
LIMIT 10
```

## 📈 트렌드 분석 쿼리

### 15. 월별 이벤트 트렌드
```cypher
MATCH (e:Event)
WHERE e.published_at IS NOT NULL
RETURN substring(e.published_at, 0, 7) as YearMonth,
       e.event_type,
       count(*) as Count
ORDER BY YearMonth DESC, Count DESC
```

### 16. 감정 분석 (긍정/부정 뉴스 비율)
```cypher
MATCH (c:Company)-[:PARTY_TO]->(e:Event)
WHERE c.is_listed = true AND e.sentiment IS NOT NULL
RETURN c.name, c.ticker,
       count(CASE WHEN e.sentiment = "positive" THEN 1 END) as PositiveNews,
       count(CASE WHEN e.sentiment = "negative" THEN 1 END) as NegativeNews,
       count(CASE WHEN e.sentiment = "neutral" THEN 1 END) as NeutralNews,
       count(*) as TotalNews
ORDER BY TotalNews DESC
LIMIT 20
```

## 🎯 신뢰도 기반 쿼리

### 17. 고신뢰도 이벤트만 조회
```cypher
MATCH (c:Company)-[:PARTY_TO]->(e:Event)
WHERE e.confidence >= 0.8
RETURN c.name, e.title, e.event_type, e.confidence, e.sentiment
ORDER BY e.confidence DESC
```

### 18. 근거 텍스트 포함 이벤트 조회
```cypher
MATCH (e:Event)-[:HAS_EVIDENCE]->(evidence:Evidence)
RETURN e.title, e.event_type, collect(evidence.text)[0..2] as EvidenceTexts
LIMIT 10
```

## 🔍 고급 분석 쿼리

### 19. 기업 이벤트 영향도 분석 (PageRank)
```cypher
CALL gds.pageRank.stream('companyGraph')
YIELD nodeId, score
MATCH (c:Company)
WHERE id(c) = nodeId
RETURN c.name, c.ticker, score
ORDER BY score DESC
LIMIT 10
```

### 20. 유사한 이벤트 패턴 찾기
```cypher
MATCH (c1:Company)-[:PARTY_TO]->(e1:Event {event_type: "Acquisition"})
MATCH (c2:Company)-[:PARTY_TO]->(e2:Event {event_type: "Acquisition"})
WHERE c1.sector = c2.sector AND c1 <> c2
AND abs(duration.between(date(e1.published_at), date(e2.published_at)).days) <= 30
RETURN c1.name, c2.name, c1.sector, e1.title, e2.title,
       date(e1.published_at) as Date1, date(e2.published_at) as Date2
ORDER BY Date1 DESC
```

## 📊 대시보드용 집계 쿼리

### 21. 일일 이벤트 통계
```cypher
MATCH (e:Event)
WHERE e.published_at IS NOT NULL
RETURN date(e.published_at) as Date,
       count(*) as TotalEvents,
       count(CASE WHEN e.event_type = "Earnings" THEN 1 END) as EarningsEvents,
       count(CASE WHEN e.event_type = "Investment" THEN 1 END) as InvestmentEvents,
       count(CASE WHEN e.event_type = "Acquisition" THEN 1 END) as AcquisitionEvents
ORDER BY Date DESC
LIMIT 30
```

### 22. 시가총액별 기업 분포
```cypher
MATCH (c:Company)
WHERE c.market_cap IS NOT NULL AND c.is_listed = true
RETURN
  CASE
    WHEN c.market_cap >= 10000 THEN "대형주 (1조원 이상)"
    WHEN c.market_cap >= 3000 THEN "중형주 (3천억-1조원)"
    WHEN c.market_cap >= 1000 THEN "소형주 (1천억-3천억원)"
    ELSE "소형주 (1천억원 미만)"
  END as MarketCapCategory,
  count(*) as CompanyCount
ORDER BY CompanyCount DESC
```

## 💡 사용 팁

1. **성능 최적화**: 대용량 데이터 조회 시 `LIMIT`과 `ORDER BY`를 활용
2. **인덱스 활용**: 자주 사용하는 속성에 인덱스 생성 권장
3. **파라미터 사용**: 동적 쿼리에는 파라미터 바인딩 사용
4. **프로파일링**: `PROFILE` 또는 `EXPLAIN` 으로 쿼리 성능 분석

### 인덱스 생성 예시
```cypher
CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name);
CREATE INDEX event_type IF NOT EXISTS FOR (e:Event) ON (e.event_type);
CREATE INDEX event_published IF NOT EXISTS FOR (e:Event) ON (e.published_at);
```