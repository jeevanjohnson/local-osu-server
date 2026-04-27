from core.models.adapters.database.beatmaps import Beatmap
from core.repositories.database import SQLDatabaseInstance
from jays_tools.sql_database import EqualTo


class BeatmapRepository:
    def __init__(self) -> None:
        self.database = SQLDatabaseInstance()

    async def get(self, md5: str) -> Beatmap | None:
        beatmaps = await self.database.find(
            Beatmap, EqualTo("md5", md5)
        )
        if not beatmaps:
            return None

        return beatmaps[0]

    async def insert(self, beatmap: Beatmap) -> Beatmap:
        return await self.database.insert(beatmap)

    async def delete(self, beatmap: Beatmap) -> Beatmap:
        return await self.database.delete(beatmap)

    async def update(self, beatmap: Beatmap) -> Beatmap:
        return await self.database.update(beatmap)
