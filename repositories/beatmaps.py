from pathlib import Path

from jays_tools import JsonDatabase

from models.database.beatmaps import CurrentBeatmap as Beatmap
from models.database.beatmaps import CurrentBeatmaps as Beatmaps
from models.database.beatmaps import CurrentBeatmapSet as BeatmapSet


# TODO: Async?
class BeatmapsRepository:
    def __init__(self, path: Path) -> None:
        self.beatmaps = JsonDatabase(path=path, models=Beatmaps)

    def get_by_md5(self, md5: str) -> Beatmap | None:
        with self.beatmaps as beatmaps:
            if md5 not in beatmaps.all["by_md5"]:
                return None

            return beatmaps.all["by_md5"][md5]

    def get_by_id(self, id: int) -> Beatmap | None:
        with self.beatmaps as beatmaps:
            if id not in beatmaps.all["by_id"]:
                return None

            return beatmaps.all["by_id"][id]

    def get_by_set_id(self, set_id: int) -> BeatmapSet | None:
        with self.beatmaps as beatmaps:
            if set_id not in beatmaps.all["by_set_id"]:
                return None

            return beatmaps.all["by_set_id"][set_id]

    def insert_beatmap(self, bmap: Beatmap) -> None:
        with self.beatmaps as beatmaps:
            beatmaps.all["by_id"][bmap.id] = bmap
            beatmaps.all["by_md5"][bmap.md5] = bmap

            self.beatmaps.set(beatmaps)

    def insert_beatmap_set(self, beatmap_set: BeatmapSet) -> None:
        with self.beatmaps as beatmaps:
            beatmaps.all["by_set_id"][beatmap_set.id] = beatmap_set

            self.beatmaps.set(beatmaps)
