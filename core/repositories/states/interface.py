from jays_tools import JsonDatabase

from core.models.application.states.interface import InterfaceState
from core.constants import INTERFACE_STATE

class InterfaceStateRepository:
    def __init__(self) -> None:
        self.database = JsonDatabase(
            path=INTERFACE_STATE, 
            database_model=InterfaceState
        )
    
    def get_state(self) -> InterfaceState:
        return self.database.get_database()

    def update_state(self, state: InterfaceState) -> InterfaceState:
        return self.database.update_database(state)