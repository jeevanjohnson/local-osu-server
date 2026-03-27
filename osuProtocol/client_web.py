from base64 import b64decode
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum, unique
from typing import TYPE_CHECKING

import ossapi.enums
import ossapi.models
from fastapi.datastructures import FormData
from py3rijndael import Pkcs7Padding, RijndaelCbc
from pydantic import BaseModel, ConfigDict
from starlette.datastructures import UploadFile as StarletteUploadFile

# from adapters import log
from models.bancho.scores import LazerScore, Score, StableScore
from models.database.scores import (
    CurrentScore as ProfileScore,
)
from models.domain.gameplay import Mods, osuGameMode, osuMods
from models.domain.scores import AcceptedScores, AllScores, ScoringAlgorithm
from osuProtocol.server_packets import osuGameMode

if TYPE_CHECKING:
    from models.database.beatmaps import CurrentBeatmap as Beatmap


@unique
class osuMapStatus(IntEnum):
    """
    Represents the ranked status of a beatmap.
    """

    NOT_SUBMITTED = -1
    PENDING = 0
    UPDATE_AVAILABLE = 1
    RANKED = 2
    APPROVED = 3
    QUALIFIED = 4
    LOVED = 5

    @property
    def permanent(self) -> bool:
        return self in {
            osuMapStatus.RANKED,
            osuMapStatus.APPROVED,
            osuMapStatus.LOVED,
        }

    def ranked(self) -> bool:
        return self in {
            osuMapStatus.RANKED,
            osuMapStatus.APPROVED,
        }

    def has_leaderboard(self) -> bool:
        return self in {
            osuMapStatus.RANKED,
            osuMapStatus.APPROVED,
            osuMapStatus.QUALIFIED,
            osuMapStatus.LOVED,
        }

    @classmethod
    def from_api_v2(cls, ranked_status: ossapi.enums.RankStatus) -> "osuMapStatus":
        return {
            ossapi.enums.RankStatus.GRAVEYARD: cls.PENDING,
            ossapi.enums.RankStatus.WIP: cls.PENDING,
            ossapi.enums.RankStatus.PENDING: cls.PENDING,
            ossapi.enums.RankStatus.RANKED: cls.RANKED,
            ossapi.enums.RankStatus.APPROVED: cls.APPROVED,
            ossapi.enums.RankStatus.QUALIFIED: cls.QUALIFIED,
            ossapi.enums.RankStatus.LOVED: cls.LOVED,
        }[ranked_status]

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()


@unique
class LeaderboardType(IntEnum):
    """
    Types of leaderboards that can be requested.
    """

    LOCAL = 0
    TOP = 1
    MODS = 2
    FRIENDS = 3
    COUNTRY = 4


LEADERBOARD_SCORE_FMT = (
    "{id}|{name}|{score}|{max_combo}|"
    "{n50}|{n100}|{n300}|{nmiss}|{nkatu}|{ngeki}|"
    "{perfect}|{mods}|{userid}|{rank}|{time}|{has_replay}"
)

EpochTime = int


