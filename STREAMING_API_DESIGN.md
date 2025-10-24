# 스트리밍 API 설계

## 목표
- 실시간 진행 상황 전송
- 각 LangGraph 단계별 업데이트
- 비동기 처리 (클라이언트 대기 시간 최소화)

## 기술 스택
- FastAPI Server-Sent Events (SSE)
- LangGraph `astream_events()` API
- AsyncIterator 패턴

## API 엔드포인트

### 1. 기존 동기 API (유지)
```
POST /mcp/chat
- 완료된 결과만 반환
- 간단한 클라이언트에 적합
```

### 2. 새로운 스트리밍 API
```
POST /mcp/chat/stream
- Server-Sent Events (SSE)
- 실시간 진행 상황 전송
- 각 단계별 업데이트
```

## 이벤트 타입

### Progress Events
```json
{
  "type": "progress",
  "data": {
    "stage": "analyze_query|plan_analysis|collect_data|...",
    "status": "started|in_progress|completed",
    "message": "쿼리 분석 중...",
    "progress": 0.1,
    "elapsed_time": 2.5
  }
}
```

### Step Events (LangGraph 노드 실행)
```json
{
  "type": "step",
  "data": {
    "node": "generate_insights",
    "status": "started|completed|failed",
    "result": {
      "insights_count": 3,
      "processing_time": 10.5
    }
  }
}
```

### Data Events (중간 결과)
```json
{
  "type": "data",
  "data": {
    "stage": "generate_insights",
    "partial_result": {
      "title": "HBM3 경쟁력",
      "finding": "SK하이닉스 선도..."
    }
  }
}
```

### Final Event (최종 결과)
```json
{
  "type": "final",
  "data": {
    "markdown": "# 분석 보고서...",
    "quality_score": 0.92,
    "processing_time": 65.3,
    "insights_count": 5,
    "relationships_count": 4
  }
}
```

### Error Event
```json
{
  "type": "error",
  "data": {
    "stage": "deep_reasoning",
    "error": "LLM timeout",
    "message": "심화 추론 단계에서 오류 발생"
  }
}
```

## LangGraph 스트리밍 통합

### astream_events() 사용
```python
async for event in workflow.astream_events(initial_state):
    if event["event"] == "on_chain_start":
        # 노드 시작
        yield {"type": "step", "data": {"node": event["name"], "status": "started"}}

    elif event["event"] == "on_chain_end":
        # 노드 완료
        yield {"type": "step", "data": {"node": event["name"], "status": "completed"}}

    elif event["event"] == "on_llm_stream":
        # LLM 스트리밍 (선택적)
        yield {"type": "llm_chunk", "data": {"text": event["data"]["chunk"]}}
```

### 진행률 계산
```python
WORKFLOW_STAGES = {
    "analyze_query": 0.10,
    "plan_analysis": 0.15,
    "collect_parallel_data": 0.20,
    "cross_validate_contexts": 0.25,
    "generate_insights": 0.40,
    "analyze_relationships": 0.55,
    "deep_reasoning": 0.70,
    "synthesize_report": 0.85,
    "quality_check": 0.95,
    "enhance_report": 1.00
}
```

## FastAPI 구현

### Streaming Endpoint
```python
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        start_time = time.time()

        try:
            # LangGraph 스트리밍 실행
            async for event in langgraph_engine.stream_report(request.query):
                # SSE 형식으로 전송
                yield f"data: {json.dumps(event)}\n\n"

                # Keep-alive
                await asyncio.sleep(0)

        except Exception as e:
            error_event = {
                "type": "error",
                "data": {"error": str(e)}
            }
            yield f"data: {json.dumps(error_event)}\n\n"

        finally:
            # Done 이벤트
            done_event = {
                "type": "done",
                "data": {"total_time": time.time() - start_time}
            }
            yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginx buffering 비활성화
        }
    )
```

## LangGraphReportEngine 확장

