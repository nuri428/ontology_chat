# 스키마 기반 컨텍스트 품질 향상 제안서

**작성 일시**: 2025-10-03 17:30
**목표**: 새로운 스키마 필드를 활용하여 컨텍스트 품질 0.32 → 0.9+ 개선
**현재 상태**: P0 수정 완료, 타임아웃 해결, 품질 점수 낮음

---

## 🎯 문제 정의

### 현재 상황
- ✅ **Context Engineering**: 85% 완성도 (6단계 파이프라인 정상 작동)
- ✅ **타임아웃**: 해결 완료 (240초 여유)
- ❌ **품질 점수**: 0.32 (목표 0.9+)
- ⚠️ **원인**: 메타데이터 미활용

### 품질 점수가 낮은 이유

**현재 활용 중인 메타데이터** (기본):
- `source` (출처)
- `confidence` (기본 신뢰도)
- `timestamp` (시간)
- `content` (내용)

**활용하지 않는 고품질 메타데이터** (신규 스키마):
- ⭐⭐⭐ `quality_score` (품질 점수) - **핵심**
- ⭐⭐⭐ `is_featured` (추천 콘텐츠) - **핵심**
- ⭐⭐⭐ `neo4j_synced` (그래프 동기화 여부) - **핵심**
- ⭐⭐ `event_chain_id` (이벤트 체인)
- ⭐⭐ `ontology_status` (온톨로지 상태)
- ⭐⭐ `neo4j_node_count` (연결 노드 수)

---

## 📊 신규 스키마 분석

### MySQL (news_db) - 메타데이터 저장소

#### ⭐⭐⭐ 필수 활용 필드

1. **`quality_score`** (DECIMAL(3,2))
   - **의미**: 콘텐츠 품질 점수 (0.0 - 1.0)
   - **활용**: Context Engineering 필터링 및 재정렬
   - **효과**: 고품질 콘텐츠 우선 선택

2. **`is_featured`** (BOOLEAN)
   - **의미**: 추천/중요 콘텐츠 플래그
   - **활용**: 우선순위 최상위로 상향
   - **효과**: 핵심 콘텐츠 보장

3. **`neo4j_synced`** (BOOLEAN)
   - **의미**: Neo4j 그래프 동기화 완료 여부
   - **활용**: 그래프 연결 데이터 우선 선택
   - **효과**: 관계 분석 품질 향상

#### ⭐⭐ 중요 활용 필드

4. **`event_chain_id`** (VARCHAR(255))
   - **의미**: 연속된 이벤트 체인 ID
   - **활용**: 이벤트 흐름 추적
   - **효과**: 시계열 분석 품질 향상

5. **`ontology_status`** (ENUM: pending/processing/completed/failed)
   - **의미**: 온톨로지 처리 상태
   - **활용**: completed 상태 우선 선택
   - **효과**: 완전히 처리된 데이터만 사용

6. **`neo4j_node_count`** (INT)
   - **의미**: 연결된 Neo4j 노드 개수
   - **활용**: 높은 연결성 데이터 우선
   - **효과**: 풍부한 관계 정보 확보

#### ⭐ 보조 활용 필드

7. **`neo4j_last_sync`** (TIMESTAMP)
   - **의미**: 마지막 Neo4j 동기화 시각
   - **활용**: 최신 동기화 데이터 우선

8. **`related_news_count`** (INT)
   - **의미**: 관련 뉴스 개수
   - **활용**: 다양한 관점 확보

### Neo4j - 지식 그래프

#### 노드 타입 (10가지)
1. **News**: 뉴스 기사
2. **Event**: 이벤트
3. **Company**: 기업
4. **Contract**: 계약
5. **FinancialMetric**: 재무 지표
6. **Person**: 인물
7. **Technology**: 기술
8. **Product**: 제품
9. **Location**: 지역
10. **Theme**: 테마/주제

#### 관계 타입
- `MENTIONS`: 언급
- `PARTY_TO`: 계약 당사자
- `HAS_CONTRACT`: 계약 보유
- `LOCATED_IN`: 위치
- `EMPLOYS`: 고용
- `DEVELOPS`: 개발
- `COMPETES_WITH`: 경쟁

---

## 🔧 개선 방안

### Phase 1: 메타데이터 기반 필터링 강화 (P1)

**목표**: `quality_score`, `is_featured`, `neo4j_synced` 활용

#### 1.1 Context 준비 단계 수정

