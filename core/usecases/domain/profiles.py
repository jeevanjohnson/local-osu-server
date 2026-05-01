from core.models.adapters.database.profile import Profile
from core.models.domain.normalizers.country_codes import CountryCode
from core.repositories.profiles import ProfilesRepository
from jays_tools.architecture import DomainUseCase, Repositories


class ProfilesRepositories(Repositories):
    profiles = ProfilesRepository()


class ProfilesDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.repositories = ProfilesRepository()
        self.adapters = None
        self.services = None

    async def get_all(self) -> list[Profile]:
        """Get all profiles from repository."""
        return await self.repositories.get_profiles()

    async def get(self, profile_name: str) -> Profile | None:
        """Get a profile by name."""
        return await self.repositories.get_profile(profile_name)

    async def create_new_profile(self, profile_name: str) -> Profile:
        """Create a new profile."""
        return await self.repositories.create_new_profile(profile_name)

    async def profile_exists(self, profile_name: str) -> bool:
        """Check if a profile exists."""
        return await self.repositories.profile_exists(profile_name)

    async def delete_profile(self, profile_name: str) -> None:
        """Delete a profile."""
        profile = await self.get(profile_name)

        if not profile:
            raise ValueError(f"Profile {profile_name} does not exist.")

        await self.repositories.delete_profile(profile)

    async def update_profile(self, profile: Profile) -> Profile:
        """Update an entire profile in the repository."""
        return await self.repositories.update_profile(profile)

    async def update_pfp(self, profile_name: str, pfp_url: str) -> Profile:
        profile = await self.get(profile_name)
        if profile is None:
            raise Exception("no profile to update")

        profile.avatar_url = pfp_url

        return await self.update_profile(profile)

    async def update_notes(self, profile_name: str, notes: str) -> Profile:
        profile = await self.get(profile_name)
        if profile is None:
            raise Exception("no profile to update")

        profile.notes = notes

        return await self.update_profile(profile)

    async def update_country(self, profile_name: str, country_code: CountryCode) -> Profile:
        profile = await self.get(profile_name)
        if profile is None:
            raise Exception("no profile to update")

        profile.country_code = country_code

        return await self.update_profile(profile)
