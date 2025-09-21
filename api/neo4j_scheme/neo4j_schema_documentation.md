# Neo4j 온톨로지 스키마 문서

## 📊 노드 타입 및 속성

### 1. **News** (뉴스 기사)
- **레이블**: `News`
- **고유키**: `articleId` (뉴스 기사 ID)
- **속성**:
  - `articleId`: 뉴스 기사 고유 ID
  - `url`: 뉴스 기사 URL
  - `lastSeenAt`: 마지막 처리 시간

### 2. **Event** (비즈니스 이벤트)
- **레이블**: `Event`
- **고유키**: `eventId` (이벤트 고유 ID)
- **속성**:
  - `eventId`: 이벤트 고유 ID
  - `event_type`: 이벤트 유형 (Earnings, Investment, Acquisition 등)
  - `published_at`: 발행 시간 (ISO datetime)
  - `title`: 이벤트 제목
  - `sentiment`: 감정 (positive, neutral, negative)
  - `confidence`: 신뢰도 (0.0-1.0)

### 3. **Company** (기업/상장사)
- **레이블**: `Company`
- **고유키**: `name` (기업명)
- **속성**:
  - `name`: 기업명
  - `ticker`: 주식 코드 (예: "005930")
  - `market`: 거래소 (KOSPI, KOSDAQ, KONEX)
  - `sector`: 업종
  - `market_cap`: 시가총액 (억원)
  - `is_listed`: 상장 여부 (boolean)

### 4. **Evidence** (근거 텍스트)
- **레이블**: `Evidence`
- **고유키**: `eventId + text` (이벤트별 근거 텍스트)
- **속성**:
  - `eventId`: 연결된 이벤트 ID
  - `text`: 근거 텍스트 내용

### 5. **Contract** (계약/수주)
- **레이블**: `Contract`
- **고유키**: `contractId` (계약 ID)
- **속성**:
  - `contractId`: 계약 고유 ID
  - `amount`: 계약 금액
  - `value_ccy`: 통화 (KRW, USD 등)
  - `award_date`: 계약 체결일 (ISO date)

### 6. **Country** (국가)
- **레이블**: `Country`
- **고유키**: `code` (국가 코드)
- **속성**:
  - `code`: 국가 코드 (KR, US, CN 등)
  - `name`: 국가명

### 7. **Product** (제품/서비스)
- **레이블**: `Product`
- **고유키**: `name` (제품명)
- **속성**:
  - `name`: 제품명
  - `category`: 카테고리 (weapon, vehicle, electronics 등)
  - `description`: 제품 설명
  - `is_defense_related`: 방산 관련 여부 (boolean)
  - `product_type`: 제품 유형 (hardware, software, service)

### 8. **FinancialMetric** (재무 지표)
- **레이블**: `FinancialMetric`
- **고유키**: `eventId + metric_type` (이벤트별 재무 지표)
- **속성**:
  - `eventId`: 연결된 이벤트 ID
  - `metric_type`: 지표 유형 (revenue, operating_profit, net_income 등)
  - `amount`: 금액
  - `currency`: 통화 (기본값: KRW)
  - `period`: 기간 (2024Q1, 2024 등)
  - `year_over_year`: 전년대비 증감률

### 9. **Investment** (투자 정보)
- **레이블**: `Investment`
- **고유키**: `eventId + investment_type` (이벤트별 투자 정보)
- **속성**:
  - `eventId`: 연결된 이벤트 ID
  - `investment_type`: 투자 유형 (equity, debt 등)
  - `amount`: 투자 금액
  - `currency`: 통화 (기본값: KRW)
  - `stake_percentage`: 지분율
  - `purpose`: 투자 목적

### 10. **Program** (방산 프로그램) - 조건부
- **레이블**: `Program`
- **고유키**: `code` (프로그램 코드)
- **속성**:
  - `code`: 프로그램 코드
  - `label`: 프로그램명
  - `isOfficial`: 공식 프로그램 여부

### 11. **Agency** (방산 기관) - 조건부
- **레이블**: `Agency`
- **고유키**: `code` (기관 코드)
- **속성**:
  - `code`: 기관 코드
  - `label`: 기관명

