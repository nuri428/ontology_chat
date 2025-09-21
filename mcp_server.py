#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server for Ontology Chat API
외부에서 ontology_chat의 기능을 MCP를 통해 사용할 수 있도록 제공
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from mcp import Server, Tool
from mcp.server import stdio
from mcp.types import TextContent, ToolResult, ToolCall

# API 서비스들 import
from api.services.chat_service import ChatService
from api.services.report_service import ReportService, ReportRequest
from api.services.langgraph_report_service import LangGraphReportEngine
from api.services.stock_data_service import stock_data_service
from api.logging import setup_logging

# 로거 설정
logger = setup_logging()

# MCP 서버 인스턴스
server = Server("ontology-chat")

# 서비스 인스턴스들
chat_service = ChatService()
report_service = ReportService()
langgraph_engine = LangGraphReportEngine()


@server.list_tools()
async def list_tools() -> List[Tool]:
    """사용 가능한 도구 목록 반환"""
    return [
        Tool(
            name="chat",
            description="온톨로지 기반 챗봇 대화 - 질문에 대한 답변 생성",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "사용자 질문"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="generate_report",
            description="도메인별 분석 리포트 생성",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "분석할 질의"
                    },
                    "domain": {
                        "type": "string",
                        "description": "도메인 (optional)"
                    },
                    "lookback_days": {
                        "type": "integer",
                        "description": "분석 기간 (일)",
                        "default": 180
                    },
                    "news_size": {
                        "type": "integer",
                        "description": "뉴스 검색 수",
                        "default": 20
                    },
                    "graph_limit": {
                        "type": "integer",
                        "description": "그래프 검색 수",
                        "default": 30
                    },
                    "symbol": {
                        "type": "string",
                        "description": "종목 심볼 (optional)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="generate_comparative_report",
            description="여러 키워드에 대한 비교 분석 리포트 생성",
            inputSchema={
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "비교할 질의들 (2-5개)",
                        "minItems": 2,
                        "maxItems": 5
                    },
                    "domain": {
                        "type": "string",
                        "description": "도메인 (optional)"
                    },
                    "lookback_days": {
                        "type": "integer",
                        "description": "분석 기간 (일)",
                        "default": 180
                    }
                },
                "required": ["queries"]
            }
        ),
        Tool(
            name="generate_trend_report",
            description="시계열 트렌드 분석 리포트 생성",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "분석할 질의"
                    },
                    "domain": {
                        "type": "string",
                        "description": "도메인 (optional)"
                    },
                    "periods": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "분석 기간들 (예: [30, 90, 180])",
                        "default": [30, 90, 180]
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="generate_langgraph_report",
            description="LangGraph 기반 고급 컨텍스트 엔지니어링 리포트 생성",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "분석할 질의"
                    },
                    "domain": {
                        "type": "string",
                        "description": "도메인 (optional)"
                    },
                    "lookback_days": {
                        "type": "integer",
                        "description": "분석 기간 (일)",
                        "default": 180
                    },
                    "analysis_depth": {
                        "type": "string",
                        "enum": ["shallow", "standard", "deep", "comprehensive"],
                        "description": "분석 깊이",
                        "default": "standard"
                    },
                    "symbol": {
                        "type": "string",
                        "description": "종목 심볼 (optional)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_stocks",
            description="종목 검색",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색어"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "결과 수 제한",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_market_themes",
            description="시장 주요 테마 목록 조회",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_theme_stocks",
            description="특정 테마의 관련 종목 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "theme": {
                        "type": "string",
                        "description": "테마명"
                    }
                },
                "required": ["theme"]
            }
        ),
        Tool(
            name="get_top_stocks",
            description="상승률 기준 상위 종목 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "theme": {
                        "type": "string",
                        "description": "테마명 (optional)"
                    }
                }
            }
        ),
        Tool(
            name="generate_forecast_report",
            description="테마/종목별 전망 리포트 생성",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "분석 질의"
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "키워드 목록"
                    },
                    "companies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "관련 기업 목록"
                    },
                    "lookback_days": {
                        "type": "integer",
                        "description": "분석 기간",
                        "default": 30
                    },
                    "include_news": {
                        "type": "boolean",
                        "description": "뉴스 포함 여부",
                        "default": True
                    },
                    "include_ontology": {
                        "type": "boolean",
                        "description": "온톨로지 포함 여부",
                        "default": True
                    },
                    "include_financial": {
                        "type": "boolean",
                        "description": "재무 정보 포함 여부",
                        "default": True
                    },
                    "report_mode": {
                        "type": "string",
                        "description": "리포트 모드",
                        "default": "테마별 분석"
                    }
                },
                "required": ["query", "keywords", "companies"]
            }
        )
    ]


