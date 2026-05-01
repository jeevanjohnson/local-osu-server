from core.models.adapters.database.profile_settings import ProfileSettings
from core.repositories.database import SQLDatabaseInstance
from jays_tools.architecture import Repository
from jays_tools.sql_database import EqualTo


class ProfileSettingsRepository(Repository):
    def __init__(self) -> None:
        self.database = SQLDatabaseInstance()

    async def get_profile_settings(self, profile_name: str) -> ProfileSettings | None:
        settings_search_result = await self.database.find(
            ProfileSettings,
            where=EqualTo("profile_name", profile_name)
        )
        if not settings_search_result:
            return None

        return settings_search_result[0]

    async def create_profile_settings(self, profile_name: str) -> ProfileSettings:
        return await self.database.insert(
            ProfileSettings(profile_name=profile_name)
        )

    async def update_profile_settings(self, profile_settings: ProfileSettings) -> ProfileSettings:
        return await self.database.update(profile_settings)

    async def delete_profile_settings(self, profile_settings: ProfileSettings) -> None:
        await self.database.delete(profile_settings)
