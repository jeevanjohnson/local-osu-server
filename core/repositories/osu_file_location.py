from core.models.database.osu_file_location import OsuFileLocation
from jays_tools import JsonDatabase
from core.constants import OSU_FILE_LOCATION

class OsuFileLocationRepository:
    # Class-level cache to avoid reloading database from disk on every instantiation
    cached_database: OsuFileLocation | None = None
    
    def __init__(self) -> None:
        self.database = JsonDatabase(
            path=OSU_FILE_LOCATION, 
            database_model=OsuFileLocation
        )
    
    def get(self) -> OsuFileLocation:
        # Return cached copy if available, otherwise load and cache
        if OsuFileLocationRepository.cached_database is None:
            OsuFileLocationRepository.cached_database = self.database.get_database()
        
        return OsuFileLocationRepository.cached_database

    def update(self, location: OsuFileLocation) -> OsuFileLocation:
        # Update database and refresh cache
        result = self.database.update_database(location)
        OsuFileLocationRepository.cached_database = result
        return result
