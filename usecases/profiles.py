"""
Purpose/Domain/Concept:
- This file contains the logic related to user profiles.
"""

from adapters.app_logger import app_logger
from constants import PROFILES_FILE
from models.database.profiles import (
    CurrentProfile as Profile,
)
from models.database.profiles import (
    CurrentProfiles as Profiles,
)
from models.domain.errors import ProfileNotFoundError, ProfilesNotFoundError
from repositories.profiles import ProfilesRepository


@app_logger.log(msg="usecase get profiles")
async def get_profiles() -> Profiles | None:
    profiles_repo = ProfilesRepository(PROFILES_FILE)
    try:
        return await profiles_repo.require_profiles()
    except ProfilesNotFoundError:
        return None


@app_logger.log(msg="usecase get profile")
async def get_profile(profile_name: str) -> Profile | None:
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    try:
        return await profiles_repo.require_profile(profile_name)
    except ProfileNotFoundError:
        return None


@app_logger.log(msg="usecase require profile")
async def require_profile(profile_name: str) -> Profile:
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    return await profiles_repo.require_profile(profile_name)


@app_logger.log(msg="usecase create profile")
async def create_profile(profile_name: str) -> None:
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    await profiles_repo.create_new_profile(profile_name)

    return


@app_logger.log(msg="usecase delete profile")
async def delete_profile(profile_name: str) -> None:
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    await profiles_repo.delete_profile(profile_name)

    return


@app_logger.log(msg="usecase update profile")
async def update_profile(profile_name: str, updated_profile: Profile) -> None:
    profiles_repo = ProfilesRepository(PROFILES_FILE)

    await profiles_repo.update_profile(profile_name, updated_profile)

    return
