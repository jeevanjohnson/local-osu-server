import httpx
from typing import AsyncIterator


async def get_async_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client
