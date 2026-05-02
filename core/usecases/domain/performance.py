from core.repositories.performance import PerformanceRepository
from jays_tools.architecture import DomainUseCase, Repositories
from core.models.adapters.database.performance import Performance


class PerformanceRepositories(Repositories):
    performance = PerformanceRepository()


class PerformanceDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.repositories = PerformanceRepositories()
        self.services = None
        self.adapters = None

    async def get_performance(self, profile_name: str) -> Performance | None:
        return await self.repositories.performance.get_performance(profile_name)

    async def create_performance(self, performance: Performance) -> Performance:
        return await self.repositories.performance.create_performance(performance)

    async def update_performance(self, performance: Performance) -> Performance:
        return await self.repositories.performance.update_performance(performance)

    async def delete_performance(self, performance: Performance) -> None:
        await self.repositories.performance.delete_performance(performance)
