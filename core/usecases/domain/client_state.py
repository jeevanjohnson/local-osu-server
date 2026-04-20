from core.repositories.states.client import ClientStateRepository
from core.models.application.states.client import ClientState

def get_client_state() -> ClientState:
    client_state_repo = ClientStateRepository()
    return client_state_repo.get_state()

def update_client_state(new_state: ClientState) -> ClientState:
    client_state_repo = ClientStateRepository()
    return client_state_repo.update_state(new_state)