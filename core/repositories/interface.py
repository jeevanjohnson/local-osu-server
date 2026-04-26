from core.models.adapters.database.interface import InterfaceState
from core.repositories.database import SQLDatabaseInstance


class InterfaceStateRepository:
    def __init__(self) -> None:
        self.database = SQLDatabaseInstance()

    async def get_state(self) -> InterfaceState | None:
        interface_state = await self.database.find(InterfaceState)
        if interface_state is None:
            return None

        return interface_state[0]

    async def create_state(self, profile_name: str) -> InterfaceState:
        return await self.database.insert(InterfaceState(
            profile_name=profile_name
        ))

    async def update_state(self, state: InterfaceState) -> None:
        await self.database.update(state)

    async def delete_state(self, state: InterfaceState) -> None:
        await self.database.delete(state)
