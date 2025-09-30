#!/bin/bash
for query in "삼성전자" "LG에너지솔루션" "SK하이닉스"; do
  echo "===== 질문: $query ====="
  curl -s -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"query\":\"$query\"}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
meta = data.get('meta', {})
print(f'Graph: {meta.get(\"graph_samples_shown\", 0)}건, News: {len(data.get(\"sources\", []))}건, Time: {meta.get(\"total_latency_ms\", 0):.0f}ms')
"
  echo
done