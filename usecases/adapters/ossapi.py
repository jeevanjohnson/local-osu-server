import time
from typing import TypedDict

import aiohttp

from usecases.adapters.ossapiasync import OssapiAsync
from repositories.server_settings import ServerSettingsRepository


async def get() -> OssapiAsync | None:
    credentials = await credentials_exist()

    if not credentials:
        return None

    return OssapiAsync(
        credentials["osu_api_v2_client_id"], credentials["osu_api_v2_client_secret"]
    )


class CredentialsExistResponse(TypedDict):
    osu_api_v2_client_id: int
    osu_api_v2_client_secret: str


async def credentials_exist() -> CredentialsExistResponse | None:
    server_settings_repo = ServerSettingsRepository()
    server_settings = await server_settings_repo.get_server_settings()

    if (
        not server_settings.osu_api_v2_client_id
        or not server_settings.osu_api_v2_client_secret
    ):
        return None

    return {
        "osu_api_v2_client_id": server_settings.osu_api_v2_client_id,
        "osu_api_v2_client_secret": server_settings.osu_api_v2_client_secret,
    }


async def latency() -> float:
    start = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        async with session.get("https://osu.ppy.sh/api/v2/") as response:
            await response.read()

    return (time.perf_counter() - start) * 1000  # ms
