import asyncio
from api.mcp.tools import SearchNewsTool

async def test_search_news():
    tool = SearchNewsTool()
    result = await tool.call(query="인공지능", limit=5)
    print(result)

# 실행
asyncio.run(test_search_news())