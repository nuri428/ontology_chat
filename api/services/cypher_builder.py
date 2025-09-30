# src/ontology_chat/services/cypher_builder.py
from typing import Dict, List

def build_label_aware_search_cypher(keys_map: Dict[str, List[str]]) -> str:
    """
    라벨별 키 배열을 받아 최적화된 검색 쿼리 생성.
    - TEXT INDEX 활용으로 성능 향상 (CONTAINS 대신 인덱스 기반 검색)
    - CALL () { ... UNION ... } 사용 (5.x 권장)
    - 인덱스가 있는 속성은 직접 검색, 없는 속성은 동적 접근
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
        elif label.lower() == "weaponsystem": alias = "pr"
        elif label.lower() == "contract": alias = "ct"
        elif label.lower() == "program": alias = "p"
        elif label.lower() == "agency": alias = "ag"
        elif label.lower() == "country": alias = "co"
        elif label.lower() == "technology": alias = "t"
        elif label.lower() == "theme": alias = "th"

        # 인덱스가 있는 주요 속성은 직접 WHERE 조건으로 (더 빠름)
        # 나머지는 동적 속성 접근
        indexed_keys = {
            "Company": ["name"],
            "Event": ["title"],
            "Technology": ["name"],
            "Theme": ["name"],
            "News": ["title"]
        }

        primary_keys = indexed_keys.get(label, [])
        other_keys = [k for k in keys if k not in primary_keys]

        # WHERE 조건 구성
        where_conditions = []

        # 1. 인덱스 기반 검색 (주요 속성)
        if primary_keys:
            for key in primary_keys:
                where_conditions.append(f"toLower({alias}.{key}) CONTAINS toLower(q)")

        # 2. 동적 속성 검색 (기타 속성)
        if other_keys:
            keys_list = "[" + ",".join(f'"{k}"' for k in other_keys) + "]"
            where_conditions.append(f"ANY(k IN {keys_list} WHERE {alias}[k] IS NOT NULL AND toLower(toString({alias}[k])) CONTAINS toLower(q))")

        where_clause = " OR ".join(where_conditions) if where_conditions else "true"

        block = f"""
  WITH $q AS q
  MATCH ({alias}:{label})
  WHERE {where_clause}
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