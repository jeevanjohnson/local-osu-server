from datetime import datetime, timedelta
import time
import re
import functools

from core.repositories.beatmaps import BeatmapRepository
from core.repositories.osu_file_locations import OsuFileLocationRepository
from core.models.adapters.database.beatmaps import Beatmap
import core.usecases.osu_api as osu_api_usecases
from core.models.domain.gameplay.game_mode import GameMode
from core.models.domain.gameplay.rank_status import RankStatus
from pathlib import Path
import core.usecases.adapters.osufile as osufile_usecases

FILENAME_REGEX = re.compile(
    r"(?P<artist>.*) - (?P<song_name>.*) ((?P<mapper>.*) \[)(?P<diff_name>.*)\]\.osu"
)
DIFFICULTY_ADJUSTED_REGEX = re.compile(
    r"(?P<rate>[0-9]{1,2}(?:\.[0-9]{1,2})?x) \((?P<bpm>[0-9]+bpm)\)"
)
ATTRIBUTE_EDIT_REGEX = re.compile(r"(.*) (HP|CS|AR|OD)([0-9]{1,2}(?:\.[0-9]{1,2})?)")

@functools.cache
def valid_difficulty_adjusted_filename(filename: str) -> bool:
    """
    Checks if the filename matches a difficulty-adjusted pattern.
    Time Complexity: O(1) (regex search on a short string)
    """
    file_name_data = FILENAME_REGEX.search(filename)
    if not file_name_data:
        return False

    difficulty_name = file_name_data["diff_name"]
    if not difficulty_name:
        return False

    has_rate_adjust = bool(DIFFICULTY_ADJUSTED_REGEX.search(difficulty_name))
    has_attribute_adjust = bool(ATTRIBUTE_EDIT_REGEX.search(difficulty_name))

    # Accept either type of adjustment: rate-only (e.g. 0.89x (240bpm))
    # or explicit stat edits (AR/CS/HP/OD).
    return has_rate_adjust or has_attribute_adjust

def get_path_by_md5(md5: str) -> Path | None:
    """Get the file path of a beatmap by its MD5 hash."""
    t0 = time.time()
    osu_file_location_repo = OsuFileLocationRepository()
    t1 = time.time()
    database = osu_file_location_repo.get()
    t2 = time.time()
    result = database.by_md5.get(md5)
    t3 = time.time()
    
    print(f"[PERF] get_path_by_md5: repo init {(t1-t0)*1000:.2f}ms, get() {(t2-t1)*1000:.2f}ms, lookup {(t3-t2)*1000:.2f}ms, total {(t3-t0)*1000:.2f}ms")
    return result

# Retriving MD5
def get_md5_by_filename(filename: str) -> str | None:
    """Get the MD5 hash of a beatmap by its filename."""
    osu_file_location_repo = OsuFileLocationRepository()
    database = osu_file_location_repo.get()

    path = database.by_filename.get(filename)
    if path is None:
        return None

    return database.path_to_md5.get(path)

def get_md5_by_id(beatmap_id: int, original_map: bool = True) -> str | None:
    osu_file_location_repo = OsuFileLocationRepository()
    database = osu_file_location_repo.get()

    paths = database.by_id.get(beatmap_id)
    if paths is None:
        return None
    
    if not original_map:
        raise NotImplementedError("Difficulty adjusted map lookup by ID is not implemented yet")

    final_path: Path | None = None
    for path in paths:
        if valid_difficulty_adjusted_filename(path.name):
            continue
        
        final_path = path
        break
    
    if final_path is None:
        return None
    
    return database.path_to_md5.get(final_path)

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

async def get_by_md5_api(md5: str, osu_file_location: Path | None = None) -> Beatmap | None:
    api_client = osu_api_usecases.get_api_client()

    try:
        api_beatmap = await api_client.beatmap(checksum=md5)
    except ValueError:
        return None

    beatmap_set = api_beatmap.beatmapset()

    # Use provided path if available, otherwise look it up
    path = osu_file_location or get_path_by_md5(md5)
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
        play_count_timestamp=datetime.now(),
        last_updated=api_beatmap.last_updated,
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

async def get_pass_count(beatmap: Beatmap) -> int:
    # only update pass count if its been a day
    day = timedelta(days=1).total_seconds()

    if datetime.now().timestamp() - beatmap.pass_count_timestamp.timestamp() < day:
        return beatmap.pass_count

    try:
        beatmap_info = await get_by_md5_api(beatmap.md5)
    except ValueError:
        return beatmap.pass_count

    if beatmap_info is None:
        return beatmap.pass_count

    beatmap.pass_count = beatmap_info.pass_count
    beatmap.pass_count_timestamp = datetime.now()

    beatmap.last_updated = beatmap_info.last_updated

    updated_beatmap = update(beatmap.md5, beatmap)

    return updated_beatmap.pass_count