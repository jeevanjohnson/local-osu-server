from jays_tools.architecture import Repository
from core.repositories.database import SQLDatabaseInstance
from core.models.adapters.database.client_state import ClientState


class ClientStateRepository(Repository):
    def __init__(self) -> None:
        self.database = SQLDatabaseInstance()

    async def create_client_state(self) -> ClientState:
        return await self.database.insert(ClientState())

    async def get_client_state(self) -> ClientState:
        client_state = await self.database.find(ClientState)
        if client_state is None:
            return await self.create_client_state()

        return client_state[0]

    async def update_client_state(self, client_state: ClientState) -> ClientState:
        return await self.database.update(client_state)

    async def delete_client_state(self) -> ClientState:
        client_state = await self.get_client_state()
        await self.database.delete(client_state)
        return client_state
