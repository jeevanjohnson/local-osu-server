import time
from typing import TypedDict

import aiohttp

from repositories.server_settings import ServerSettingsRepository
from usecases.adapters.ossapiasync import OssapiAsync


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


def format_time_delta(delta: float) -> str:
    if delta < 1:
        return f"{round(delta * 1000, 2)}ms"
    elif delta < 60:
        return f"{round(delta, 2)}s"
    else:
        minutes = int(delta // 60)
        seconds = round(delta % 60, 2)
        return f"{minutes}m {seconds}s"


async def latency() -> str:
    start = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        async with session.get("https://osu.ppy.sh/api/v2/") as response:
            await response.read()

    latency = time.perf_counter() - start

    return format_time_delta(latency)
