from core.repositories.server_settings import ServerSettingsRepository
from core.models.adapters.database.server_settings import ServerSettings
from jays_tools.architecture import DomainUseCase, Repositories


class ServerSettingsRepositories(Repositories):
    server_settings = ServerSettingsRepository()


class ServerSettingsDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.repositories = ServerSettingsRepositories()
        self.adapters = None
        self.services = None

    async def get_current_server_settings(self) -> ServerSettings:
        return await self.repositories.server_settings.get_settings()

    async def update_server_settings(self, settings: ServerSettings) -> ServerSettings:
        return await self.repositories.server_settings.update_settings(settings)

    async def get_osu_api_v2_client_id(self) -> int | None:
        settings = await self.get_current_server_settings()
        return settings.osu_api_v2_client_id

    async def get_osu_api_v2_client_secret(self) -> str | None:
        settings = await self.get_current_server_settings()
        return settings.osu_api_v2_client_secret

    async def update_osu_api_client_id(self, client_id: int | None) -> ServerSettings:
        settings = await self.get_current_server_settings()
        settings.osu_api_v2_client_id = client_id
        return await self.update_server_settings(settings)

    async def update_osu_api_client_secret(self, client_secret: str | None) -> ServerSettings:
        settings = await self.get_current_server_settings()
        settings.osu_api_v2_client_secret = client_secret
        return await self.update_server_settings(settings)
