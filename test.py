import asyncio

from aiohttp import ClientSession, ClientTimeout


async def main() -> None:
    url = "https://osudaily.net/api/pp.php"
    params = {
        "k": "8b22a91f9f3558578c70cf650d963f61",
        "t": "pp",
        "v": "9999",
        "m": "0",
    }

    async with ClientSession() as session:
        async with session.get(
            url,
            params=params,
            timeout=ClientTimeout(total=10),
        ) as response:
            response.raise_for_status()
            print(await response.text())


asyncio.run(main())