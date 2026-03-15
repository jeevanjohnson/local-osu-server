"""
Purpose/Domain/Concept:
- This file contains the logic related to user profiles.
"""

from constants import PROFILES_FILE
from repositories.profiles import ProfilesRepository
from models.database.profiles import Profile, ProfileData

def get_all_profiles() -> Profile | None:
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

def update_profile(profile_name: str, profile_data: ProfileData) -> None:
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    profiles_repo.update_profile(profile_name, profile_data)

    return