**위치**: `langgraph_report_service.py::_prepare_contexts_for_engineering`

**현재 코드**:
```python
ctx_dict = {
    "source": ctx.source,
    "type": ctx.type,
    "content": str(ctx.content.get("title", "")) + " " + str(ctx.content.get("summary", ""))[:500],
    "confidence": ctx.confidence,
    "relevance": ctx.relevance,
    "timestamp": ctx.timestamp,
    "metadata": ctx.content
}
```

**개선 코드**:
```python
ctx_dict = {
    "source": ctx.source,
    "type": ctx.type,
    "content": str(ctx.content.get("title", "")) + " " + str(ctx.content.get("summary", ""))[:500],
    "confidence": ctx.confidence,
    "relevance": ctx.relevance,
    "timestamp": ctx.timestamp,
    "metadata": ctx.content,

    # ⭐⭐⭐ 신규 스키마 필드 추가
    "quality_score": ctx.content.get("quality_score", 0.5),  # MySQL quality_score
    "is_featured": ctx.content.get("is_featured", False),    # MySQL is_featured
    "neo4j_synced": ctx.content.get("neo4j_synced", False),  # MySQL neo4j_synced

    # ⭐⭐ 보조 필드
    "event_chain_id": ctx.content.get("event_chain_id"),
    "ontology_status": ctx.content.get("ontology_status", "unknown"),
    "neo4j_node_count": ctx.content.get("neo4j_node_count", 0),
}
```

#### 1.2 출처 우선순위 수정

**위치**: `langgraph_report_service.py::_filter_by_source_priority`

**현재 코드**:
```python
source_weights = {
    "neo4j": 1.3,      # 구조화된 그래프 데이터
    "opensearch": 1.0,  # 뉴스 데이터
    "stock": 0.8        # 시장 데이터
}
```

**개선 코드**:
```python
source_weights = {
    "neo4j": 1.3,
    "opensearch": 1.0,
    "stock": 0.8
}

# 출처 가중치 + 품질 점수 조합
for ctx in contexts:
    source = ctx.get("source", "unknown")
    base_weight = source_weights.get(source, 0.5)

    # ⭐⭐⭐ quality_score 반영 (0.0-1.0)
    quality_score = ctx.get("quality_score", 0.5)

    # ⭐⭐⭐ is_featured 보너스 (+0.3)
    featured_bonus = 0.3 if ctx.get("is_featured", False) else 0

    # ⭐⭐⭐ neo4j_synced 보너스 (+0.2)
    synced_bonus = 0.2 if ctx.get("neo4j_synced", False) else 0

    # 최종 가중치 = 출처 * (품질 + 보너스)
    final_weight = base_weight * (quality_score + featured_bonus + synced_bonus)

    ctx["source_weight"] = final_weight
    ctx["confidence"] = min(ctx.get("confidence", 0.5) * final_weight, 1.0)
```

**예상 효과**:
- 고품질 콘텐츠 (`quality_score` 0.9) → confidence 상승
- Featured 콘텐츠 → 최우선 선택
- Neo4j 동기화 콘텐츠 → 관계 분석 품질 향상

---

### Phase 2: 메타데이터 재정렬 강화 (P1)

**위치**: `langgraph_report_service.py::_rerank_with_metadata`

**현재 코드**:
```python
metadata_score = (
    semantic_score * 0.35 +      # Semantic 관련성
    source_weight * 0.25 +       # 출처 신뢰도
    recency_score * 0.20 +       # 최신성
    confidence * 0.10 +          # 신뢰도
    plan_alignment * 0.10        # 분석 계획 적합성
)
```

**개선 코드**:
```python
# 기본 점수 (60%)
base_score = (
    semantic_score * 0.30 +      # Semantic 관련성
    source_weight * 0.15 +       # 출처 신뢰도
    recency_score * 0.15         # 최신성
)

# ⭐⭐⭐ 품질 메타데이터 (40%)
quality_metadata_score = (
    ctx.get("quality_score", 0.5) * 0.20 +  # MySQL quality_score (20%)
    (1.0 if ctx.get("is_featured", False) else 0.0) * 0.10 +  # is_featured (10%)
    (1.0 if ctx.get("neo4j_synced", False) else 0.0) * 0.10   # neo4j_synced (10%)
)

# 최종 점수
metadata_score = base_score + quality_metadata_score
```

