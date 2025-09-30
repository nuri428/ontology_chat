#!/bin/bash

queries=(
  "현대차 전기차"
  "AI 반도체"
  "2차전지"
  "네이버"
  "카카오"
  "테슬라"
  "반도체 장비"
)

for query in "${queries[@]}"; do
  echo "========================================="
  echo "질의: $query"
  echo "========================================="

  result=$(curl -s -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"$query\"}")

  echo "$result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
meta = data.get('meta', {})
graph_samples = data.get('graph_samples', [])
sources = data.get('sources', [])

print(f'📊 결과 요약:')
print(f'  - Graph Samples: {meta.get(\"graph_samples_shown\", 0)}건')
print(f'  - News Sources: {len(sources)}건')
print(f'  - Total Time: {meta.get(\"total_latency_ms\", 0):.0f}ms')
print(f'  - Neo4j Latency: {meta.get(\"latency_ms\", {}).get(\"neo4j\", 0):.0f}ms')

if graph_samples:
    print(f'\n🔍 그래프 샘플 (상위 3개):')
    for i, sample in enumerate(graph_samples[:3], 1):
        n = sample.get('n', {})
        labels = sample.get('labels', [])
        name = n.get('name') or n.get('title') or n.get('label', 'N/A')
        label = labels[0] if labels else '?'
        print(f'  {i}. [{label}] {name[:50]}')

if sources:
    print(f'\n📰 뉴스 샘플 (상위 2개):')
    for i, src in enumerate(sources[:2], 1):
        title = src.get('title', 'N/A')
        print(f'  {i}. {title[:60]}')
"
  echo
  echo
done