@dataclass
class LeaderboardScore:
    """
    Represents a single score on the leaderboard.
    """

    score_id: int
    username: str
    score: int
    max_combo: int
    count50: int
    count100: int
    count300: int
    count_miss: int
    countkatu: int
    countgeki: int
    perfect: bool
    enabled_mods: osuMods
    user_id: int
    position: int
    time_set: EpochTime
    replay_available: bool

    def serialize(self) -> str:
        return LEADERBOARD_SCORE_FMT.format(
            id=self.score_id,
            name=self.username,
            score=self.score,
            max_combo=self.max_combo,
            n50=self.count50,
            n100=self.count100,
            n300=self.count300,
            nmiss=self.count_miss,
            nkatu=self.countkatu,
            ngeki=self.countgeki,
            perfect=int(self.perfect),
            mods=self.enabled_mods,
            userid=self.user_id,
            rank=self.position,
            time=self.time_set,
            has_replay=int(self.replay_available),
        )

    def __repr__(self) -> str:
        return self.serialize()

    @classmethod
    def from_score(
        cls,
        score: Score | ProfileScore,
        position: int,
        ingame_score: int,
        from_difficulty_adjusted: bool = False,
        truncate_username: bool = False,
    ) -> "LeaderboardScore":
        stable_mods, lazer_mods = score.enabled_mods.to_stable_mods()
        has_lazer_rate_change = any(m.endswith("x") for m in lazer_mods)

        if isinstance(score, LazerScore):
            title = f"[LAZER] {score.username}"

            total_lazer_mods = len(lazer_mods)

            if lazer_mods:
                title += " ("

                for i, lazer_mod in enumerate(lazer_mods):
                    if lazer_mod == "DA":
                        continue

                    if lazer_mod.endswith("x"):  # Rate change
                        # remove any rate changing mod
                        # so more space can be given to lazer-exclusive mods in the title
                        stable_mods = (
                            stable_mods
                            & ~osuMods.DOUBLETIME
                            & ~osuMods.HALFTIME
                            & ~osuMods.NIGHTCORE
                        )

                        if float(lazer_mod[:-1]) < 1.0:
                            lazer_mod = lazer_mod.replace("0.", ".", count=1)

                    if i == total_lazer_mods - 1:
                        title += lazer_mod
                    else:
                        title += lazer_mod + ","

                title += ")"
        else:
            title = score.username

        if "NC" in score.enabled_mods:
            # Client needs this in order to actual speed up the
            # replay properly
            stable_mods |= osuMods.DOUBLETIME

            if isinstance(score, LazerScore):
                stable_mods |= osuMods.NIGHTCORE

        if from_difficulty_adjusted and not isinstance(score, ProfileScore):
            # https://capitalizemytitle.com/small-text-converter/
            title = f"[ᵒᵍ ᵈⁱᶠᶠ] {title}"

            stable_mods = (
                stable_mods
                & ~osuMods.DOUBLETIME
                & ~osuMods.HALFTIME
                & ~osuMods.NIGHTCORE
            )

            if isinstance(score, StableScore):
                if "DT" in score.enabled_mods or "NC" in score.enabled_mods:
                    title += " (1.5x)"
                elif "HT" in score.enabled_mods or "DC" in score.enabled_mods:
                    title += " (.75x)"
                else:
                    title += " (1x)"
            elif isinstance(score, LazerScore):
                if not has_lazer_rate_change:
                    if "DT" in score.enabled_mods or "NC" in score.enabled_mods:
                        title += " (1.5x)"
                    elif "HT" in score.enabled_mods or "DC" in score.enabled_mods:
                        title += " (.75x)"
                    else:
                        title += " (1x)"

        if truncate_username and len(title) > 15 + 3:  # 15 chars + 3 for "..."
            title = title[:15] + "..."  # Truncate username to 20 characters

        if isinstance(score, ProfileScore):
            score_id = -score.id
            max_combo = score.combo
            user_id = 2
            replay_available = score.replay_frames is not None
        else:
            user_id = score.user_id
            score_id = score.score_id
            max_combo = score.combo.actual
            replay_available = score.replay_available

        if not stable_mods & osuMods.SCOREV2:
            if not isinstance(score, ProfileScore):
                # This allows watching replays
                # and playing w/ score v2 making the
                # ranking up the map feel with the lb on more
                # realistic to bancho/lazer
                stable_mods |= osuMods.SCOREV2
            else:
                # TODO: profile setting?
                # cause when you actually play the map the side leaderboards
                # you just become number 1 cause client will calculate score
                # by legacy algorithm instead of score v2, which is what the profile scores are stored with
                # & the replay's acc will be off cause of slider acc
                pass

        return cls(
            score_id=score_id,
            username=title,
            score=ingame_score,
            max_combo=max_combo,
            count50=score.count50,
            count100=score.count100,
            count300=score.count300,
            count_miss=score.count_miss,
            countkatu=0,
            countgeki=0,
            perfect=score.perfect,
            enabled_mods=stable_mods,
            user_id=user_id,
            position=position,
            time_set=score.time_set,
            replay_available=replay_available,
        )


STARTING_LB_FORMAT = (
    "{beatmap_status}|false|{beatmap_id}|{beatmap_set_id}|{num_of_scores}\n0\n"
    "[bold:0,size:20]{artist_unicode}|{title_unicode}\n10.0\n"
)


@dataclass
class LeaderboardHeader:
    """
    Represents the header of a leaderboard, containing metadata about the leaderboard.
    """

    beatmap_status: osuMapStatus
    beatmap_id: int
    beatmap_set_id: int
    num_of_scores: int
    artist: str
    title: str

    def serialize(self) -> str:
        return STARTING_LB_FORMAT.format(
            beatmap_status=self.beatmap_status.value,
            beatmap_id=self.beatmap_id,
            beatmap_set_id=self.beatmap_set_id,
            num_of_scores=self.num_of_scores,
            artist_unicode=self.artist,
            title_unicode=self.title,
        )


