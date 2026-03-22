from constants import SERVER_SETTINGS_FILE
from models.database.server_settings import CurrentServerSettings as ServerSettings
from repositories.server_settings import ServerSettingsRepository


async def get_server_settings() -> ServerSettings:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    return await server_settings_repo.get_server_settings()


async def update_server_settings(updated_settings: ServerSettings) -> None:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    await server_settings_repo.update_server_settings(updated_settings)

    return

async def credentials_exist() -> bool:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    server_settings = await server_settings_repo.get_server_settings()

    return (
        server_settings.osu_api_v2_client_id is not None
        and server_settings.osu_api_v2_client_secret is not None
        and server_settings.osu_api_v2_client_id.isdecimal()
    )