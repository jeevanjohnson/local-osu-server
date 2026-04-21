import functools
import re
from core.models.database.beatmaps import Beatmap
import core.usecases.domain.beatmap as beatmap_usecases
import core.usecases.adapters.osufile as osufile_usecases
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

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
) -> Beatmap | None:
    original_beatmap_id = beatmap_usecases.get_id_by_filename(filename)
    if original_beatmap_id is None:
        return None

    original_md5 = beatmap_usecases.get_md5_by_id(original_beatmap_id)
    if original_md5 is None:
        return None

    original_beatmap = beatmap_usecases.get_by_md5_database(original_md5)
    if original_beatmap is None:
        original_beatmap = await beatmap_usecases.get_by_md5_api(original_md5)
        if original_beatmap is None:
            return None
    
    difficulty_adjusted_map_path = beatmap_usecases.get_path_by_md5(md5)
    if difficulty_adjusted_map_path is None:
        return None

    version = osufile_usecases.get_version(difficulty_adjusted_map_path)
    attributes = osufile_usecases.get_difficulty_attributes(difficulty_adjusted_map_path)
    object_count = osufile_usecases.get_object_count(difficulty_adjusted_map_path)
    drain_time_seconds = osufile_usecases.get_drain_time_seconds(difficulty_adjusted_map_path)

    
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

    # check if its in db
    beatmap = beatmap_usecases.get_by_md5_database(md5)
    if beatmap:
        return BeatmapResult(
            beatmap=beatmap, 
            status=BeatmapStatus.VALID
        )

    # check if its in api
    beatmap = await beatmap_usecases.get_by_md5_api(md5)

    if beatmap:
        beatmap_usecases.add(md5, beatmap)
        return BeatmapResult(
            beatmap=beatmap,
            status=BeatmapStatus.VALID
        )
    
    # if its a difficulty adjusted map, try to find the original map and add it as a difficulty adjusted copy
    if valid_difficulty_adjusted_filename(filename):
        beatmap = await get_difficulty_adjusted_beatmap(filename, md5)
        if beatmap:
            return BeatmapResult(
                beatmap=beatmap,
                status=BeatmapStatus.VALID
            )

    # check if its unsubmitted
    osu_file = beatmap_usecases.get_path_by_md5(md5)
    if osu_file is None:
        return BeatmapResult(
            beatmap=None,
            status=BeatmapStatus.UNSUBMITTED
        )

    beatmap_id = osufile_usecases.get_beatmap_id(osu_file)
    beatmap_set_id = osufile_usecases.get_beatmap_set_id(osu_file)

    if beatmap_id == 0 or beatmap_set_id == 0:
        return BeatmapResult(
            beatmap=None,
            status=BeatmapStatus.UNSUBMITTED
        )
    
    if valid_difficulty_adjusted_filename(filename):
        return BeatmapResult(
            beatmap=None,
            status=BeatmapStatus.UNSUBMITTED
        )
    else:
        # a valid beatmap and set id exists, so map is probably outdated and needs to be updated 
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
