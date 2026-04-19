from jays_tools import JsonDatabase
from core.models.server_settings import ServerSettings
from core.constants import SERVER_SETTINGS

class ServerSettingsRepository:
    def __init__(self) -> None:
        self.database = JsonDatabase(
            path=SERVER_SETTINGS, 
            database_model=ServerSettings
        )
    
    def get_settings(self) -> ServerSettings:
        return self.database.get_database()

    def update_settings(self, settings: ServerSettings) -> ServerSettings:
        return self.database.update_database(settings)