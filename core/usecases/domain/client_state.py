from core.models.adapters.database.client_state import ClientState
from core.repositories.client_state import ClientStateRepository
from jays_tools.architecture import DomainUseCase, Repositories
import core.adapters.osu_protocol.cho.server as cho_server


class ClientStateRepositories(Repositories):
    client_state = ClientStateRepository()


class ClientStateDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.repositories = ClientStateRepositories()
        self.adapters = None
        self.services = None

    async def get_client_state(self) -> ClientState:
        return await self.repositories.client_state.get_client_state()

    async def update_client_state(self, new_state: ClientState) -> ClientState:
        return await self.repositories.client_state.update_client_state(new_state)
