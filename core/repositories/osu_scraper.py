from core.models.database.osu_scraper import OsuScraperState
from jays_tools import JsonDatabase
from core.constants import OSU_SCRAPER_STATE

class OsuScraperRepository:
    def __init__(self) -> None:
        self.db = JsonDatabase(
            path=OSU_SCRAPER_STATE,
            database_model=OsuScraperState,
        )

    def get_state(self) -> OsuScraperState:
        """Get the current state of the osu! scraper."""
        return self.db.get_database()

    def update_state(self, state: OsuScraperState) -> OsuScraperState:
        """Update the state of the osu! scraper."""
        return self.db.update_database(state)