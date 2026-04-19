import socket

from core.repositories.interface_state import InterfaceStateRepository

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

def in_use() -> bool:
    state_repo = InterfaceStateRepository()
    database = state_repo.get_state()

    if database.port_in_use is not None:
        return is_port_in_use(database.port_in_use)

    return False

def get() -> int:
    state_repo = InterfaceStateRepository()
    database = state_repo.get_state()

    if database.port_in_use is not None:
        return database.port_in_use

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        database.port_in_use = s.getsockname()[1]

    updated_database = state_repo.update_state(database)

    return updated_database.port_in_use  # type: ignore


def clear() -> None:
    state_repo = InterfaceStateRepository()
    database = state_repo.get_state()

    database.port_in_use = None
    state_repo.update_state(database)
