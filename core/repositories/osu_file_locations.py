from jays_tools.sql_database import EqualTo
from core.repositories.database import SQLDatabaseInstance
from core.models.adapters.database.osu_file_locations import OsuFileLocations
from pathlib import Path
from jays_tools.architecture import Repository


class OsuFileLocationsRepository(Repository):
    def __init__(self) -> None:
        self.database = SQLDatabaseInstance()

    async def get(self, songs_folder: Path) -> OsuFileLocations | None:
        osu_file_locations = await self.database.find(
            OsuFileLocations,
            where=EqualTo("songs_folder_directory", str(songs_folder))
        )
        if not osu_file_locations:
            return None

        return osu_file_locations[0]

    async def create(self, songs_folder: Path) -> OsuFileLocations:
        return await self.database.insert(
            OsuFileLocations(songs_folder_directory=songs_folder)
        )

    async def update(self, locations: OsuFileLocations) -> OsuFileLocations:
        return await self.database.update(locations)
