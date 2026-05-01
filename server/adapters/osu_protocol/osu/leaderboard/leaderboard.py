from dataclasses import dataclass, field

from server.adapters.osu_protocol.osu.enums import BeatmapSetStatus
from server.adapters.osu_protocol.enums import ClientMods

LEADERBOARD_SCORE_FMT = (
    "{id}|{name}|{score}|{max_combo}|"
    "{n50}|{n100}|{n300}|{nmiss}|{nkatu}|{ngeki}|"
    "{perfect}|{mods}|{userid}|{rank}|{time}|{has_replay}"
)

EpochTime = int


@dataclass
class Score:
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
    enabled_mods: ClientMods
    user_id: int
    position: int
    time_set_epoch: int
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
            time=self.time_set_epoch,
            has_replay=int(self.replay_available),
        )

    def __repr__(self) -> str:
        return self.serialize()


STARTING_LB_FORMAT = (
    "{beatmap_status}|false|{beatmap_id}|{beatmap_set_id}|{num_of_scores}\n0\n"
    "[bold:0,size:20]{artist_unicode}|{title_unicode}\n10.0\n"
)


@dataclass
class LeaderboardHeader:
    """
    Represents the header of a leaderboard, containing metadata about the leaderboard.
    """

    beatmap_status: BeatmapSetStatus
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


@dataclass
class Leaderboard:
    header: LeaderboardHeader
    scores: list[Score] = field(default_factory=list)
    personal_best: Score | None = None

    @classmethod
    def for_status(cls, status: BeatmapSetStatus) -> "Leaderboard":
        return cls(
            header=LeaderboardHeader(
                beatmap_status=status,
                beatmap_id=0,
                beatmap_set_id=0,
                num_of_scores=0,
                artist="",
                title="",
            )
        )

    def serialize(self) -> bytes:
        if self.header.beatmap_status < 1:
            return f"{self.header.beatmap_status.value}|false".encode()

        buffer = bytearray()
        buffer += self.header.serialize().encode()

        if self.personal_best:
            buffer += self.personal_best.serialize().encode()

        buffer += b"\n"

        for score in self.scores:
            buffer += score.serialize().encode() + b"\n"

        return bytes(buffer)


def empty_leaderboard(status: BeatmapSetStatus) -> Leaderboard:
    """
    Creates an empty leaderboard with default values.
    """
    return Leaderboard.for_status(status)


def pending_leaderboard() -> Leaderboard:
    """
    Creates a leaderboard for a beatmap that is pending, which has no scores.
    """
    return Leaderboard.for_status(BeatmapSetStatus.PENDING)


def update_available_leaderboard() -> Leaderboard:
    """
    Creates a leaderboard for a beatmap that has an update available, which has no scores.
    """
    return Leaderboard.for_status(BeatmapSetStatus.UPDATE_AVAILABLE)


def not_submitted_leaderboard() -> Leaderboard:
    """
    Creates a leaderboard for a beatmap that has not been submitted, which has no scores.
    """
    return Leaderboard.for_status(BeatmapSetStatus.NOT_SUBMITTED)