class Leaderboard:
    """
    Represents a full leaderboard, including the header and the list of scores.
    """

    def __init__(
        self,
        header: LeaderboardHeader,
        scores: list[LeaderboardScore] | None = None,
        personal_best: LeaderboardScore | None = None,
    ):
        self.header = header

        if scores is None:
            self.scores = []
        else:
            self.scores = scores

        self.personal_best = personal_best

    def update_scores(self, new_scores: list[LeaderboardScore]):
        self.scores = new_scores

    def serialize(self) -> bytes:
        if isinstance(self.header.beatmap_status, bool):
            error_message = (
                f"Error: Beatmap status is a boolean value ({self.header.beatmap_status}). This is likely a bug.\n"
                f"Beatmap ID: {self.header.beatmap_id}, Beatmap Set ID: {self.header.beatmap_set_id}\n"
                f"Artist: {self.header.artist}, Title: {self.header.title}"
            )
            raise ValueError(error_message)

        if self.header.beatmap_status < 1:
            return f"{self.header.beatmap_status.value}|false".encode()

        buffer = bytearray()

        buffer += self.header.serialize().encode()

        raw_personal_best = b"\n"
        if self.personal_best:
            raw_personal_best = self.personal_best.serialize().encode() + b"\n"

        buffer += raw_personal_best

        for score in self.scores:
            buffer += score.serialize().encode() + b"\n"

        return bytes(buffer)


class LeaderboardWithScores(Leaderboard):
    # # log
    def __init__(
        self,
        beatmap: "Beatmap",
        scores: AllScores,
        personal_best: ProfileScore | None,
        scoring_algorithm: ScoringAlgorithm,
        difficulty_adjusted: bool,
        limit: int,
        accepted_scores: AcceptedScores,
        profile_name: str,
    ) -> None:
        self.beatmap = beatmap
        self.scores = scores
        self.personal_best = personal_best
        self.scoring_algorithm = scoring_algorithm
        self.difficulty_adjusted = difficulty_adjusted
        self.limit = limit
        self.accepted_scores = accepted_scores
        self.profile_name = profile_name

        if self.personal_best is not None:
            if self.personal_best not in self.scores:
                self.scores.append(self.personal_best)

        self.scores.sort(self.scoring_algorithm)

    @property
    def play_count(self) -> int:
        return self.beatmap.play_count

    @property
    def pass_count(self) -> int:
        if self.beatmap.pass_count < 1:
            return 1

        return self.beatmap.pass_count

    def personal_best_position(self) -> int:
        if self.personal_best is None:
            return 0

        return self.scores.position_of_score(
            self.personal_best,
            self.scoring_algorithm,
            beatmap_pass_count=self.beatmap.pass_count,
            leaderboard_limit=self.limit,
        )

    def serialize_personal_best(self) -> LeaderboardScore | None:
        if self.personal_best is None:
            return None

        if (
            self.scoring_algorithm == ScoringAlgorithm.PP
            and self.beatmap.can_display_pp
        ):
            ingame_score = self.personal_best.performance_points or 0
        else:
            ingame_score = self.personal_best.total_score

        return LeaderboardScore.from_score(
            score=self.personal_best,
            position=self.personal_best_position(),
            ingame_score=ingame_score,
            from_difficulty_adjusted=self.difficulty_adjusted,
        )

    def serialize(self) -> bytes:
        leaderboard_header = LeaderboardHeader(
            beatmap_status=self.beatmap.status[self.profile_name],
            beatmap_id=self.beatmap.id,
            beatmap_set_id=self.beatmap.set_id,
            num_of_scores=self.beatmap.pass_count,
            artist=self.beatmap.artist,
            title=self.beatmap.title,
        )

        leaderboard = Leaderboard(
            header=leaderboard_header,
            personal_best=self.serialize_personal_best(),
        )

        leaderboard_scores = []

        seen_self = False
        for index, score in enumerate(self.scores[: self.limit]):
            if (
                self.scoring_algorithm == ScoringAlgorithm.PP
                and self.beatmap.can_display_pp
            ):
                ingame_score = score.performance_points or 0
            else:
                ingame_score = score.total_score

            if seen_self:
                score.username += " " * (index + 1)

            if score == self.personal_best:
                seen_self = True

            leaderboard_score = LeaderboardScore.from_score(
                score=score,
                position=index + 1,
                ingame_score=ingame_score,
                from_difficulty_adjusted=self.difficulty_adjusted,
            )
            leaderboard_scores.append(leaderboard_score)

        if not seen_self and leaderboard.personal_best:
            # if personal best not in top scores, calc its position
            # using interpolation
            leaderboard.personal_best.position = self.personal_best_position()

        leaderboard.scores = leaderboard_scores

        return leaderboard.serialize()


