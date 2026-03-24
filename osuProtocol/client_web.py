from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, unique

import ossapi.enums

from models.bancho.scores import LazerScore, Score, StableScore
from models.database.scores import (
    CurrentScore as ProfileScore,
)
from models.domain.gameplay import osuMods


@unique
class osuMapStatus(IntEnum):
    """
    Represents the ranked status of a beatmap.
    """

    NOTSUBMITTED = -1
    PENDING = 0
    UPDATEAVALIABLE = 1
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
            # This allows watching replays
            # and playing w/ score v2 making the
            # ranking up the map feel with the lb on more
            # realistic to bancho/lazer
            stable_mods |= osuMods.SCOREV2

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


class _GraveyardLeaderboard(Leaderboard):
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


GRAVEYARD_LEADERBOARD = _GraveyardLeaderboard().serialize()


class _UpdateBeatmapRequestLeaderboard(Leaderboard):
    """
    Represents a leaderboard for beatmaps that have been updated.
    """

    def __init__(self):
        super().__init__(
            LeaderboardHeader(
                beatmap_status=osuMapStatus.UPDATEAVALIABLE,
                beatmap_id=0,
                beatmap_set_id=0,
                num_of_scores=0,
                artist="",
                title="",
            ),
            [],
        )


UPDATE_BEATMAP_REQUEST_LEADERBOARD = _UpdateBeatmapRequestLeaderboard().serialize()


class _NotSubmittedLeaderboard(Leaderboard):
    """
    Represents a leaderboard for beatmaps that have not been submitted.
    """

    def __init__(self):
        super().__init__(
            LeaderboardHeader(
                beatmap_status=osuMapStatus.NOTSUBMITTED,
                beatmap_id=0,
                beatmap_set_id=0,
                num_of_scores=0,
                artist="",
                title="",
            ),
            [],
        )


NOT_SUBMITTED_LEADERBOARD = _NotSubmittedLeaderboard().serialize()


class ScoringAlgorithm(IntEnum):
    LAZER = 0
    PP = 1

    def to_api_v2(self) -> ossapi.enums.RankingType:
        return {
            ScoringAlgorithm.LAZER: ossapi.enums.RankingType.SCORE,
            ScoringAlgorithm.PP: ossapi.enums.RankingType.PERFORMANCE,
        }[self]


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


class Beatmap(Chart):
    pass


class OverallRanking(Chart):
    pass


@dataclass
class SubmissionCharts:
    beatmap_id: int
    beatmap_set_id: int
    beatmap_playcount: int
    beatmap_passcount: int
    last_updated: datetime
    score_id: int
    beatmap_chart: Beatmap
    overall_ranking_chart: OverallRanking
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
    beatmap_chart=Beatmap(
        rank=Rank(name="rank"),
        ranked_score=RankedScore(name="rankedScore"),
        total_score=TotalScore(name="totalScore"),
        max_combo=MaxCombo(name="maxCombo"),
        accuracy=Accuracy(name="accuracy"),
        pp=PerformancePoints(name="pp"),
    ),
    overall_ranking_chart=OverallRanking(
        rank=Rank(name="rank"),
        ranked_score=RankedScore(name="rankedScore"),
        total_score=TotalScore(name="totalScore"),
        max_combo=MaxCombo(name="maxCombo"),
        accuracy=Accuracy(name="accuracy"),
        pp=PerformancePoints(name="pp"),
    ),
    achievements=Achievements(),
)
