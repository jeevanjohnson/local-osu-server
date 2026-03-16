from models.database.server_settings import ServerSettings
from database.jsonfile import JsonFile

class ServerSettingsRepository:
    def __init__(self, path):
        self.server_settings = JsonFile[ServerSettings](path)

    def initialize_server_settings(self) -> None:
        with self.server_settings as server_settings:
            server_settings.update(ServerSettings(
                osu_api_key_v1=None,
                osu_api_v2_client_id=None,
                osu_api_v2_client_secret=None,
            ))

    def get_server_settings(self) -> ServerSettings | None:
        with self.server_settings as server_settings:
            if not server_settings:
                return None
            
            return server_settings

    def update_server_settings(self, settings: ServerSettings) -> None:
        with self.server_settings as server_settings:
            server_settings.update(settings)