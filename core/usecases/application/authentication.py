from core.repositories.states.interface import InterfaceStateRepository
from core.repositories.profiles import ProfilesRepository
from core.models.database.profile import Profile

def current_logged_in_profile() -> tuple[str, Profile] | None:
    state_repo = InterfaceStateRepository()
    database = state_repo.get_state()

    if database.current_profile is None:
        return None

    profiles_repo = ProfilesRepository()
    profile = profiles_repo.get_profile(database.current_profile)
    if profile is None:
        return None

    return (database.current_profile, profile)

def is_logged_in() -> bool:
    return current_logged_in_profile() is not None

def log_in(profile_name: str) -> None:
    state_repo = InterfaceStateRepository()
    database = state_repo.get_state()

    database.current_profile = profile_name
    state_repo.update_state(database)

def log_out() -> None:
    state_repo = InterfaceStateRepository()
    database = state_repo.get_state()

    database.current_profile = None
    state_repo.update_state(database)