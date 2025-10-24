#!/bin/bash

echo "===== Testing Query Routing and Performance ====="
echo ""

echo "1. Simple Query (should be fast ~200ms):"
time curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"삼성전자 뉴스"}' | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"✓ Intent: {d['meta']['intent']}, Time: {d['meta']['processing_time_ms']:.1f}ms\")" || echo "✗ Failed"

echo ""
echo "2. Moderate Query (should be fast ~200ms):"
timeout 10 curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"AI 반도체 시장"}' | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"✓ Intent: {d['meta']['intent']}, Time: {d['meta']['processing_time_ms']:.1f}ms\")" || echo "✗ Failed or timeout"

echo ""
echo "3. Complex Query WITHOUT force_deep (testing complexity detection):"
echo "   Query: '삼성전자와 SK하이닉스 비교'"
echo "   Timeout: 15 seconds"
timeout 15 curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"삼성전자와 SK하이닉스 비교"}' > /tmp/complex_test.json 2>&1

if [ $? -eq 124 ]; then
  echo "✗ TIMEOUT (15s) - This is the problem!"
  echo "   → LangGraph is being triggered and taking too long"
else
  python3 -c "import sys, json; d=json.load(open('/tmp/complex_test.json')); print(f\"✓ Intent: {d['meta']['intent']}, Time: {d['meta']['processing_time_ms']:.1f}ms, Type: {d.get('type', 'unknown')}\")" 2>&1 || cat /tmp/complex_test.json
fi

echo ""
echo "4. Forced Simple Handler (bypassing LangGraph):"
echo "   Same query but analyzing what fast handler would return"
timeout 5 curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"삼성전자 뉴스 SK하이닉스 뉴스"}' | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"✓ Intent: {d['meta']['intent']}, Time: {d['meta']['processing_time_ms']:.1f}ms\")" || echo "✗ Failed"

echo ""
echo "===== Analysis ====="
echo "If test 3 times out, the issue is:"
echo "1. Complexity scoring is triggering LangGraph for comparison queries"
echo "2. LangGraph workflow is taking more than 15 seconds"
echo "3. Need to either:"
echo "   - Optimize LangGraph workflow (identify bottleneck agents)"
echo "   - Adjust complexity threshold to avoid triggering for simple comparisons"
echo "   - Add timeout handling in LangGraph execution"
