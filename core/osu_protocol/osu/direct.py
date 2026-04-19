from dataclasses import dataclass
from datetime import datetime

import ossapi.enums
import ossapi.models

from models.domain.gameplay import osuGameMode

DIRECT_DIFF_FORMAT = (
    "[{difficulty:.2f}⭐] {version} {{CS{cs} OD{accuracy} AR{ar} HP{drain}}}@{mode_int}"
)

DIRECT_SET_FORMAT = (
    "{id}.osz|{artist}|{title}|{creator}|"
    "{ranked}|10.0|{last_updated}|{id}|"
    "0|{has_video}|{has_story}|0|0|{diffs}"
    # 0s are threadid, has_vid, has_story, filesize, filesize_novid
)


@dataclass
class DirectBeatmap:
    star_rating: float
    difficulty_name: str
    cs: float
    od: float
    ar: float
    hp: float
    mode: osuGameMode

    def serialize(self) -> str:
        return DIRECT_DIFF_FORMAT.format(
            difficulty=self.star_rating,
            version=self.difficulty_name,
            cs=self.cs,
            accuracy=self.od,
            ar=self.ar,
            drain=self.hp,
            mode_int=self.mode.value,
        )


@dataclass
class DirectBeatmapSet:
    id: int
    artist: str
    title: str
    creator: str
    has_video: bool
    has_story: bool
    last_updated: datetime  # utc timestamp
    status: ossapi.models.RankStatus
    maps: list[DirectBeatmap]

    def serialize(self) -> str:
        diffs = ",".join(
            bmap.serialize() for bmap in sorted(self.maps, key=lambda b: b.star_rating)
        )
        return DIRECT_SET_FORMAT.format(
            id=self.id,
            artist=self.artist,
            title=self.title,
            creator=self.creator,
            ranked=self.status.value,
            last_updated=int(self.last_updated.timestamp()),
            has_video=int(self.has_video),
            has_story=int(self.has_story),
            diffs=diffs,
        )


@dataclass
class DirectSearchResult:
    beatmap_sets: list[DirectBeatmapSet]

    def serialize(self) -> bytes:
        count = len(self.beatmap_sets)
        header = "101" if count == 50 else str(count)
        rows = [header] + [bmap_set.serialize() for bmap_set in self.beatmap_sets]
        return "\n".join(rows).encode()


class osuRankedStatus:
    ALL = 4
    RANKED = 0
    RANKED_PLAYED = 7
    LOVED = 8
    QUALIFIED = 3
    PENDING = 2
    GRAVEYARD = 5


def osu_direct_ranked_status_to_osu_api_v2(
    ranked_status: int,
) -> ossapi.enums.BeatmapsetSearchCategory:
    try:
        return {
            osuRankedStatus.ALL: ossapi.enums.BeatmapsetSearchCategory.ANY,
            osuRankedStatus.RANKED: ossapi.enums.BeatmapsetSearchCategory.RANKED,
            osuRankedStatus.RANKED_PLAYED: ossapi.enums.BeatmapsetSearchCategory.RANKED,
            osuRankedStatus.LOVED: ossapi.enums.BeatmapsetSearchCategory.LOVED,
            osuRankedStatus.QUALIFIED: ossapi.enums.BeatmapsetSearchCategory.QUALIFIED,
            osuRankedStatus.PENDING: ossapi.enums.BeatmapsetSearchCategory.PENDING,
            osuRankedStatus.GRAVEYARD: ossapi.enums.BeatmapsetSearchCategory.GRAVEYARD,
        }[ranked_status]
    except KeyError as e:
        # # log.error(
        #     f"Received unknown ranked status {ranked_status} in osu-direct request, defaulting to ranked"
        # )
        raise e


def osu_direct_mode_to_osu_api_v2(mode: int) -> ossapi.enums.BeatmapsetSearchMode:
    return {
        -1: ossapi.enums.BeatmapsetSearchMode.ANY,
        0: ossapi.enums.BeatmapsetSearchMode.OSU,
        1: ossapi.enums.BeatmapsetSearchMode.TAIKO,
        2: ossapi.enums.BeatmapsetSearchMode.CATCH,
        3: ossapi.enums.BeatmapsetSearchMode.MANIA,
    }[mode]
