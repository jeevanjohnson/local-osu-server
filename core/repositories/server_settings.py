from core.repositories.database import SQLDatabaseInstance
from core.models.adapters.database.server_settings import ServerSettings
from jays_tools.sql_database import EqualTo


class ServerSettingsRepository:
    def __init__(self) -> None:
        self.database = SQLDatabaseInstance()

    async def get_settings(self) -> ServerSettings:
        settings = await self.database.find(ServerSettings)
        if not settings:
            return await self.database.insert(ServerSettings())

        return settings[0]

    async def update_settings(self, settings: ServerSettings) -> ServerSettings:
        return await self.database.update(settings)
