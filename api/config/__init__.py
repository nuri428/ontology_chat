# Configuration package
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Dict, List
import json
from pathlib import Path

class Settings(BaseSettings):
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    openai_api_key: str | None = None

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_password"
    neo4j_database: str = "neo4j"

    opensearch_host: str = "http://localhost:9200"
    opensearch_user: str = "admin"
    opensearch_password: str = "admin"
    news_bulk_index: str = "news_article_bulk"
    news_embedding_index: str = "news_article_embedding"

    stock_api_key: str | None = None
    
    # Ollama LLM 설정
    ollama_host: str = "localhost"
    ollama_model: str = "llama3.1:8b"

    # BGE-M3 임베딩 설정 (원격 서버)
    bge_m3_host: str = "192.168.0.10"
    bge_m3_model: str = "bge-m3:latest"
    enable_hybrid_search: bool = True

    # Langfuse 트레이싱 설정
    langfuse_secret_key: str | None = None
    langfuse_public_key: str | None = None
    langfuse_host: str | None = None
    
    neo4j_search_cypher: Optional[str] = None    
    graph_search_keys: Optional[str] = None  # JSON 문자열
    
    neo4j_search_cypher_file: str | None = "api/config/graph_search.cypher"
    neo4j_search_lookback_days: int = 180
    neo4j_search_default_domain: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    def resolve_search_cypher(self) -> Optional[str]:
        if self.neo4j_search_cypher_file:
            p = Path(self.neo4j_search_cypher_file)
            if not p.is_absolute():
                # project_root 추정 (api/config/__init__.py 기준으로 두 단계 위)
                project_root = Path(__file__).resolve().parents[2]
                p = project_root / p
            if p.exists():
                return p.read_text(encoding="utf-8")
        return None

    def get_graph_search_defaults(self) -> dict:
        return {
            "domain": self.neo4j_search_default_domain,
            "lookback_days": self.neo4j_search_lookback_days,
        }
    
    def get_ollama_base_url(self) -> str:
        """Ollama 서버 URL 생성"""
        if "://" in self.ollama_host:
            return f"{self.ollama_host}:11434" if ":11434" not in self.ollama_host else self.ollama_host
        else:
            return f"http://{self.ollama_host}:11434"

    def get_bge_m3_base_url(self) -> str:
        """BGE-M3 Ollama 서버 URL 생성"""
        if "://" in self.bge_m3_host:
            return f"{self.bge_m3_host}:11434" if ":11434" not in self.bge_m3_host else self.bge_m3_host
        else:
            return f"http://{self.bge_m3_host}:11434"

    def get_graph_search_keys(self) -> Dict[str, List[str]]:
        """
        GRAPH_SEARCH_KEYS JSON 파싱. 없으면 빈 dict
        """
        if not self.graph_search_keys:
            return {}
        try:
            data = json.loads(self.graph_search_keys)
            # 값이 리스트가 아닌 항목 제거/보정
            return {
                label: [str(k) for k in keys] 
                for label, keys in data.items() if isinstance(keys, list)
            }
        except Exception:
            return {}

settings = Settings()  # singleton-like