@server.call_tool()
async def call_tool(tool_call: ToolCall) -> List[ToolResult]:
    """도구 실행"""
    try:
        tool_name = tool_call.name
        arguments = tool_call.arguments or {}

        logger.info(f"MCP 도구 호출: {tool_name} with args: {arguments}")

        # 챗봇 대화
        if tool_name == "chat":
            result = await chat_service.generate_answer(arguments["query"])
            return [ToolResult(
                toolCallId=tool_call.id,
                content=[TextContent(text=json.dumps(result, ensure_ascii=False))]
            )]

        # 기본 리포트 생성
        elif tool_name == "generate_report":
            report = await report_service.generate_report(
                query=arguments["query"],
                domain=arguments.get("domain"),
                lookback_days=arguments.get("lookback_days", 180),
                news_size=arguments.get("news_size", 20),
                graph_limit=arguments.get("graph_limit", 30),
                symbol=arguments.get("symbol")
            )
            return [ToolResult(
                toolCallId=tool_call.id,
                content=[TextContent(text=json.dumps({
                    "markdown": report["markdown"],
                    "metrics": report["metrics"]
                }, ensure_ascii=False))]
            )]

        # 비교 분석 리포트
        elif tool_name == "generate_comparative_report":
            result = await report_service.generate_comparative_report(
                queries=arguments["queries"],
                domain=arguments.get("domain"),
                lookback_days=arguments.get("lookback_days", 180)
            )
            return [ToolResult(
                toolCallId=tool_call.id,
                content=[TextContent(text=json.dumps(result, ensure_ascii=False))]
            )]

        # 트렌드 분석 리포트
        elif tool_name == "generate_trend_report":
            result = await report_service.generate_trend_analysis(
                query=arguments["query"],
                domain=arguments.get("domain"),
                periods=arguments.get("periods", [30, 90, 180])
            )
            return [ToolResult(
                toolCallId=tool_call.id,
                content=[TextContent(text=json.dumps(result, ensure_ascii=False))]
            )]

        # LangGraph 리포트
        elif tool_name == "generate_langgraph_report":
            result = await langgraph_engine.generate_langgraph_report(
                query=arguments["query"],
                domain=arguments.get("domain"),
                lookback_days=arguments.get("lookback_days", 180),
                analysis_depth=arguments.get("analysis_depth", "standard"),
                symbol=arguments.get("symbol")
            )
            return [ToolResult(
                toolCallId=tool_call.id,
                content=[TextContent(text=json.dumps(result, ensure_ascii=False))]
            )]

        # 종목 검색
        elif tool_name == "search_stocks":
            stocks = await stock_data_service.search_stocks_by_query(
                arguments["query"],
                arguments.get("limit", 10)
            )
            result = [
                {
                    "name": stock.name,
                    "symbol": stock.symbol.replace('.KS', ''),
                    "sector": stock.sector,
                    "industry": stock.industry,
                    "price": stock.price,
                    "change_percent": stock.change_percent,
                    "market_cap": stock.market_cap,
                    "volume": stock.volume
                }
                for stock in stocks
            ]
            return [ToolResult(
                toolCallId=tool_call.id,
                content=[TextContent(text=json.dumps(result, ensure_ascii=False))]
            )]

        # 시장 테마 조회
        elif tool_name == "get_market_themes":
            themes = await stock_data_service.get_market_themes()
            result = [
                {
                    "name": theme.theme_name,
                    "description": theme.description,
                    "stocks": [
                        {
                            "name": stock.name,
                            "symbol": stock.symbol.replace('.KS', ''),
                            "sector": stock.sector,
                            "price": stock.price,
                            "change_percent": stock.change_percent
                        }
                        for stock in theme.stocks
                    ],
                    "performance": theme.performance
                }
                for theme in themes
            ]
            return [ToolResult(
                toolCallId=tool_call.id,
                content=[TextContent(text=json.dumps(result, ensure_ascii=False))]
            )]

        # 테마별 종목 조회
        elif tool_name == "get_theme_stocks":
            stocks = await stock_data_service.get_theme_stocks(arguments["theme"])
            result = [
                {
                    "name": stock.name,
                    "symbol": stock.symbol.replace('.KS', ''),
                    "sector": stock.sector,
                    "industry": stock.industry,
                    "price": stock.price,
                    "change_percent": stock.change_percent,
                    "market_cap": stock.market_cap
                }
                for stock in stocks
            ]
            return [ToolResult(
                toolCallId=tool_call.id,
                content=[TextContent(text=json.dumps(result, ensure_ascii=False))]
            )]

        # 상위 종목 조회
        elif tool_name == "get_top_stocks":
            stocks = await stock_data_service.get_top_performing_stocks(
                arguments.get("theme")
            )
            result = [
                {
                    "name": stock.name,
                    "symbol": stock.symbol.replace('.KS', ''),
                    "sector": stock.sector,
                    "price": stock.price,
                    "change_percent": stock.change_percent,
                    "market_cap": stock.market_cap
                }
                for stock in stocks
            ]
            return [ToolResult(
                toolCallId=tool_call.id,
                content=[TextContent(text=json.dumps(result, ensure_ascii=False))]
            )]

        # 전망 리포트 생성
        elif tool_name == "generate_forecast_report":
            from datetime import datetime

            # 뉴스 수집
            news_data = []
            if arguments.get("include_news", True):
                for keyword in arguments["keywords"][:3]:
                    try:
                        hits, _, _ = await chat_service._search_news_simple_hybrid(keyword, size=10)
                        news_data.extend(hits)
                    except Exception as e:
                        logger.warning(f"뉴스 검색 실패 ({keyword}): {e}")

            # 온톨로지 그래프 데이터 수집
            graph_data = []
            if arguments.get("include_ontology", True):
                try:
                    for company in arguments["companies"][:3]:
                        rows, _ = await chat_service._graph(company)
                        graph_data.extend(rows)
                except Exception as e:
                    logger.warning(f"그래프 데이터 수집 실패: {e}")

            # 리포트 생성
            report_content = await _generate_forecast_content(
                query=arguments["query"],
                news_data=news_data[:15],
                graph_data=graph_data,
                companies=arguments["companies"],
                keywords=arguments["keywords"],
                report_mode=arguments.get("report_mode", "테마별 분석")
            )

            result = {
                "query": arguments["query"],
                "report_mode": arguments.get("report_mode", "테마별 분석"),
                "generated_at": datetime.now().isoformat(),
                "companies": arguments["companies"],
                "keywords": arguments["keywords"],
                **report_content,
                "data_quality": {
                    "news_count": len(news_data),
                    "graph_entities": len(graph_data),
                    "analysis_period": f"{arguments.get('lookback_days', 30)}일"
                }
            }

            return [ToolResult(
                toolCallId=tool_call.id,
                content=[TextContent(text=json.dumps(result, ensure_ascii=False))]
            )]

        else:
            return [ToolResult(
                toolCallId=tool_call.id,
                content=[TextContent(text=f"Unknown tool: {tool_name}")]
            )]

    except Exception as e:
        logger.error(f"도구 실행 오류: {e}", exc_info=True)
        return [ToolResult(
            toolCallId=tool_call.id,
            content=[TextContent(text=f"Error: {str(e)}")]
        )]


