import asyncio, httpx

async def check():
    aid = 'cade6e0a-b68d-4817-8634-be90a982a6c3'
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(f'http://127.0.0.1:8001/api/v1/analysis/{aid}')
        result = r.json()
        print(f"Status: {result['status']}")
        print(f"AI: {result.get('ai_interpretation')}")

asyncio.run(check())
