from core.models.database.beatmaps import Beatmap
from jays_tools import JsonCollection
from core.constants import BEATMAPS

class BeatmapRepository:
    def __init__(self) -> None:
        self.collection = JsonCollection(
            path=BEATMAPS, 
            model=Beatmap
        )
    
    def add(self, md5: str, beatmap: Beatmap) -> Beatmap:
        return self.collection.create(md5, beatmap)

    def get(self, md5: str) -> Beatmap | None:
        if not self.collection.exists(md5):
            return None

        database = self.collection.get(md5)

        return database.get_database()
    
    def get_all(self) -> dict[str, Beatmap]:
        return self.collection.get_all()
    
    def delete(self, md5: str) -> None:
        self.collection.delete(md5)

    def update(self, md5: str, beatmap: Beatmap) -> Beatmap:
        return self.collection.update(md5, beatmap)