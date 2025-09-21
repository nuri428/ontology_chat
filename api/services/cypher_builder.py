# src/ontology_chat/services/cypher_builder.py
from typing import Dict, List

def build_label_aware_search_cypher(keys_map: Dict[str, List[str]]) -> str:
    """
    라벨별 키 배열을 받아 안전한 검색 쿼리 생성.
    - 동적 속성 접근: n[k]
    - CALL () { ... UNION ... } 사용 (5.x 권장)
    - 각 분기 WITH $q 재선언
    """
    if not keys_map:
        # 최소 fallback (Company/News만)
        keys_map = {
            "Company": ["name"],
            "News": ["title", "content"]
        }

    blocks = []
    for label, keys in keys_map.items():
        alias = "n"
        # 라벨마다 다른 별칭 부여(가독성), 반환 시 AS n으로 통일
        if label.lower() == "company": alias = "c"
        elif label.lower() == "news": alias = "nw"
        elif label.lower() == "event": alias = "e"
        elif label.lower() == "product": alias = "pr"
        elif label.lower() == "weaponsystem": alias = "pr"  # 이전 호환성 유지
        elif label.lower() == "contract": alias = "ct"
        elif label.lower() == "program": alias = "p"
        elif label.lower() == "agency": alias = "ag"
        elif label.lower() == "country": alias = "co"

        # 키 배열을 Cypher 리스트로 직렬화
        # 예: ['title','content'] → '["title","content"]'
        keys_list = "[" + ",".join(f'"{k}"' for k in keys) + "]"

        block = f"""
  WITH $q AS q
  MATCH ({alias}:{label})
  WITH {alias}, q, {keys_list} AS keys
  WHERE ANY(k IN keys WHERE {alias}[k] IS NOT NULL AND toLower(toString({alias}[k])) CONTAINS toLower(q))
  RETURN {alias} AS n, labels({alias}) AS labels
""".rstrip()
        blocks.append(block)

    unioned = "\n  UNION\n".join(blocks)

    return f"""
CALL () {{
{unioned}
}}
RETURN n, labels
LIMIT $limit
""".strip()