## 🔗 관계 타입 및 방향

### 1. **News → Event**
- **관계**: `MENTIONS`
- **방향**: `(News)-[:MENTIONS]->(Event)`
- **의미**: 뉴스가 특정 이벤트를 언급함

### 2. **Event → Evidence**
- **관계**: `HAS_EVIDENCE`
- **방향**: `(Event)-[:HAS_EVIDENCE]->(Evidence)`
- **의미**: 이벤트가 특정 근거 텍스트를 가짐

### 3. **Company → Event**
- **관계**: `PARTY_TO`
- **방향**: `(Company)-[:PARTY_TO]->(Event)`
- **의미**: 기업이 특정 이벤트의 당사자임

### 4. **Event → Contract**
- **관계**: `HAS_CONTRACT`
- **방향**: `(Event)-[:HAS_CONTRACT]->(Contract)`
- **의미**: 이벤트가 특정 계약과 연관됨

### 5. **Country → Event**
- **관계**: `INVOLVED_IN`
- **방향**: `(Country)-[:INVOLVED_IN]->(Event)`
- **의미**: 국가가 특정 이벤트에 관련됨

### 6. **Product → Event**
- **관계**: `INVOLVED_IN`
- **방향**: `(Product)-[:INVOLVED_IN]->(Event)`
- **의미**: 제품이 특정 이벤트에 관련됨

### 7. **Event → FinancialMetric**
- **관계**: `HAS_FINANCIAL_DATA`
- **방향**: `(Event)-[:HAS_FINANCIAL_DATA]->(FinancialMetric)`
- **의미**: 이벤트가 특정 재무 데이터를 가짐

### 8. **Event → Investment**
- **관계**: `INVOLVES_INVESTMENT`
- **방향**: `(Event)-[:INVOLVES_INVESTMENT]->(Investment)`
- **의미**: 이벤트가 특정 투자와 관련됨

### 9. **Program → Event** (방산 전용)
- **관계**: `SUBJECT_OF`
- **방향**: `(Program)-[:SUBJECT_OF]->(Event)`
- **의미**: 방산 프로그램이 특정 이벤트의 주체임

### 10. **Agency → Event** (방산 전용)
- **관계**: `INVOLVED_IN`
- **방향**: `(Agency)-[:INVOLVED_IN]->(Event)`
- **의미**: 방산 기관이 특정 이벤트에 관련됨

## 📋 이벤트 타입 목록

### 상장사/경제 이벤트
- `Earnings`: 실적 발표
- `Investment`: 투자/출자
- `Acquisition`: 인수합병
- `Partnership`: 파트너십
- `IPO`: 신규상장
- `StockSplit`: 주식분할
- `Dividend`: 배당
- `CapitalIncrease`: 증자
- `BusinessExpansion`: 사업확장
- `Restructuring`: 구조조정

### 방산/계약 이벤트
- `ContractAward`: 계약 체결
- `Export`: 수출
- `Test`: 시험/테스트
- `Delivery`: 납품/인도
- `R&D`: 연구개발
- `MOU`: 양해각서
- `Certification`: 인증
- `Production`: 생산
- `Order`: 주문/발주
- `Policy`: 정책

## 🎯 핵심 그래프 패턴

### 1. 뉴스 중심 패턴
```cypher
(News)-[:MENTIONS]->(Event)-[:HAS_EVIDENCE]->(Evidence)
```

### 2. 상장사 실적 패턴
```cypher
(Company)-[:PARTY_TO]->(Event:Earnings)-[:HAS_FINANCIAL_DATA]->(FinancialMetric)
```

### 3. 투자/인수합병 패턴
```cypher
(Company)-[:PARTY_TO]->(Event:Investment)-[:INVOLVES_INVESTMENT]->(Investment)
```

### 4. 제품 출시 패턴
```cypher
(Company)-[:PARTY_TO]->(Event)-[:INVOLVED_IN]<-(Product)
```

### 5. 계약/수주 패턴
```cypher
(Company)-[:PARTY_TO]->(Event)-[:HAS_CONTRACT]->(Contract)
```