class GraveyardLeaderboard(Leaderboard):
    """
    Represents a leaderboard for beatmaps that are in the graveyard.
    """

    def __init__(self):
        super().__init__(
            LeaderboardHeader(
                beatmap_status=osuMapStatus.PENDING,
                beatmap_id=0,
                beatmap_set_id=0,
                num_of_scores=0,
                artist="",
                title="",
            ),
            [],
        )


class UpdateBeatmapRequestLeaderboard(Leaderboard):
    """
    Represents a leaderboard for beatmaps that have been updated.
    """

    def __init__(self):
        super().__init__(
            LeaderboardHeader(
                beatmap_status=osuMapStatus.UPDATE_AVAILABLE,
                beatmap_id=0,
                beatmap_set_id=0,
                num_of_scores=0,
                artist="",
                title="",
            ),
            [],
        )


class NotSubmittedLeaderboard(Leaderboard):
    """
    Represents a leaderboard for beatmaps that have not been submitted.
    """

    def __init__(self):
        super().__init__(
            LeaderboardHeader(
                beatmap_status=osuMapStatus.NOT_SUBMITTED,
                beatmap_id=0,
                beatmap_set_id=0,
                num_of_scores=0,
                artist="",
                title="",
            ),
            [],
        )


@dataclass
class Achievement:
    image_url: str
    title: str
    description: str

    def serialize(self) -> str:
        return f"{self.image_url}+{self.title}+{self.description}"


class Achievements(list[Achievement]):
    def serialize(self) -> str:
        return "/".join(achievement.serialize() for achievement in self)


@dataclass
class ChartColumn:
    name: str
    before: float | None = None
    after: float | None = None

    def serialize(self) -> str:
        return (
            f"{self.name}Before:{self.before or ''}|{self.name}After:{self.after or ''}"
        )


@dataclass
class Rank(ChartColumn):
    name: str = "rank"


@dataclass
class RankedScore(ChartColumn):
    name: str = "rankedScore"


@dataclass
class TotalScore(ChartColumn):
    name: str = "totalScore"


@dataclass
class MaxCombo(ChartColumn):
    name: str = "maxCombo"


@dataclass
class Accuracy(ChartColumn):
    name: str = "accuracy"


@dataclass
class PerformancePoints(ChartColumn):
    name: str = "pp"


@dataclass
class Chart:
    rank: Rank
    ranked_score: RankedScore
    total_score: TotalScore
    max_combo: MaxCombo
    accuracy: Accuracy
    pp: PerformancePoints

    def serialize(self) -> list[str]:
        return [
            self.rank.serialize(),
            self.ranked_score.serialize(),
            self.total_score.serialize(),
            self.max_combo.serialize(),
            self.accuracy.serialize(),
            self.pp.serialize(),
        ]


class BeatmapChart(Chart):
    pass


class OverallRankingChart(Chart):
    pass


@dataclass
class SubmissionCharts:
    beatmap_id: int
    beatmap_set_id: int
    beatmap_playcount: int
    beatmap_passcount: int
    last_updated: datetime
    score_id: int
    beatmap_chart: BeatmapChart
    overall_ranking_chart: OverallRankingChart
    achievements: Achievements

    @property
    def beatmap_url(self) -> str:
        return f"https://osu.ppy.sh/b/{self.beatmap_id}"

    @property
    def chart_url(self) -> str:
        # TODO: Redirect to GUI?
        return "https://osu.ppy.sh/u/2"

    def serialize(self) -> bytes:
        submission_charts = [
            f"beatmapId:{self.beatmap_id}",
            f"beatmapSetId:{self.beatmap_set_id}",
            f"beatmapPlaycount:{self.beatmap_playcount}",
            f"beatmapPasscount:{self.beatmap_passcount}",
            f"approvedDate:{self.last_updated}",
            "\n",
            # beatmap ranking chart
            "chartId:beatmap",
            f"chartUrl:{self.beatmap_url}",
            "chartName:Beatmap Ranking",
            *self.beatmap_chart.serialize(),
            f"onlineScoreId:{self.score_id}",
            "\n",
            # overall ranking chart
            "chartId:overall",
            f"chartUrl:{self.chart_url}",
            "chartName:Overall Ranking",
            *self.overall_ranking_chart.serialize(),
            f"achievements-new:{self.achievements.serialize()}",
        ]

        return "|".join(submission_charts).encode()


