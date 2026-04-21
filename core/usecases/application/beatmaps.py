import functools
import re
from core.models.database.beatmaps import Beatmap
import core.usecases.domain.beatmap as beatmap_usecases
import core.usecases.adapters.osufile as osufile_usecases
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

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

async def get_difficulty_adjusted_beatmap(
    filename: str,
    md5: str,
    difficulty_adjusted_osu_file_location: Path,
) -> Beatmap | None:
    print(f"[DIFFICULTY_ADJUSTED] Processing: {filename} (md5: {md5})")
    
    original_beatmap_id = beatmap_usecases.get_id_by_filename(filename)
    if original_beatmap_id is None:
        print(f"[DIFFICULTY_ADJUSTED] FAILED: Could not find original beatmap ID for filename: {filename}")
        return None
    print(f"[DIFFICULTY_ADJUSTED] Found original beatmap ID: {original_beatmap_id}")

    original_md5 = beatmap_usecases.get_md5_by_id(original_beatmap_id)
    if original_md5 is None:
        print(f"[DIFFICULTY_ADJUSTED] FAILED: Could not find MD5 for beatmap ID: {original_beatmap_id}")
        return None
    print(f"[DIFFICULTY_ADJUSTED] Found original MD5: {original_md5}")

    original_beatmap = beatmap_usecases.get_by_md5_database(original_md5)
    if original_beatmap is None:
        print(f"[DIFFICULTY_ADJUSTED] Not in DB, fetching from API: {original_md5}")
        original_beatmap = await beatmap_usecases.get_by_md5_api(original_md5)
        if original_beatmap is None:
            print(f"[DIFFICULTY_ADJUSTED] FAILED: Could not fetch original beatmap from API: {original_md5}")
            return None
    print(f"[DIFFICULTY_ADJUSTED] Successfully loaded original beatmap: {original_beatmap.artist} - {original_beatmap.title}")

    version = osufile_usecases.get_version(difficulty_adjusted_osu_file_location)
    attributes = osufile_usecases.get_difficulty_attributes(difficulty_adjusted_osu_file_location)
    object_count = osufile_usecases.get_object_count(difficulty_adjusted_osu_file_location)
    drain_time_seconds = osufile_usecases.get_drain_time_seconds(difficulty_adjusted_osu_file_location)
    
    print(f"[DIFFICULTY_ADJUSTED] Extracted attributes - AR: {attributes['ar']}, CS: {attributes['cs']}, HP: {attributes['hp']}, OD: {attributes['od']}")
    
    beatmap = beatmap_usecases.add(
        md5,
        Beatmap(
            md5=md5,
            osu_id=original_beatmap.osu_id,
            osu_set_id=original_beatmap.osu_set_id,
            artist=original_beatmap.artist,
            title=original_beatmap.title,
            version=version,
            difficulty_adjusted=True,
            original_beatmap_md5=original_md5,
            max_combo=original_beatmap.max_combo,
            mode=original_beatmap.mode,
            status=original_beatmap.status,
            status_override=original_beatmap.status_override,
            ar=attributes["ar"],
            cs=attributes["cs"],
            hp=attributes["hp"],
            od=attributes["od"],
            object_count=object_count,
            drain_time_seconds=drain_time_seconds,
            play_count=original_beatmap.play_count,
            pass_count=original_beatmap.pass_count,
            pass_count_timestamp=original_beatmap.pass_count_timestamp,
            play_count_timestamp=original_beatmap.play_count_timestamp
        )
    )
    
    print(f"[DIFFICULTY_ADJUSTED] Successfully created difficulty adjusted beatmap: {beatmap.artist} - {beatmap.title} [{beatmap.version}]")

    return beatmap

class BeatmapStatus(Enum):
    VALID = "valid"
    UNSUBMITTED = "unsubmitted"
    NEEDS_UPDATE = "needs_update"

@dataclass
class BeatmapResult:
    beatmap: Beatmap | None
    status: BeatmapStatus

