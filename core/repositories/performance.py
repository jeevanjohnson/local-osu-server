from jays_tools.architecture import Repository
from core.models.adapters.database.performance import Performance
from core.repositories.database import SQLDatabaseInstance


class PerformanceRepository(Repository):
    def __init__(self) -> None:
        self.database = SQLDatabaseInstance()

    async def get_performance(self, profile_name: str) -> Performance | None:
        performance_search_result = await self.database.find(
            Performance,
            where={"profile_name": profile_name}
        )

        if not performance_search_result:
            return None

        return performance_search_result[0]

    async def create_performance(self, performance: Performance) -> Performance:
        return await self.database.insert(performance)

    async def update_performance(self, performance: Performance) -> Performance:
        return await self.database.update(performance)

    async def delete_performance(self, performance: Performance) -> None:
        await self.database.delete(performance)
