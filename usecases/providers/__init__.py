from ossapi import OssapiV1

from adapters import OssapiAsync
from constants import SERVER_SETTINGS_FILE
from repositories.server_settings import ServerSettingsRepository

from .osu_daily import OsuDailyCredentialsError as OsuDailyCredentialsError


class ApiV2CredentialsError(Exception):
    pass


async def get_ossapi_async() -> OssapiAsync:
    """
    Reads credentials from ServerSettingsRepository and constructs OssapiAsync.
    Raises ApiV2CredentialsError if credentials are absent or invalid.
    Single source of truth — replaces the duplicated get_ossapi() in
    usecases/scores.py and usecases/beatmaps.py.
    """
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    server_settings = await server_settings_repo.get_server_settings()

    if server_settings.osu_api_v2_client_id is None:
        raise ApiV2CredentialsError(
            "osu! API v2 client id not found in server settings. Please set it up in the server settings page."
        )

    if server_settings.osu_api_v2_client_secret is None:
        raise ApiV2CredentialsError(
            "osu! API v2 client secret not found in server settings. Please set it up in the server settings page."
        )

    if not server_settings.osu_api_v2_client_id.isdecimal():
        raise ApiV2CredentialsError(
            "osu! API v2 client id must be a number. Please check the server settings page."
        )

    osuApiAsync = OssapiAsync(
        int(server_settings.osu_api_v2_client_id),
        server_settings.osu_api_v2_client_secret,
    )

    return osuApiAsync


async def get_ossapi_v1() -> OssapiV1:
    """
    Same pattern as above for v1.
    Replaces the duplicated get_ossapi_v1() in usecases/scores.py.
    """
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    server_settings = await server_settings_repo.get_server_settings()

    if server_settings.osu_api_key_v1 is None:
        raise ApiV2CredentialsError(
            "osu! API v1 token not found in server settings. Please set it up in the server settings page."
        )

    osuApiV1 = OssapiV1(server_settings.osu_api_key_v1)

    return osuApiV1
