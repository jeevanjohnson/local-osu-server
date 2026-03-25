import time

import aiohttp

from cache import cached_for_10_minutes


async def measure(url: str) -> float:
    start = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            await response.read()

    return (time.perf_counter() - start) * 1000  # ms

@cached_for_10_minutes
async def bancho_api() -> float:
    return await measure("https://osu.ppy.sh/api/v2/")