UNRANKED_CHARTS = SubmissionCharts(
    beatmap_id=0,
    beatmap_set_id=0,
    beatmap_playcount=0,
    beatmap_passcount=0,
    last_updated=datetime.now(),
    score_id=0,
    beatmap_chart=BeatmapChart(
        rank=Rank(name="rank"),
        ranked_score=RankedScore(name="rankedScore"),
        total_score=TotalScore(name="totalScore"),
        max_combo=MaxCombo(name="maxCombo"),
        accuracy=Accuracy(name="accuracy"),
        pp=PerformancePoints(name="pp"),
    ),
    overall_ranking_chart=OverallRankingChart(
        rank=Rank(name="rank"),
        ranked_score=RankedScore(name="rankedScore"),
        total_score=TotalScore(name="totalScore"),
        max_combo=MaxCombo(name="maxCombo"),
        accuracy=Accuracy(name="accuracy"),
        pp=PerformancePoints(name="pp"),
    ),
    achievements=Achievements(),
)

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


def parse_form_data(form_data: FormData) -> tuple[bytes, StarletteUploadFile] | None:
    try:
        score_parts = form_data.getlist("score")
        assert len(score_parts) == 2, "Expected exactly 2 score parts"

        score_data_b64 = score_parts[0]
        assert isinstance(score_data_b64, str), "Expected score data to be a string"

        score_replay_file = score_parts[1]
        assert isinstance(score_replay_file, StarletteUploadFile), (
            "Expected score replay file to be an UploadFile"
        )

        return score_data_b64.encode(), score_replay_file
    except (AssertionError, IndexError):
        return None


class ScoreData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    beatmap_md5: str
    username: str
    online_checksum: str
    count_300: int
    count_100: int
    count_50: int
    count_geki: int
    count_katu: int
    count_miss: int
    total_score: int
    max_combo: int
    perfect: bool
    grade: str
    mods: Mods
    passed: bool
    game_mode: osuGameMode
    play_time: datetime
    # Ignore client flags & version since we don't have a use for them
    # Although not parsing could cause issues?

    # @field_serializer("mods")
    # def serialize_mods(self, value: Mods) -> list[str]:
    #     return list(value)

    # @field_validator("mods", mode="before")
    # @classmethod
    # def deserialize_mods(cls, value: list[str]) -> Mods:
    #     return Mods(value)


def decrypt_score_aes_data(
    # to decode
    score_data_b64: bytes,
    client_hash_b64: bytes,
    # used for decoding
    iv_b64: bytes,
    osu_version: str,
) -> tuple[ScoreData, str]:
    """Decrypt the base64'ed score data."""

    # attempt to decrypt score data
    aes = RijndaelCbc(
        key=f"osu!-scoreburgr---------{osu_version}".encode(),
        iv=b64decode(iv_b64),
        padding=Pkcs7Padding(32),
        block_size=32,
    )

    score_data = aes.decrypt(b64decode(score_data_b64)).decode().split(":")
    client_hash_decoded = aes.decrypt(b64decode(client_hash_b64)).decode()

    parsed_score_data = ScoreData(
        beatmap_md5=score_data[0],
        username=score_data[1].strip(),
        online_checksum=score_data[2],
        count_300=int(score_data[3]),
        count_100=int(score_data[4]),
        count_50=int(score_data[5]),
        count_geki=int(score_data[6]),
        count_katu=int(score_data[7]),
        count_miss=int(score_data[8]),
        total_score=int(score_data[9]),
        max_combo=int(score_data[10]),
        perfect=score_data[11] == "True",
        grade=score_data[12].upper(),
        mods=Mods.from_score_submission(int(score_data[13])),
        passed=score_data[14] == "True",
        game_mode=osuGameMode(int(score_data[15])),
        # Score submission timestamp is UTC; keep it timezone-aware so epoch conversion is stable.
        play_time=datetime.strptime(score_data[16], "%y%m%d%H%M%S").replace(tzinfo=UTC),
    )

    # score data is delimited by colons (:).
    return parsed_score_data, client_hash_decoded

