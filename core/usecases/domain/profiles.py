from core.models.database.profile import Profile
from core.repositories.profiles import ProfilesRepository


def get_all() -> dict[str, Profile]:
    """Get all profiles from repository."""
    profiles_repo = ProfilesRepository()
    return profiles_repo.get_profiles()


def get(profile_name: str) -> Profile | None:
    """Get a profile by name."""
    profiles_repo = ProfilesRepository()
    return profiles_repo.get_profile(profile_name)


def create_new_profile(profile_name: str) -> Profile:
    """Create a new profile."""
    profiles_repo = ProfilesRepository()
    return profiles_repo.create_new_profile(profile_name)


def profile_exists(profile_name: str) -> bool:
    """Check if a profile exists."""
    profiles_repo = ProfilesRepository()
    return profiles_repo.profile_exists(profile_name)


def delete_profile(profile_name: str) -> None:
    """Delete a profile."""
    profiles_repo = ProfilesRepository()
    profiles_repo.delete_profile(profile_name)


def update_profile(profile_name: str, profile: Profile) -> Profile:
    """Update an entire profile in the repository."""
    profiles_repo = ProfilesRepository()
    return profiles_repo.update_profile(profile_name, profile)