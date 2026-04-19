from core.repositories.server_settings import ServerSettingsRepository
from core.models.server_settings import ServerSettings

def get_server_settings() -> ServerSettings:
    repo = ServerSettingsRepository()
    return repo.get_settings()

def update_server_settings(settings: ServerSettings) -> ServerSettings:
    repo = ServerSettingsRepository()
    return repo.update_settings(settings)

def get_osu_api_v2_client_id() -> int | None:
    settings = get_server_settings()
    return settings.osu_api_v2_client_id

def get_osu_api_v2_client_secret() -> str | None:
    settings = get_server_settings()
    return settings.osu_api_v2_client_secret

def update_osu_api_client_id(client_id: int | None) -> ServerSettings:
    settings = get_server_settings()
    settings.osu_api_v2_client_id = client_id
    return update_server_settings(settings)

def update_osu_api_client_secret(client_secret: str | None) -> ServerSettings:
    settings = get_server_settings()
    settings.osu_api_v2_client_secret = client_secret
    return update_server_settings(settings)