**가중치 재배분**:
- Semantic 관련성: 35% → 30% (여전히 중요)
- 출처 신뢰도: 25% → 15%
- 최신성: 20% → 15%
- **quality_score: 0% → 20%** (신규)
- **is_featured: 0% → 10%** (신규)
- **neo4j_synced: 0% → 10%** (신규)

---

### Phase 3: 온톨로지 상태 필터링 (P2)

**목표**: `ontology_status`, `neo4j_node_count` 활용

#### 3.1 온톨로지 완료 필터

**위치**: `_filter_by_confidence` 이후 추가

**신규 함수**:
```python
def _filter_by_ontology_status(self, contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """온톨로지 처리 상태 기반 필터링 (Cascading Step 4)

    우선순위:
    1. completed (완료) - 최우선
    2. processing (처리 중) - 차선
    3. pending (대기) - 보조
    4. failed (실패) - 제외
    """
    status_priority = {
        "completed": 1.0,
        "processing": 0.7,
        "pending": 0.4,
        "failed": 0.0  # 제외
    }

    filtered = []
    for ctx in contexts:
        status = ctx.get("ontology_status", "unknown")
        priority = status_priority.get(status, 0.5)

        if priority > 0:  # failed 제외
            ctx["ontology_priority"] = priority
            filtered.append(ctx)

    return sorted(filtered, key=lambda x: x.get("ontology_priority", 0), reverse=True)
```

#### 3.2 Neo4j 연결성 보너스

**위치**: `_rerank_with_metadata` 내부 추가

```python
# Neo4j 연결성 보너스
neo4j_node_count = ctx.get("neo4j_node_count", 0)
connectivity_bonus = min(neo4j_node_count / 10.0, 0.3)  # 최대 0.3 보너스

# 이벤트 체인 보너스
has_event_chain = bool(ctx.get("event_chain_id"))
event_chain_bonus = 0.1 if has_event_chain else 0

# 최종 점수에 반영
metadata_score = base_score + quality_metadata_score + connectivity_bonus + event_chain_bonus
```

**효과**:
- 10개 이상 노드 연결 → +0.3 보너스
- 이벤트 체인 존재 → +0.1 보너스

---

### Phase 4: 그래프 관계 활용 (P2)

**목표**: Neo4j 관계 정보 활용

#### 4.1 관계 기반 컨텍스트 확장

**신규 함수**:
```python
async def _expand_contexts_via_graph(
    self,
    contexts: List[Dict[str, Any]],
    query_entities: List[str]
) -> List[Dict[str, Any]]:
    """Neo4j 그래프 관계를 활용한 컨텍스트 확장

    전략:
    1. neo4j_synced=true 컨텍스트에서 시작
    2. MENTIONS, PARTY_TO 관계 추적
    3. 연결된 Company, Event 노드 추가
    """
    expanded = []

    for ctx in contexts:
        expanded.append(ctx)

        # Neo4j 동기화된 항목만 확장
        if ctx.get("neo4j_synced", False):
            # 관련 엔티티 추출 (예: Company, Event)
            related_entities = await self._get_related_entities_from_neo4j(
                news_id=ctx.get("id"),
                entity_types=["Company", "Event", "Contract"]
            )

            # 관련 엔티티를 컨텍스트로 추가 (최대 5개)
            for entity in related_entities[:5]:
                expanded.append({
                    "source": "neo4j_expansion",
                    "type": entity["type"],
                    "content": entity["content"],
                    "confidence": 0.8,  # 그래프 확장은 중간 신뢰도
                    "quality_score": 0.7,
                    "neo4j_synced": True
                })

    return expanded[:50]  # 최대 50개로 제한
```

#### 4.2 Neo4j 쿼리 헬퍼

```python
async def _get_related_entities_from_neo4j(
    self,
    news_id: str,
    entity_types: List[str]
) -> List[Dict[str, Any]]:
    """Neo4j에서 관련 엔티티 조회

    Cypher 쿼리:
    MATCH (n:News {id: $news_id})-[r:MENTIONS|PARTY_TO]-(e)
    WHERE labels(e) IN $entity_types
    RETURN e, type(r) as relation
    LIMIT 5
    """
    # 실제 Neo4j 쿼리 구현
    # (기존 neo4j 어댑터 활용)
    pass
```

---

## 📈 예상 개선 효과

### Before (현재)
```
Query: "삼성전자와 SK하이닉스 HBM 경쟁력 비교 분석"
복잡도 점수: 1.0 ✅
처리 시간: 92.1초 ✅
품질 점수: 0.32 ❌
인사이트: 3개
관계: 4개

Context Engineering:
- Source filtering: 50 → 50
- Confidence filtering: 50 → 42
- 최종: 30개
- Diversity: 0.39
```

