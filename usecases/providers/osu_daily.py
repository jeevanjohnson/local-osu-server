"""
Provider for osu!daily HTTP client and credential validation.
Follows the same pattern as OSS API provider.
"""

from aiohttp import ClientSession
from constants import SERVER_SETTINGS_FILE
from repositories.server_settings import ServerSettingsRepository


class OsuDailyCredentialsError(Exception):
    """Raised when osu!daily API key is missing or invalid."""
    pass


HTTP_SESSION: ClientSession | None = None


async def get_http_client() -> ClientSession:
    """Get or create persistent HTTP client for osu!daily requests."""
    global HTTP_SESSION
    if HTTP_SESSION is None or HTTP_SESSION.closed:
        HTTP_SESSION = ClientSession()
    return HTTP_SESSION


async def get_osu_daily_api_key() -> str:
    """
    Get osu!daily API key from server settings.
    Raises OsuDailyCredentialsError if key is missing.
    """
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    server_settings = await server_settings_repo.get_server_settings()

    if server_settings.osu_daily_api_key is None:
        raise OsuDailyCredentialsError(
            "osu!daily API key not found in server settings. Please set it up in the server settings page."
        )

    normalized_api_key = server_settings.osu_daily_api_key.strip()

    if not normalized_api_key:
        raise OsuDailyCredentialsError(
            "osu!daily API key is empty. Please check the server settings page."
        )

    return normalized_api_key
