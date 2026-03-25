import time

import aiohttp


async def measure(url: str) -> float:
    start = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            await response.read()

    return (time.perf_counter() - start) * 1000  # ms


async def bancho_api() -> float:
    return await measure("https://osu.ppy.sh/api/v2/")
