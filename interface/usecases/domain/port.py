import socket

from interface.repositories.interface_state import StateRepository


def get() -> int:
    state_repo = StateRepository()
    database = state_repo.get_state()

    if database.port_in_use is not None:
        return database.port_in_use

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        database.port_in_use = s.getsockname()[1]

    updated_database = state_repo.update_state(database)

    return updated_database.port_in_use  # type: ignore


def clear() -> None:
    state_repo = StateRepository()
    database = state_repo.get_state()

    database.port_in_use = None
    state_repo.update_state(database)
