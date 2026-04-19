from jays_tools import JsonDatabase

from interface.models.state import State


class StateRepository:
    def __init__(self) -> None:
        self.database = JsonDatabase(
            path="./.data/interface_state.json", 
            database_model=State
        )
    
    def get_state(self) -> State:
        return self.database.get_database()

    def update_state(self, state: State) -> State:
        return self.database.update_database(state)