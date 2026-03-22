from jays_tools.json_database import JsonDatabase

from models.database.server_settings import CurrentServerSettings as Settings


class ServerSettingsRepository:
    def __init__(self, path):
        self.server_settings = JsonDatabase(path, models=Settings)

    async def get_server_settings(self) -> Settings:
        async with self.server_settings as server_settings:
            return server_settings

    async def update_server_settings(self, updated_settings: Settings) -> None:
        async with self.server_settings as server_settings:
            server_settings = updated_settings

            self.server_settings.set(server_settings)
