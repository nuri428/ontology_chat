#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '/app')

async def test():
    from api.services.chat_service import ChatService

    service = ChatService()
    rows, elapsed, error = await service._query_graph('삼성전자', limit=10)

    print(f'===== SAMSUNG QUERY TEST =====')
    print(f'Results: {len(rows)} rows in {elapsed:.1f}ms')
    if error:
        print(f'Error: {error}')

    print(f'\nTop 10 results:')
    for i, r in enumerate(rows[:10], 1):
        labels = r.get('labels', [])
        n = r.get('n', {})
        label_str = labels[0] if labels else '?'
        name = n.get('name') or n.get('title') or n.get('label', 'N/A')
        print(f'{i}. [{label_str}] {name[:70]}')

asyncio.run(test())