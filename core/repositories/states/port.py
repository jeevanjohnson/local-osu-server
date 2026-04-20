from core.models.application.states.port import PortState
from jays_tools import JsonDatabase
from core.constants import PORT_STATE

class PortStateRepository:
    def __init__(self) -> None:
        self.database = JsonDatabase(
            path=PORT_STATE, 
            database_model=PortState
        )
    
    def get_state(self) -> PortState:
        return self.database.get_database()

    def update_state(self, state: PortState) -> PortState:
        return self.database.update_database(state)