### stream_report() 메서드 추가
```python
async def stream_report(
    self,
    query: str,
    analysis_depth: str = "standard"
) -> AsyncIterator[Dict[str, Any]]:
    """스트리밍 보고서 생성"""

    start_time = time.time()

    # 초기 상태
    initial_state = self._initialize_state(query, analysis_depth)

    # 진행률 추적
    current_progress = 0.0

    try:
        # LangGraph astream_events 사용
        async for event in self.workflow.astream_events(
            initial_state,
            version="v1"
        ):
            event_type = event.get("event")
            event_name = event.get("name", "")

            # 노드 시작
            if event_type == "on_chain_start":
                if event_name in WORKFLOW_STAGES:
                    current_progress = WORKFLOW_STAGES[event_name]
                    yield {
                        "type": "progress",
                        "data": {
                            "stage": event_name,
                            "status": "started",
                            "progress": current_progress,
                            "elapsed_time": time.time() - start_time
                        }
                    }

            # 노드 완료
            elif event_type == "on_chain_end":
                if event_name in WORKFLOW_STAGES:
                    output = event.get("data", {}).get("output", {})

                    # 부분 결과 전송
                    if "insights" in output:
                        yield {
                            "type": "data",
                            "data": {
                                "stage": event_name,
                                "insights_count": len(output["insights"])
                            }
                        }

                    yield {
                        "type": "step",
                        "data": {
                            "node": event_name,
                            "status": "completed"
                        }
                    }

        # 최종 상태 조회
        final_state = await self.workflow.ainvoke(initial_state)

        # 최종 결과 전송
        yield {
            "type": "final",
            "data": {
                "markdown": final_state.get("final_report", ""),
                "quality_score": final_state.get("quality_score", 0),
                "processing_time": time.time() - start_time,
                "insights_count": len(final_state.get("insights", [])),
                "relationships_count": len(final_state.get("relationships", []))
            }
        }

    except Exception as e:
        yield {
            "type": "error",
            "data": {
                "error": str(e),
                "stage": "unknown"
            }
        }
```

## 클라이언트 사용 예시

### JavaScript (EventSource)
```javascript
const eventSource = new EventSource('/mcp/chat/stream?query=삼성전자 분석');

eventSource.addEventListener('message', (e) => {
    const event = JSON.parse(e.data);

    switch(event.type) {
        case 'progress':
            updateProgressBar(event.data.progress);
            updateStatus(event.data.message);
            break;

        case 'step':
            console.log(`Step ${event.data.node}: ${event.data.status}`);
            break;

        case 'data':
            displayPartialResult(event.data);
            break;

        case 'final':
            displayFinalReport(event.data.markdown);
            eventSource.close();
            break;

        case 'error':
            showError(event.data.error);
            eventSource.close();
            break;
    }
});
```

### Python (httpx)
```python
import httpx
import json

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://localhost:8000/mcp/chat/stream",
        json={"query": "삼성전자 분석"}
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])

                if event["type"] == "progress":
                    print(f"Progress: {event['data']['progress']:.0%}")

                elif event["type"] == "final":
                    print(f"Final report: {event['data']['markdown'][:100]}...")
```

### cURL 테스트
```bash
curl -N -X POST http://localhost:8000/mcp/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query":"삼성전자 분석"}'
```

## 성능 고려사항

### 1. 이벤트 빈도 제한
- 너무 많은 이벤트는 네트워크 부담
- 주요 단계만 전송 (10단계)
- LLM 스트리밍은 선택적

### 2. 버퍼링 비활성화
```python
headers={
    "X-Accel-Buffering": "no",  # Nginx
    "Cache-Control": "no-cache"
}
```

### 3. Keep-Alive
- 30-60초마다 heartbeat 전송
- 연결 유지 확인

### 4. 타임아웃
- 클라이언트 타임아웃: 5분
- 서버 타임아웃: 2분 (comprehensive)

## 보안 고려사항

### 1. 인증
- 기존 인증 미들웨어 적용
- SSE는 쿠키 기반 인증 지원

### 2. Rate Limiting
- 동시 스트리밍 연결 제한
- IP당 최대 3개 연결

### 3. 리소스 관리
- 스트리밍 연결 타임아웃
- 메모리 누수 방지

## 모니터링

### 메트릭
- 활성 스트리밍 연결 수
- 평균 스트리밍 시간
- 단계별 처리 시간
- 오류율

### 로깅
```python
logger.info(f"[Streaming] Started: query={query}, user={user_id}")
logger.info(f"[Streaming] Progress: stage={stage}, elapsed={elapsed}s")
logger.info(f"[Streaming] Completed: total_time={total_time}s")
```

## 점진적 롤아웃

### Phase 1: 기본 스트리밍
- [ ] progress 이벤트
- [ ] step 이벤트
- [ ] final 이벤트
- [ ] error 처리

### Phase 2: 부분 결과
- [ ] data 이벤트 (insights, relationships)
- [ ] 중간 결과 표시

### Phase 3: 고급 기능
- [ ] LLM 스트리밍 (token-by-token)
- [ ] 실시간 Markdown 렌더링
- [ ] 취소 기능

## 테스트 계획

### 단위 테스트
- stream_report() 메서드
- 이벤트 생성기
- 오류 처리

### 통합 테스트
- E2E 스트리밍 테스트
- 타임아웃 시나리오
- 동시 연결 테스트

### 부하 테스트
- 100개 동시 스트리밍
- 메모리 사용량
- CPU 사용률
