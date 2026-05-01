from core.models.adapters.database.profile_settings import ProfileSettings
from core.repositories.profile_settings import ProfileSettingsRepository
from jays_tools.architecture import DomainUseCase, Repositories


class ProfileSettingsRepositories(Repositories):
    profile_settings = ProfileSettingsRepository()


class ProfileSettingsDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.repositories = ProfileSettingsRepositories()
        self.adapters = None
        self.services = None

    async def get_profile_settings(self, profile_name: str) -> ProfileSettings | None:
        return await self.repositories.profile_settings.get_profile_settings(profile_name)

    async def update_profile_settings(self, profile_settings: ProfileSettings) -> ProfileSettings:
        return await self.repositories.profile_settings.update_profile_settings(profile_settings)

    async def create_profile_settings(self, profile_name: str) -> ProfileSettings:
        return await self.repositories.profile_settings.create_profile_settings(profile_name)

    async def delete_profile_settings(self, profile_settings: ProfileSettings) -> None:
        await self.repositories.profile_settings.delete_profile_settings(profile_settings)
