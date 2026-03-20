from repositories.server_settings import ServerSettingsRepository
from models.database.server_settings import (
    CurrentServerSettings as ServerSettings
)
from constants import SERVER_SETTINGS_FILE

def get_server_settings() -> ServerSettings:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    return server_settings_repo.get_server_settings()

def update_server_settings(updated_settings: ServerSettings) -> None:
    server_settings_repo = ServerSettingsRepository(SERVER_SETTINGS_FILE)
    server_settings_repo.update_server_settings(updated_settings)

    return