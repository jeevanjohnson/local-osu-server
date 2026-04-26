from core.models.adapters.database.profile import Profile
from core.repositories.database import SQLDatabaseInstance
from jays_tools.architecture import Repository
from jays_tools.sql_database import EqualTo


class ProfilesRepository(Repository):
    def __init__(self) -> None:
        self.database = SQLDatabaseInstance()

    async def get_profiles(self) -> list[Profile]:
        return await self.database.find(Profile)

    async def get_profile(self, profile_name: str) -> Profile | None:
        profile_search_result = await self.database.find(
            Profile,
            where=EqualTo("name", profile_name)
        )
        if not profile_search_result:
            return None

        return profile_search_result[0]

    async def create_new_profile(self, profile_name: str) -> Profile:
        return await self.database.insert(
            Profile(name=profile_name)
        )

    async def profile_exists(self, profile_name: str) -> bool:
        profile_search_result = await self.database.find(
            Profile,
            where=EqualTo("name", profile_name)
        )

        if not profile_search_result:
            return False

        return True

    async def update_profile(self, profile: Profile) -> Profile:
        return await self.database.update(profile)

    async def delete_profile(self, profile: Profile) -> None:
        await self.database.delete(profile)
