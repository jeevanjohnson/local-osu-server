from jays_tools import JsonDatabase

from constants.paths import CLIENT_STATE
from models.database.client.state import ClientState


class ClientStateRepository:
    def __init__(self) -> None:
        self.client_state = JsonDatabase(path=CLIENT_STATE, models=ClientState)

    async def start_client_state(self, profile_name: str) -> None:
        async with self.client_state as client_state:
            client_state.profile_name = profile_name
            client_state.logged_in = True
            self.client_state.set(client_state)

    async def delete_client_state(self) -> None:
        async with self.client_state as client_state:
            client_state.profile_name = ""
            client_state.logged_in = False
            self.client_state.set(client_state)

    async def get_client_state(self) -> ClientState:
        async with self.client_state as client_state:
            return client_state

    async def update_client_state(self, new_state: ClientState) -> None:
        async with self.client_state as old_client_state:
            self.client_state.set(new_state)