async def _generate_forecast_content(
    query: str,
    news_data: list,
    graph_data: list,
    companies: list,
    keywords: list,
    report_mode: str
) -> dict:
    """전망 리포트 내용 생성 (헬퍼 함수)"""

    # 뉴스 요약
    news_summary = []
    for news in news_data[:10]:
        title = news.get("title", "")
        date = news.get("date", "")
        if title:
            news_summary.append(f"• {title} ({date})")

    # 회사/테마 정보
    if report_mode == "테마별 분석":
        subject = f"{keywords[0]} 테마" if keywords else "분석 대상"
        analysis_scope = f"관련 주요 기업: {', '.join(companies[:5])}" if companies else ""
    else:
        subject = companies[0] if companies else "대상 기업"
        analysis_scope = f"분석 대상: {subject}"

    return {
        "executive_summary": f"""
**{subject} 전망 요약**

{analysis_scope}

최근 {len(news_data)}건의 관련 뉴스를 분석한 결과, {subject} 섹터는 다음과 같은 주요 동향을 보이고 있습니다:

• 최신 뉴스 동향: {len(news_data)}건
• 주요 키워드: {', '.join(keywords[:3])}
• 분석 기업 수: {len(companies)}개사
        """.strip(),

        "news_analysis": f"""
**주요 뉴스 분석**

최근 수집된 뉴스 중 주요 내용:

{chr(10).join(news_summary[:8])}

**분석 결과:**
- 총 {len(news_data)}건의 관련 뉴스가 확인됨
- 주요 관심사: {', '.join(keywords[:3])}
        """.strip(),

        "ontology_insights": f"""
**관계 분석 및 인사이트**

온톨로지 그래프 분석 결과:
- 수집된 엔티티: {len(graph_data)}개
- 주요 관계: 기업간 연관성, 사업 영역 중복도

**주요 발견사항:**
- {companies[0] if companies else '분석 대상'} 중심의 네트워크 구조
- 관련 산업 간 연결성 분석
        """.strip(),

        "financial_outlook": f"""
**재무 전망**

{subject}의 재무적 관점 분석:

**기회 요인:**
- 관련 뉴스 활동도가 {'높아' if len(news_data) > 10 else '적정 수준이어서'} 시장 관심도 상승 기대
- {keywords[0] if keywords else '관련'} 산업 동향 긍정적

**리스크 요인:**
- 시장 변동성에 따른 불확실성
- 거시경제 환경 변화 영향
        """.strip(),

        "conclusion": f"""
**투자 전망 및 결론**

**종합 평가:** {subject}

1. **긍정적 요인**
   - 관련 뉴스 발생량: {len(news_data)}건
   - 산업 내 연관성: {len(graph_data)}개 엔티티

2. **주의사항**
   - 뉴스 기반 단기 변동성 가능성
   - 펀더멘털 분석 병행 필요

3. **투자 의견**
   - 관심 종목: {', '.join(companies[:3])}
   - 모니터링 키워드: {', '.join(keywords[:3])}
        """.strip()
    }


async def main():
    """MCP 서버 실행"""
    logger.info("Ontology Chat MCP 서버 시작...")

    try:
        # stdio 전송을 통한 서버 실행
        async with stdio.stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream)
    except Exception as e:
        logger.error(f"MCP 서버 실행 오류: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())