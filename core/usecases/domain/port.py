import socket

from core.repositories.port_state import PortStateRepository

def in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

def assign_port_to(identifier: str) -> int:
    state_repo = PortStateRepository()
    database = state_repo.get_state()

    if identifier in database.ports_in_uses:
        del database.ports_in_uses[identifier]
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port = s.getsockname()[1]
    
    database.ports_in_uses[identifier] = port
    state_repo.update_state(database)

    return port

def retrive_port_for(identifier: str) -> int | None:
    state_repo = PortStateRepository()
    database = state_repo.get_state()

    if identifier in database.ports_in_uses:
        return database.ports_in_uses[identifier]
    
    return None

def clear_port_for(identifier: str) -> None:
    state_repo = PortStateRepository()
    database = state_repo.get_state()

    if identifier in database.ports_in_uses:
        del database.ports_in_uses[identifier]
        state_repo.update_state(database)
