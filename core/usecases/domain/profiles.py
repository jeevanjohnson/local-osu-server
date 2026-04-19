from core.repositories.profiles import ProfilesRepository
from core.models.profile import Profile

def get_all() -> dict[str, Profile]:
    profiles_repo = ProfilesRepository()
    return profiles_repo.get_profiles()

def get(profile_name: str) -> Profile | None:
    profiles_repo = ProfilesRepository()
    return profiles_repo.get_profile(profile_name)

def create_new_profile(profile_name: str) -> None:
    profiles_repo = ProfilesRepository()
    profiles_repo.create_new_profile(profile_name)

def profile_exists(profile_name: str) -> bool:
    profiles_repo = ProfilesRepository()
    return profiles_repo.profile_exists(profile_name)

def delete_profile(profile_name: str) -> None:
    profiles_repo = ProfilesRepository()
    profiles_repo.delete_profile(profile_name)

def update_avatar_url(profile_name: str, avatar_url: str) -> None:
    profiles_repo = ProfilesRepository()
    profile = profiles_repo.get_profile(profile_name)

    if profile is not None:
        profile.avatar_url = avatar_url
        profiles_repo.update_profile(profile_name, profile)