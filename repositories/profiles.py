"""
Purpose/Domain/Concept:
- This file contains the repository (database interactions) related profiles.json file.
"""

from pathlib import Path

from jays_tools.json_database import JsonDatabase

from adapters.app_logger import app_logger
from models.database.profiles import CurrentProfile as Profile
from models.database.profiles import CurrentProfiles as Profiles
from models.domain.errors import (
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
    ProfilesNotFoundError,
)


class ProfilesRepository:
    def __init__(self, path: Path):
        self.profiles = JsonDatabase(path, models=Profiles)

    @app_logger.log(msg="repository require profiles")
    async def require_profiles(self) -> Profiles:
        async with self.profiles as profiles:
            if not profiles.all:
                raise ProfilesNotFoundError("No profiles found.")

            return profiles

    @app_logger.log(msg="repository get profiles")
    async def get_profiles(self) -> Profiles | None:
        try:
            return await self.require_profiles()
        except ProfilesNotFoundError:
            return None

    @app_logger.log(msg="repository require profile")
    async def require_profile(self, profile_name: str) -> Profile:
        async with self.profiles as profiles:
            if profile_name not in profiles.all:
                raise ProfileNotFoundError(f"Profile '{profile_name}' does not exist.")

            return profiles.all[profile_name]

    @app_logger.log(msg="repository get profile")
    async def get_profile(self, profile_name: str) -> Profile | None:
        try:
            return await self.require_profile(profile_name)
        except ProfileNotFoundError:
            return None

    @app_logger.log(msg="repository create new profile")
    async def create_new_profile(self, profile_name: str) -> None:
        async with self.profiles as profiles:
            if profile_name in profiles.all:
                raise ProfileAlreadyExistsError("Profile already exists.")

            profiles.all[profile_name] = Profile()

            self.profiles.set(profiles)

    @app_logger.log(msg="repository create profile")
    async def create_profile(self, profile_name: str, profile_data: Profile) -> None:
        async with self.profiles as profiles:
            profiles.all[profile_name] = profile_data
            self.profiles.set(profiles)

    @app_logger.log(msg="repository delete profile")
    async def delete_profile(self, profile_name: str) -> None:
        async with self.profiles as profiles:
            if profile_name in profiles.all:
                del profiles.all[profile_name]
            else:
                raise ProfileNotFoundError("Profile does not exist.")

            self.profiles.set(profiles)

    @app_logger.log(msg="repository update profile")
    async def update_profile(self, profile_name: str, profile: Profile) -> None:
        async with self.profiles as profiles:
            if profile_name in profiles.all:
                profiles.all[profile_name] = profile
            else:
                raise ProfileNotFoundError("Profile does not exist.")

            self.profiles.set(profiles)
