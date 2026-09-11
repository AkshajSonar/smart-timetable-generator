import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def run():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        pass # Let's just modify the test to print the response body instead.
