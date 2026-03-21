"""
Purpose/Domain/Concept:
- This file contains the logic related to user profiles.
"""

from constants import PROFILES_FILE
from models.database.profiles import (
    CurrentProfile as Profile,
)
from models.database.profiles import (
    CurrentProfiles as Profiles,
)
from repositories.profiles import ProfilesRepository


def get_profiles() -> Profiles | None:
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    return profiles_repo.get_profiles()


def get_profile(profile_name: str) -> Profile | None:
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    profile = profiles_repo.get_profile(profile_name)

    if profile is None:
        return None

    return profile


def create_profile(profile_name: str) -> None:
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    profiles_repo.create_new_profile(profile_name)

    return


def delete_profile(profile_name: str) -> None:
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    profiles_repo.delete_profile(profile_name)

    return


def update_profile(profile_name: str, updated_profile: Profile) -> None:
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    profiles_repo.update_profile(profile_name, updated_profile)

    return
