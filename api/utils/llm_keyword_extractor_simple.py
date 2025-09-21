"""
간단한 LLM 기반 키워드 추출기
pydantic 버전 충돌 문제를 피해 직접 구현
"""
import json
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

try:
    from langchain_ollama import OllamaLLM
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from api.logging import setup_logging
logger = setup_logging()

@dataclass
class LLMKeywordResult:
    """LLM 키워드 추출 결과"""
    keywords: List[str]
    weighted_keywords: Dict[str, float]
    categories: Dict[str, List[str]]
    confidence: float
    reasoning: str

class SimpleLLMKeywordExtractor:
    """간단한 langchain-ollama 키워드 추출기 (환경변수 기반)"""
    
    def __init__(
        self, 
        model: str = None,
        base_url: str = None,
        temperature: float = 0.1
    ):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("langchain-ollama is not available")
        
        # 환경변수에서 설정 읽기
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        import importlib.util
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
        spec = importlib.util.spec_from_file_location("config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        settings = config_module.settings
        
        self.model = model or settings.ollama_model
        self.base_url = base_url or settings.get_ollama_base_url()
        self.temperature = temperature
        
        logger.info(f"Ollama LLM 초기화: {self.model} @ {self.base_url}")
        
        # Ollama LLM 초기화
        self.llm = OllamaLLM(
            model=self.model,
            base_url=self.base_url,
            temperature=self.temperature,
            num_predict=1000
        )

    def create_keyword_prompt(self, query: str, domain_hints: List[str] = None) -> str:
        """키워드 추출 프롬프트 생성"""
        
        domain_context = ""
        if domain_hints:
            domain_context = f"**도메인 컨텍스트:** 다음 도메인들을 특히 고려하세요: {', '.join(domain_hints)}"

        prompt = f"""Extract Korean keywords from query. Return ONLY JSON format.

Query: "{query}"
{domain_context}

Extract search keywords including companies, technology terms, finance terms, industry terms.

Return JSON only:
{{"keywords":["기업명","기술","수출","산업","종목"],"weighted_keywords":{{"기업명":2.5,"기술":2.8,"수출":2.0,"산업":2.3,"종목":2.1}},"categories":{{"companies":["기업명"],"technology":["기술","혁신"],"finance":["종목","투자"],"industry":["산업","제조"]}},"confidence":0.9,"reasoning":"키워드 추출 완료"}}"""
        
        return prompt

    async def extract_keywords_async(self, query: str, domain_hints: List[str] = None) -> LLMKeywordResult:
        """비동기 키워드 추출"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.extract_keywords, query, domain_hints)

    def extract_keywords(self, query: str, domain_hints: List[str] = None) -> LLMKeywordResult:
        """동기 키워드 추출"""
        try:
            # 프롬프트 생성
            prompt = self.create_keyword_prompt(query, domain_hints)
            
            logger.info(f"LLM 키워드 추출 시작: {query[:50]}...")
            
            # LLM 호출
            response = self.llm.invoke(prompt)
            
            logger.debug(f"LLM 응답: {response[:200]}...")
            
            # JSON 파싱
            parsed_result = self._parse_llm_response(response)
            
            if parsed_result:
                logger.info(f"LLM 키워드 추출 성공: {len(parsed_result.keywords)}개 키워드")
                return parsed_result
            else:
                # 파싱 실패 시 폴백
                logger.warning("LLM JSON 파싱 실패, 폴백 사용")
                return self._fallback_extraction(query, response)
                
        except Exception as e:
            logger.error(f"LLM 키워드 추출 실패: {e}")
            return self._simple_fallback(query, str(e))

    def _parse_llm_response(self, response: str) -> Optional[LLMKeywordResult]:
        """LLM 응답 JSON 파싱"""
        try:
            # JSON 추출 (마크다운 코드 블록 처리)
            json_str = self._extract_json_from_response(response)
            parsed = json.loads(json_str)
            
            # 유효성 검증
            if not isinstance(parsed.get("keywords"), list):
                return None
                
            return LLMKeywordResult(
                keywords=parsed.get("keywords", [])[:15],
                weighted_keywords=parsed.get("weighted_keywords", {}),
                categories=parsed.get("categories", {}),
                confidence=min(max(parsed.get("confidence", 0.5), 0.0), 1.0),
                reasoning=parsed.get("reasoning", "")
            )
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"JSON 파싱 오류: {e}")
            return None

    def _extract_json_from_response(self, response: str) -> str:
        """응답에서 JSON 부분만 추출"""
        response = response.strip()
        
        # 마크다운 코드 블록 제거
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        # JSON 객체 찾기 (중괄호 기준)
        start = response.find("{")
        if start >= 0:
            brace_count = 0
            for i, char in enumerate(response[start:], start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return response[start:i+1]
        
        return response

    def _fallback_extraction(self, query: str, llm_response: str) -> LLMKeywordResult:
        """LLM 응답에서 키워드 추출 (JSON 파싱 실패 시)"""
        import re
        
        # 응답에서 한글/영문 키워드 추출
        keywords = re.findall(r'[가-힣a-zA-Z]+', llm_response)
        
        # 불용어 제거
        stopwords = {'json', 'keywords', 'categories', 'confidence', 'reasoning', 'response'}
        meaningful_keywords = []
        
        for word in keywords:
            if (len(word) >= 2 and 
                word.lower() not in stopwords and
                not word.isdigit()):
                meaningful_keywords.append(word)
        
        # 중복 제거 및 상위 선택
        unique_keywords = list(dict.fromkeys(meaningful_keywords))[:12]
        
        return LLMKeywordResult(
            keywords=unique_keywords,
            weighted_keywords={k: 1.0 for k in unique_keywords},
            categories={},
            confidence=0.4,
            reasoning="JSON parsing failed, extracted from LLM text response"
        )

    def _simple_fallback(self, query: str, error: str) -> LLMKeywordResult:
        """완전 폴백 키워드 추출"""
        import re
        
        # 불용어
        stopwords = {'은', '는', '이', '가', '을', '를', '의', '에', '와', '과', '도', '만', '관련', '어떤', '어떻게'}
        
        # 한글 단어 추출
        words = re.findall(r'[가-힣]+', query)
        keywords = [w for w in words if len(w) >= 2 and w not in stopwords]
        
        # 영문 단어도 추출
        english_words = re.findall(r'[a-zA-Z]+', query)
        keywords.extend([w for w in english_words if len(w) >= 2])
        
        return LLMKeywordResult(
            keywords=keywords[:10],
            weighted_keywords={k: 0.8 for k in keywords[:10]},
            categories={},
            confidence=0.2,
            reasoning=f"LLM extraction completely failed: {error}"
        )

    async def health_check(self) -> bool:
        """Ollama 서버 상태 확인"""
        try:
            # 간단한 테스트 쿼리
            result = await self.extract_keywords_async("테스트", [])
            return len(result.keywords) > 0
        except:
            return False

# 기본 인스턴스
simple_llm_extractor = SimpleLLMKeywordExtractor()