### After (개선 후)
```
Query: "삼성전자와 SK하이닉스 HBM 경쟁력 비교 분석"
복잡도 점수: 1.0 ✅
처리 시간: 95초 ✅ (약간 증가 acceptable)
품질 점수: 0.85+ ✅ (2.7배 향상)
인사이트: 5개 (고품질)
관계: 8개 (그래프 확장)

Context Engineering:
- Source + Quality filtering: 50 → 45 (quality_score > 0.6)
- Featured filtering: 45 → 40 (is_featured 우선)
- Neo4j synced filtering: 40 → 35 (그래프 동기화)
- Ontology status filtering: 35 → 32 (completed 우선)
- Graph expansion: 32 → 42 (관계 확장)
- 최종: 30개 (고품질)
- Diversity: 0.45 (향상)
```

---

## 🎯 구현 우선순위

### P1 (즉시 구현 - 2시간)
1. ✅ `quality_score` 활용 (20% 가중치)
2. ✅ `is_featured` 필터링 (우선순위 최상위)
3. ✅ `neo4j_synced` 보너스 (관계 분석 품질 향상)
4. ✅ 메타데이터 재정렬 로직 수정

**예상 효과**: 품질 점수 0.32 → 0.65 (2배)

### P2 (추가 구현 - 3시간)
1. ⚠️ `ontology_status` 필터링
2. ⚠️ `neo4j_node_count` 연결성 보너스
3. ⚠️ `event_chain_id` 시계열 분석
4. ⚠️ Neo4j 그래프 확장 (관계 추적)

**예상 효과**: 품질 점수 0.65 → 0.85+ (추가 30%)

### P3 (최적화 - 추후)
1. ⚠️ 실시간 품질 점수 계산
2. ⚠️ 그래프 임베딩 활용
3. ⚠️ Multi-hop 관계 추적

---

## 🔧 수정 파일 계획

### 1. api/services/langgraph_report_service.py

**수정 위치**:
- `_prepare_contexts_for_engineering()` (Line 1627-1646): 메타데이터 추가
- `_filter_by_source_priority()` (Line 1648-1669): 품질 점수 반영
- `_rerank_with_metadata()` (Line 1712-1745): 가중치 재배분
- `_filter_by_ontology_status()` (신규 추가): 온톨로지 필터링

**예상 라인 수**: +80줄

### 2. api/services/context_*.py (필요시)

**신규 파일**:
- `context_quality_scorer.py`: 품질 점수 계산 전용 모듈

---

## 📝 테스트 계획

### 1. 단위 테스트
```python
def test_quality_score_filtering():
    contexts = [
        {"quality_score": 0.9, "is_featured": True},   # 최우선
        {"quality_score": 0.7, "is_featured": False},  # 중간
        {"quality_score": 0.3, "is_featured": False},  # 낮음
    ]

    filtered = filter_by_quality(contexts, threshold=0.6)
    assert len(filtered) == 2
    assert filtered[0]["quality_score"] == 0.9
```

### 2. 통합 테스트
```bash
# 품질 점수 0.85+ 달성 확인
curl -X POST http://localhost:8000/mcp/chat \
  -d '{"query": "삼성전자와 SK하이닉스 HBM 경쟁력 비교 분석"}'

# 예상 결과:
# quality_score: 0.85+
# contexts_count: 30 (고품질)
# insights_count: 5+
```

---

## ✅ 결론

### 핵심 전략
1. **quality_score 활용** → 고품질 콘텐츠 우선 선택
2. **is_featured 필터링** → 핵심 콘텐츠 보장
3. **neo4j_synced 보너스** → 관계 분석 품질 향상
4. **ontology_status 필터** → 완전 처리 데이터만 사용

### 예상 개선
- **품질 점수**: 0.32 → 0.85+ (**2.7배 향상**)
- **인사이트**: 3개 → 5개 (고품질)
- **관계**: 4개 → 8개 (그래프 확장)
- **처리 시간**: 92초 → 95초 (3% 증가, acceptable)

### 다음 단계
1. **P1 구현**: `quality_score`, `is_featured`, `neo4j_synced` 활용 (2시간)
2. **테스트**: 품질 점수 0.85+ 검증
3. **P2 구현**: 온톨로지 필터, 그래프 확장 (3시간)

**시작할까요?**
