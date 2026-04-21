from core.repositories.states.client import ClientStateRepository
from core.models.application.states.client import ClientState
import core.osu_protocol.cho.server as cho_server

def get_client_state() -> ClientState:
    client_state_repo = ClientStateRepository()
    return client_state_repo.get_state()

def update_client_state(new_state: ClientState) -> ClientState:
    client_state_repo = ClientStateRepository()
    return client_state_repo.update_state(new_state)

def restart_client() -> ClientState:
    client_state = get_client_state()
    client_state.outgoing_packets += cho_server.reset()
    return update_client_state(client_state)