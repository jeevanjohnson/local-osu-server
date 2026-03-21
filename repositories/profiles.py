"""
Purpose/Domain/Concept:
- This file contains the repository (database interactions) related profiles.json file.
"""

from pathlib import Path

from jays_tools.json_database import JsonDatabase

from models.database.profiles import CurrentProfile as Profile
from models.database.profiles import CurrentProfiles as Profiles


class ProfilesRepository:
    def __init__(self, path: Path):
        self.profiles = JsonDatabase(path, models=Profiles)

    def get_profiles(self) -> Profiles | None:
        with self.profiles as profiles:
            if not profiles.all:
                return None

            return profiles

    def get_profile(self, profile_name: str) -> Profile | None:
        with self.profiles as profiles:
            if profile_name not in profiles.all:
                return None

            return profiles.all[profile_name]

    def create_new_profile(self, profile_name: str) -> None:
        with self.profiles as profiles:
            if profile_name in profiles.all:
                raise ValueError("Profile already exists.")

            profiles.all[profile_name] = Profile()

            self.profiles.set(profiles)

    def create_profile(self, profile_name: str, profile_data: Profile) -> None:
        with self.profiles as profiles:
            profiles.all[profile_name] = profile_data
            self.profiles.set(profiles)

    def delete_profile(self, profile_name: str) -> None:
        with self.profiles as profiles:
            if profile_name in profiles.all:
                del profiles.all[profile_name]
            else:
                raise ValueError("Profile does not exist.")

            self.profiles.set(profiles)

    def update_profile(self, profile_name: str, profile: Profile) -> None:
        with self.profiles as profiles:
            if profile_name in profiles.all:
                profiles.all[profile_name] = profile
            else:
                raise ValueError("Profile does not exist.")
