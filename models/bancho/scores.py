import functools
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
)

from models.domain.gameplay import Mods, osuGameMode

if TYPE_CHECKING:
    from osu_protocol.client_web import ScoringAlgorithm


EpochTime = int


class Combo(BaseModel):
    actual: int
    max: int


class BaseScore(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    score_id: int
    game_mode: osuGameMode
    username: str
    total_score_value: int = Field(
        validation_alias=AliasChoices("_total_score", "total_score"),
        serialization_alias="_total_score",
    )
    combo: Combo
    count50: int
    count100: int
    count300: int
    count_miss: int
    perfect: bool
    enabled_mods: Mods
    user_id: int
    time_set: EpochTime
    replay_available: bool

    performance_points: int
    lazer: bool = Field(default=False)

    @field_serializer("enabled_mods")
    def serialize_mods(self, value: Mods) -> list[str]:
        return list(value)

    @field_validator("enabled_mods", mode="before")
    @classmethod
    def deserialize_mods(cls, value: list[str]) -> Mods:
        return Mods(value)

    # Self calc scores regardless of whether it's lazer or stable
    # this allows more accurate score sorting for leaderboards
    @functools.cached_property
    def total_score(self) -> int:
        # Note: bonus_points only comes from spinner over-spin (not implemented here)
        bonus_points: float = 0.0

        total_hits = self.count300 + self.count100 + self.count50 + self.count_miss

        if total_hits == 0:
            return 0

        # Accuracy calculation (standard osu! weighting)
        accuracy = (self.count300 + self.count100 / 3 + self.count50 / 5) / total_hits

        # Combo progress: achieved combo / max possible combo
        combo_progress = self.combo.actual / self.combo.max if self.combo.max > 0 else 0

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


class StableScore(BaseScore):
    lazer: Literal[False] = False


class LazerScore(BaseScore):
    lazer: Literal[True] = True


Score = Annotated[StableScore | LazerScore, Field(discriminator="lazer")]


class Scores(BaseModel):
    limit: int = Field(default=50)
    all_scores: list[Score]

    def append(self, score: Score) -> None:
        self.all_scores.append(score)

    @property
    def scores(self) -> list[Score]:
        return self.all_scores[: self.limit]

    @property
    def total(self) -> int:
        return len(self.scores)

    def sort_by_pp(self) -> None:
        self.all_scores.sort(
            key=lambda s: (s.performance_points or 0, -s.time_set), reverse=True
        )

    def sort_by_score(self):
        self.all_scores.sort(key=lambda s: (s.total_score, -s.time_set), reverse=True)

    def sort(self, algorithm: "ScoringAlgorithm") -> None:
        # Lazy import prevents circular import at module load time.
        from osu_protocol.client_web import ScoringAlgorithm

        if algorithm == ScoringAlgorithm.PP:
            self.sort_by_pp()
        elif algorithm == ScoringAlgorithm.LAZER:
            self.sort_by_score()
        else:
            raise ValueError(f"Unsupported scoring algorithm: {algorithm}")
