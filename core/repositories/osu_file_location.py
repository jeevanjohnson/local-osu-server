from core.models.database.osu_file_location import OsuFileLocation
from jays_tools import JsonDatabase
from core.constants import OSU_FILE_LOCATION

class OsuFileLocationRepository:
    def __init__(self) -> None:
        self.database = JsonDatabase(
            path=OSU_FILE_LOCATION, 
            database_model=OsuFileLocation
        )
    
    def get(self) -> OsuFileLocation:
        return self.database.get_database()

    def update(self, location: OsuFileLocation) -> OsuFileLocation:
        return self.database.update_database(location)
