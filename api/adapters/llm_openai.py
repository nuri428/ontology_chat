from __future__ import annotations
from typing import List, Dict
import os
from api.logging import setup_logging
logger = setup_logging()

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None  # 선택적 의존

class LLMClient:
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.enabled = bool(self.api_key and AsyncOpenAI is not None)
        self._client = AsyncOpenAI(api_key=self.api_key) if self.enabled else None

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.enabled:
            logger.warning("[LLM] disabled (no key or package)")
            return ""
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()