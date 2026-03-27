from models.database.server_settings import CurrentServerSettings as ServerSettings
from repositories.server_settings import ServerSettingsRepository


async def get_server_settings() -> ServerSettings:
    server_settings_repo = ServerSettingsRepository()
    return await server_settings_repo.get_server_settings()


async def update_server_settings(updated_settings: ServerSettings) -> None:
    server_settings_repo = ServerSettingsRepository()
    await server_settings_repo.update_server_settings(updated_settings)

    return


async def credentials_exist() -> bool:
    server_settings_repo = ServerSettingsRepository()
    server_settings = await server_settings_repo.get_server_settings()

    return (
        server_settings.osu_api_v2_client_id is not None
        and server_settings.osu_api_v2_client_secret is not None
        and server_settings.osu_api_v2_client_id.isdecimal()
    )


async def osu_daily_credentials_exist() -> bool:
    server_settings_repo = ServerSettingsRepository()
    server_settings = await server_settings_repo.get_server_settings()

    return server_settings.osu_daily_api_key is not None
