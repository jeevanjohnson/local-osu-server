from datetime import datetime

from core.repositories.beatmaps import BeatmapRepository
from core.repositories.osu_file_location import OsuFileLocationRepository
from core.models.database.beatmaps import Beatmap
import core.usecases.domain.osu_api as osu_api_usecases
from core.models.domain.gameplay.game_mode import GameMode
from core.models.domain.gameplay.rank_status import RankStatus
from pathlib import Path
import core.usecases.adapters.osufile as osufile_usecases

def get_path_by_md5(md5: str) -> Path | None:
    """Get the file path of a beatmap by its MD5 hash."""
    osu_file_location_repo = OsuFileLocationRepository()
    database = osu_file_location_repo.get()

    return database.by_md5.get(md5)

# Retriving MD5
def get_md5_by_filename(filename: str) -> str | None:
    """Get the MD5 hash of a beatmap by its filename."""
    osu_file_location_repo = OsuFileLocationRepository()
    database = osu_file_location_repo.get()

    path = database.by_filename.get(filename)
    if path is None:
        return None

    return database.path_to_md5.get(path)

def get_md5_by_id(beatmap_id: int) -> str | None:
    osu_file_location_repo = OsuFileLocationRepository()
    database = osu_file_location_repo.get()

    path = database.by_id.get(beatmap_id)
    if path is None:
        return None
    
    return database.path_to_md5.get(path)

# Retrieving ID
def get_id_by_md5(md5: str) -> int | None:
    osu_file_location_repo = OsuFileLocationRepository()
    database = osu_file_location_repo.get()

    path = database.by_md5.get(md5)
    if path is None:
        return None
    
    return database.path_to_id.get(path)

def get_id_by_filename(filename: str) -> int | None:
    osu_file_location_repo = OsuFileLocationRepository()
    database = osu_file_location_repo.get()

    path = database.by_filename.get(filename)
    if path is None:
        return None
    
    return database.path_to_id.get(path)

# Retrieving Beatmap
def get_by_md5_database(md5: str) -> Beatmap | None:
    beatmap_repo = BeatmapRepository()
    return beatmap_repo.get(md5)

async def get_by_md5_api(md5: str) -> Beatmap | None:
    api_client = osu_api_usecases.get_api_client()

    try:
        api_beatmap = await api_client.beatmap(checksum=md5)
    except ValueError:
        return None

    beatmap_set = api_beatmap.beatmapset()

    path = get_path_by_md5(md5)
    if path is None:
        return None
    
    object_count = osufile_usecases.get_object_count(path)
    drain_time_seconds = osufile_usecases.get_drain_time_seconds(path)

    return Beatmap(
        md5=md5,
        osu_id=api_beatmap.id,
        osu_set_id=api_beatmap.beatmapset_id,
        artist=beatmap_set.artist,
        title=beatmap_set.title,
        version=api_beatmap.version,
        difficulty_adjusted=False,
        original_beatmap_md5=md5,
        max_combo=api_beatmap.max_combo or 0,
        mode=GameMode.from_api_v2(api_beatmap.mode),
        status=RankStatus.from_api_v2(api_beatmap.status),
        status_override={},
        ar=api_beatmap.ar,
        cs=api_beatmap.cs,
        hp=api_beatmap.drain,
        od=api_beatmap.accuracy,
        object_count=object_count,
        drain_time_seconds=drain_time_seconds,
        play_count=api_beatmap.playcount,
        pass_count=api_beatmap.passcount,
        pass_count_timestamp=datetime.now(),
        play_count_timestamp=datetime.now()
    )

# Building beatmap
def add(md5: str, beatmap: Beatmap) -> Beatmap:
    beatmap_repo = BeatmapRepository()
    return beatmap_repo.add(md5, beatmap)

def update(md5: str, beatmap: Beatmap) -> Beatmap:
    beatmap_repo = BeatmapRepository()
    return beatmap_repo.update(md5, beatmap)

def delete(md5: str) -> None:
    beatmap_repo = BeatmapRepository()
    beatmap_repo.delete(md5)