async def from_leaderboard_request(
    filename: str,
    md5: str,
) -> BeatmapResult:
    """Fetch beatmap based on leaderboard request data."""
    import time
    start = time.time()
    
    # check if its in db
    t0 = time.time()
    beatmap = beatmap_usecases.get_by_md5_database(md5)
    if beatmap:
        print(f"[LOOKUP] DB hit in {(time.time()-t0)*1000:.2f}ms")
        return BeatmapResult(
            beatmap=beatmap, 
            status=BeatmapStatus.VALID
        )
    print(f"[LOOKUP] DB check: {(time.time()-t0)*1000:.2f}ms (miss)")

    t0 = time.time()
    osu_file = beatmap_usecases.get_path_by_md5(md5)
    print(f"[LOOKUP] File path lookup: {(time.time()-t0)*1000:.2f}ms")

    # if its a difficulty adjusted map, try to find the original map and add it as a difficulty adjusted copy
    t0 = time.time()
    if valid_difficulty_adjusted_filename(filename) and osu_file is not None:
        beatmap = await get_difficulty_adjusted_beatmap(filename, md5, osu_file)
        if beatmap:
            print(f"[LOOKUP] Difficulty adjusted found in {(time.time()-t0)*1000:.2f}ms")
            return BeatmapResult(
                beatmap=beatmap,
                status=BeatmapStatus.VALID
            )
    print(f"[LOOKUP] Difficulty adjusted check: {(time.time()-t0)*1000:.2f}ms")

    # check if its in api
    t0 = time.time()
    beatmap = await beatmap_usecases.get_by_md5_api(md5, osu_file_location=osu_file)
    print(f"[LOOKUP] API check: {(time.time()-t0)*1000:.2f}ms")

    if beatmap:
        beatmap_usecases.add(md5, beatmap)
        return BeatmapResult(
            beatmap=beatmap,
            status=BeatmapStatus.VALID
        )

    # check if its unsubmitted
    t0 = time.time()
    osu_file = beatmap_usecases.get_path_by_md5(md5)
    print(f"[LOOKUP] File lookup: {(time.time()-t0)*1000:.2f}ms")
    if osu_file is None:
        print(f"[LOOKUP] Total: {(time.time()-start)*1000:.2f}ms - UNSUBMITTED")
        return BeatmapResult(
            beatmap=None,
            status=BeatmapStatus.UNSUBMITTED
        )

    t0 = time.time()
    beatmap_id = osufile_usecases.get_beatmap_id(osu_file)
    beatmap_set_id = osufile_usecases.get_beatmap_set_id(osu_file)
    print(f"[LOOKUP] Parse .osu file: {(time.time()-t0)*1000:.2f}ms")

    if beatmap_id == 0 or beatmap_set_id == 0:
        print(f"[LOOKUP] Total: {(time.time()-start)*1000:.2f}ms - UNSUBMITTED (no id)")
        return BeatmapResult(
            beatmap=None,
            status=BeatmapStatus.UNSUBMITTED
        )
    
    if valid_difficulty_adjusted_filename(filename):
        print(f"[LOOKUP] Total: {(time.time()-start)*1000:.2f}ms - UNSUBMITTED (difficulty adjusted)")
        return BeatmapResult(
            beatmap=None,
            status=BeatmapStatus.UNSUBMITTED
        )
    else:
        # a valid beatmap and set id exists, so map is probably outdated and needs to be updated 
        print(f"[LOOKUP] Total: {(time.time()-start)*1000:.2f}ms - NEEDS_UPDATE")
        return BeatmapResult(
            beatmap=None,
            status=BeatmapStatus.NEEDS_UPDATE
        )

async def get_pass_count(beatmap: Beatmap) -> int:
    # only update pass count if its been a day
    day = timedelta(days=1).total_seconds()

    if datetime.now().timestamp() - beatmap.pass_count_timestamp.timestamp() < day:
        return beatmap.pass_count

    try:
        beatmap_info = await beatmap_usecases.get_by_md5_api(beatmap.md5)
    except ValueError:
        return beatmap.pass_count

    if beatmap_info is None:
        return beatmap.pass_count

    beatmap.pass_count = beatmap_info.pass_count
    beatmap.pass_count_timestamp = datetime.now()

    updated_beatmap = beatmap_usecases.update(beatmap.md5, beatmap)

    return updated_beatmap.pass_count
