from jays_tools.architecture import DomainUseCase, Repositories

from core.repositories.interface import InterfaceStateRepository
from core.repositories.profiles import ProfilesRepository
from core.models.adapters.database.interface import InterfaceState
from core.models.adapters.database.profile import Profile


class AuthenticationRepositories(Repositories):
    interface_state_repository = InterfaceStateRepository()
    profiles_repository = ProfilesRepository()


class AuthenticationDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.repositories = AuthenticationRepositories()
        self.adapters = None
        self.services = None

    async def logged_in_as(self) -> Profile | None:
        current_interface_state = await self.repositories.interface_state_repository.get_state()
        if current_interface_state is None:
            return None

        current_profile = await self.repositories.profiles_repository.get_profile(
            current_interface_state.profile_name
        )
        if current_profile is None:
            return None

        return current_profile

    async def is_logged_in(self) -> bool:
        return await self.logged_in_as() is not None

    async def login(self, profile_name: str) -> InterfaceState:
        return await self.repositories.interface_state_repository.create_state(profile_name)

    async def logout(self) -> None:
        current_interface_state = await self.repositories.interface_state_repository.get_state()
        if current_interface_state is None:
            print("No interface state found")
            return None

        await self.repositories.interface_state_repository.delete_state(current_interface_state)
