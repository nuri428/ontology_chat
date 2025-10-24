#!/bin/bash

echo "=========================================================================="
echo "최종 성능 테스트 - 최적화 후"
echo "=========================================================================="
echo ""

# 결과 저장
RESULTS_FILE="/tmp/final_test_results_$(date +%Y%m%d_%H%M%S).txt"

echo "결과 파일: $RESULTS_FILE" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# 테스트 함수
test_query() {
    local name="$1"
    local query="$2"
    local force_deep="${3:-false}"
    local timeout="${4:-10}"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$RESULTS_FILE"
    echo "테스트: $name" | tee -a "$RESULTS_FILE"
    echo "질의: $query" | tee -a "$RESULTS_FILE"
    echo "강제 심층 분석: $force_deep" | tee -a "$RESULTS_FILE"
    echo "타임아웃: ${timeout}초" | tee -a "$RESULTS_FILE"
    echo "" | tee -a "$RESULTS_FILE"

    START_TIME=$(date +%s.%N)

    timeout $timeout curl -s -X POST http://localhost:8000/chat \
        -H "Content-Type: application/json" \
        -d "{\"query\":\"$query\",\"force_deep_analysis\":$force_deep}" \
        > /tmp/test_response.json 2>&1

    EXIT_CODE=$?
    END_TIME=$(date +%s.%N)
    ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)

    if [ $EXIT_CODE -eq 124 ]; then
        echo "❌ 타임아웃 (${timeout}초)" | tee -a "$RESULTS_FILE"
        echo "" | tee -a "$RESULTS_FILE"
        return 1
    elif [ $EXIT_CODE -ne 0 ]; then
        echo "❌ 오류 (종료 코드: $EXIT_CODE)" | tee -a "$RESULTS_FILE"
        echo "" | tee -a "$RESULTS_FILE"
        return 1
    else
        # 응답 분석
        python3 -c "
import json, sys
try:
    with open('/tmp/test_response.json') as f:
        data = json.load(f)

    meta = data.get('meta', {})
    intent = meta.get('intent', 'unknown')
    confidence = meta.get('confidence', 0)
    proc_time = meta.get('processing_time_ms', 0)
    response_type = data.get('type', 'unknown')
    response_len = len(data.get('markdown', ''))
    langgraph_timeout = meta.get('langgraph_timeout', False)

    print(f'✅ 성공')
    print(f'   - 전체 시간: ${ELAPSED}초')
    print(f'   - 처리 시간: {proc_time:.1f}ms')
    print(f'   - 의도: {intent} (신뢰도: {confidence:.2f})')
    print(f'   - 응답 타입: {response_type}')
    print(f'   - 응답 길이: {response_len}자')

    if langgraph_timeout:
        print(f'   ⚠️  LangGraph 타임아웃으로 빠른 핸들러 사용')

    # 성능 평가
    elapsed_float = float('$ELAPSED')
    if elapsed_float < 1.0:
        grade = 'A+ (매우 빠름)'
    elif elapsed_float < 2.0:
        grade = 'A (빠름)'
    elif elapsed_float < 5.0:
        grade = 'B (보통)'
    elif elapsed_float < 10.0:
        grade = 'C (느림)'
    else:
        grade = 'D (매우 느림)'

    print(f'   📊 성능 등급: {grade}')

except Exception as e:
    print(f'❌ 응답 파싱 실패: {e}')
    with open('/tmp/test_response.json') as f:
        print(f.read()[:200])
" | tee -a "$RESULTS_FILE"

        echo "" | tee -a "$RESULTS_FILE"
        return 0
    fi
}

# 테스트 실행
echo "=========================================================================="
echo "1. 단순 질의 테스트 (빠른 핸들러)"
echo "=========================================================================="
echo ""

test_query "단순 뉴스 조회" "삼성전자 뉴스" false 5
test_query "단순 주가 조회" "현대차 주가" false 5
test_query "키워드 검색" "AI 반도체" false 5

echo ""
echo "=========================================================================="
echo "2. 중간 복잡도 질의 (빠른 핸들러로 처리되어야 함)"
echo "=========================================================================="
echo ""

test_query "트렌드 질의" "AI 반도체 시장 트렌드" false 10
test_query "비교 질의 (복잡도 낮음)" "삼성전자 SK하이닉스" false 10
test_query "분석 요청" "삼성전자 실적 분석" false 10

echo ""
echo "=========================================================================="
echo "3. 복잡한 질의 (LangGraph 또는 타임아웃 후 폴백)"
echo "=========================================================================="
echo ""

test_query "명시적 비교" "삼성전자와 SK하이닉스 HBM 경쟁력 비교" false 20
test_query "강제 심층 분석" "삼성전자 뉴스" true 20

echo ""
echo "=========================================================================="
echo "📊 최종 요약"
echo "=========================================================================="
echo ""

# 성공/실패 카운트
TOTAL=$(grep -c "^테스트:" "$RESULTS_FILE")
SUCCESS=$(grep -c "^✅ 성공" "$RESULTS_FILE")
FAILED=$((TOTAL - SUCCESS))

echo "총 테스트: $TOTAL"
echo "성공: $SUCCESS"
echo "실패: $FAILED"
echo "성공률: $(echo "scale=1; $SUCCESS * 100 / $TOTAL" | bc)%"

echo ""
echo "결과 상세 내용: $RESULTS_FILE"
echo ""
echo "=========================================================================="
echo "완료"
echo "=========================================================================="
