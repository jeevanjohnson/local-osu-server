"""
Purpose/Domain/Concept:
- This file contains the repository (database interactions) related profiles.json file.
"""

from jays_tools.json_database import JsonDatabase

# from adapters import log_time
from constants.paths import PROFILES
from models.database.profiles import CurrentProfile as Profile
from models.database.profiles import CurrentProfiles as Profiles


class ProfilesRepository:
    def __init__(self):
        self.profiles = JsonDatabase(PROFILES, models=Profiles)

    async def get_all(self) -> Profiles:
        async with self.profiles as profiles:
            return profiles

    # log
    async def get(self, name: str) -> Profile | None:
        async with self.profiles as profiles:
            if name not in profiles.all:
                return None

            return profiles.all[name]

    # log
    async def create_new_profile(self, profile_name: str) -> None:
        async with self.profiles as profiles:
            if profile_name in profiles.all:
                raise ValueError("Profile already exists.")

            profiles.all[profile_name] = Profile()

            self.profiles.set(profiles)

    # log
    async def create_profile(self, profile_name: str, profile_data: Profile) -> None:
        async with self.profiles as profiles:
            profiles.all[profile_name] = profile_data
            self.profiles.set(profiles)

    # log
    async def delete_profile(self, profile_name: str) -> None:
        async with self.profiles as profiles:
            if profile_name in profiles.all:
                del profiles.all[profile_name]
            else:
                raise ValueError("Profile does not exist.")

            self.profiles.set(profiles)

    # log
    async def update_profile(self, profile_name: str, profile: Profile) -> None:
        async with self.profiles as profiles:
            if profile_name in profiles.all:
                profiles.all[profile_name] = profile
            else:
                raise ValueError("Profile does not exist.")

            self.profiles.set(profiles)
