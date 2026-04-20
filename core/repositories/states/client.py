from core.models.application.states.client import ClientState
from jays_tools import JsonDatabase
from core.constants import CLIENT_STATE

class ClientStateRepository:
    def __init__(self) -> None:
        self.database = JsonDatabase(
            path=CLIENT_STATE, 
            database_model=ClientState
        )
    
    def get_state(self) -> ClientState:
        return self.database.get_database()

    def update_state(self, state: ClientState) -> ClientState:
        return self.database.update_database(state)