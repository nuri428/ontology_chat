#!/bin/bash
# 캐시 관리 API 테스트 스크립트

API_URL="http://localhost:8000/api/cache"

echo "📊 캐시 통계 조회"
curl -X GET "$API_URL/stats" | jq .

echo -e "\n🔥 인기 쿼리 TOP 10"
curl -X GET "$API_URL/hot-queries?top_n=10" | jq .

echo -e "\n🗑️ 전체 캐시 초기화"
curl -X POST "$API_URL/clear" | jq .

echo -e "\n🔍 특정 패턴 무효화 (SMR 관련)"
curl -X POST "$API_URL/invalidate" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "SMR"}' | jq .

echo -e "\n🧹 만료된 캐시 정리"
curl -X POST "$API_URL/cleanup" | jq .