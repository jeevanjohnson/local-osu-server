import base64
from typing import TYPE_CHECKING

from jays_tools import MigratableModel
from pydantic import ConfigDict, Field, field_serializer, field_validator

from models.domain.accuracy import UnitAccuracy
from models.domain.gameplay import Mods
from core.osu_protocol.cho.server import osuGameMode

if TYPE_CHECKING:
    from models.domain.scores import ScoringAlgorithm
    from core.osu_protocol.osu.score_submission import ScoreData

EpochTime = int


class ScoreV1(MigratableModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    beatmap_md5: str
    game_mode: osuGameMode
    username: str
    count50: int
    count100: int
    count300: int
    count_miss: int
    combo: int
    enabled_mods: Mods
    perfect: bool
    time_set: EpochTime
    performance_points: int | None = Field(default=None)
    replay_frames: bytes

    beatmap_max_combo: int

    @field_serializer("enabled_mods")
    def serialize_mods(self, value: Mods) -> list[str]:
        return list(value)

    @field_validator("enabled_mods", mode="before")
    @classmethod
    def deserialize_mods(cls, value: list[str]) -> Mods:
        return Mods(value)

    @field_serializer("replay_frames")
    def serialize_replay_frames(self, value: bytes) -> str:
        return base64.b64encode(value).decode("ascii")

    @field_validator("replay_frames", mode="before")
    @classmethod
    def deserialize_replay_frames(cls, value: object) -> bytes:
        if isinstance(value, bytes):
            return value

        assert isinstance(value, str), "Expected base64 replay frames payload"
        return base64.b64decode(value.encode("ascii"))

    @classmethod
    def from_score_submission(
        cls,
        score_id: int,
        score_data: "ScoreData",
        beatmap_md5: str,
        replay_frames: bytes,
        beatmap_max_combo: int,
        pp: int | None = None,
    ) -> "ScoreV1":
        return cls(
            id=score_id,  # This will be set when the score is saved to the database
            game_mode=score_data.game_mode,
            username=score_data.username,
            count50=score_data.count_50,
            count100=score_data.count_100,
            count300=score_data.count_300,
            count_miss=score_data.count_miss,
            combo=score_data.max_combo,
            enabled_mods=score_data.mods,
            perfect=score_data.perfect,
            time_set=int(score_data.play_time.timestamp()),
            performance_points=pp,
            replay_frames=replay_frames,
            beatmap_md5=beatmap_md5,
            beatmap_max_combo=beatmap_max_combo,
        )

    @property
    def total_score(self) -> int:
        # Note: bonus_points only comes from spinner over-spin (not implemented here)
        bonus_points: float = 0.0

        total_hits = self.count300 + self.count100 + self.count50 + self.count_miss

        if total_hits == 0:
            return 0

        # Accuracy calculation (standard osu! weighting)
        accuracy = (self.count300 + self.count100 / 3 + self.count50 / 5) / total_hits

        # Combo progress: achieved combo / max possible combo
        combo_progress = (
            self.combo / self.beatmap_max_combo if self.beatmap_max_combo > 0 else 0
        )

        # Accuracy progress: in osu!standard this is always 1.0
        accuracy_progress = 1.0

        # Correct lazer scoring formula (two 500k terms)
        hit_score = (
            500_000 * accuracy * combo_progress
            + 500_000 * (accuracy**5) * accuracy_progress
        )

        # Add bonus points (spinner overspins)
        base_score = hit_score + bonus_points

        # Apply the 0.96× "Classic" multiplier (always present for imported scores)
        # Then apply any mod multiplier from the original play (DT, HT, etc.)
        final_score = (
            base_score * 0.96 * self.enabled_mods.mod_multipler(self.game_mode)
        )

        return round(final_score)

    @property
    def accuracy(self) -> UnitAccuracy:
        total_objects = self.count300 + self.count100 + self.count50 + self.count_miss
        if total_objects == 0:
            return 0.0

        total_score = 300 * self.count300 + 100 * self.count100 + 50 * self.count50
        max_score = 300 * total_objects
        return total_score / max_score


CurrentScore = ScoreV1

BEATMAP_MD5 = str
IGNORED_MODS_IN_FILTER = ["SV2", "RX"]


class MapScoresV1(MigratableModel):
    beatmap_md5: BEATMAP_MD5
    scores: list[CurrentScore] = Field(default_factory=list)

    def sort_by_pp(self) -> None:
        self.scores.sort(
            key=lambda s: (s.performance_points or 0, -s.time_set), reverse=True
        )

    def sort_by_score(self):
        self.scores.sort(key=lambda s: (s.total_score, -s.time_set), reverse=True)

    def sort(self, algorithm: "ScoringAlgorithm") -> None:
        from models.domain.scores import ScoringAlgorithm

        if algorithm == ScoringAlgorithm.PP:
            self.sort_by_pp()
        elif algorithm == ScoringAlgorithm.LAZER:
            self.sort_by_score()
        else:
            raise ValueError(f"Unsupported scoring algorithm: {algorithm}")

    def append(self, score: CurrentScore) -> None:
        self.scores.append(score)

    def filter_by(
        self, game_mode: osuGameMode | None = None, mods: Mods | None = None
    ) -> "MapScoresV1":
        filtered_scores = []

        for score in self.scores:
            if game_mode is not None and score.game_mode != game_mode:
                continue

            if mods is not None and not score.enabled_mods.are_same(
                mods,
                ignore=IGNORED_MODS_IN_FILTER,
            ):
                continue

            filtered_scores.append(score)

        return MapScoresV1(beatmap_md5=self.beatmap_md5, scores=filtered_scores)


CurrentMapScores = MapScoresV1


class ScoresForProfileV1(MigratableModel):
    scores: dict[BEATMAP_MD5, CurrentMapScores] = Field(default_factory=dict)

    @property
    def total_scores(self) -> int:
        return sum(len(map_scores.scores) for map_scores in self.scores.values())


CurrentScoresForProfile = ScoresForProfileV1

PROFILE_NAME = str


class ScoresV1(MigratableModel):
    """
    Dual-indexed score storage for efficient O(1) access:
    - profiles: Organizes scores by profile -> beatmap (for user stats)
    - beatmap_leaderboards: Organizes scores by beatmap (for leaderboard views)
    - score_counter: Atomic score ID allocation
    """

    profiles: dict[PROFILE_NAME, CurrentScoresForProfile] = Field(default_factory=dict)
    beatmap_leaderboards: dict[BEATMAP_MD5, CurrentMapScores] = Field(
        default_factory=dict
    )
    score_counter: int = Field(default=0)

    @property
    def total_scores(self) -> int:
        """Aggregate total score count across all profiles"""
        return sum(
            profile_scores.total_scores for profile_scores in self.profiles.values()
        )


CurrentScores = ScoresV1
