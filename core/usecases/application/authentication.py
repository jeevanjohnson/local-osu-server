from core.repositories.interface_state import InterfaceStateRepository
from core.repositories.profiles import ProfilesRepository
# from models.

def current_logged_in_profile() -> str | None:
    state_repo = InterfaceStateRepository()
    database = state_repo.get_state()

    return database.current_profile

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