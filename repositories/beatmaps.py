from jays_tools import JsonDatabase

# from adapters import log_time
from constants.paths import BEATMAPS
from models.database.beatmaps import CurrentBeatmap as Beatmap
from models.database.beatmaps import CurrentBeatmaps as Beatmaps
from models.database.beatmaps import CurrentBeatmapSet as BeatmapSet


class BeatmapsRepository:
    def __init__(self) -> None:
        self.beatmaps = JsonDatabase(path=BEATMAPS, models=Beatmaps)

    # log
    async def from_md5(self, md5: str) -> Beatmap | None:
        async with self.beatmaps as beatmaps:
            if md5 not in beatmaps.all["by_md5"]:
                return None

            return beatmaps.all["by_md5"][md5]

    async def from_id(self, id: int) -> Beatmap | None:
        async with self.beatmaps as beatmaps:
            if id not in beatmaps.all["by_id"]:
                return None

            return beatmaps.all["by_id"][id]

    async def from_set_id(self, set_id: int) -> BeatmapSet | None:
        async with self.beatmaps as beatmaps:
            if set_id not in beatmaps.all["by_set_id"]:
                return None

            return beatmaps.all["by_set_id"][set_id]

    # log
    async def insert_beatmap(self, bmap: Beatmap) -> None:
        async with self.beatmaps as beatmaps:
            beatmaps.all["by_id"][bmap.id] = bmap
            beatmaps.all["by_md5"][bmap.md5] = bmap

            self.beatmaps.set(beatmaps)

    # log
    async def insert_beatmap_set(self, beatmap_set: BeatmapSet) -> None:
        async with self.beatmaps as beatmaps:
            beatmaps.all["by_set_id"][beatmap_set.id] = beatmap_set

            for beatmap in beatmap_set.maps:
                beatmaps.all["by_id"][beatmap.id] = beatmap
                beatmaps.all["by_md5"][beatmap.md5] = beatmap

            self.beatmaps.set(beatmaps)

    # log
    async def delete_beatmap(self, beatmap: Beatmap) -> None:
        async with self.beatmaps as beatmaps:
            beatmaps.all["by_id"].pop(beatmap.id, None)
            beatmaps.all["by_md5"].pop(beatmap.md5, None)

            existing_set = beatmaps.all["by_set_id"].get(beatmap.set_id)
            if existing_set is not None:
                remaining_maps = [b for b in existing_set.maps if b.md5 != beatmap.md5]
                if remaining_maps:
                    existing_set.maps = remaining_maps
                    beatmaps.all["by_set_id"][beatmap.set_id] = existing_set
                else:
                    beatmaps.all["by_set_id"].pop(beatmap.set_id, None)

            self.beatmaps.set(beatmaps)
