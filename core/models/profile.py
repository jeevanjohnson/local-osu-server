from pathlib import Path

from jays_tools.json_database import MigratableModel
from pydantic import Field, field_validator

from models.domain.accuracy import UnitAccuracy, to_unit_accuracy
from models.domain.gameplay import osuGameMode
from models.domain.scores import ScoringAlgorithm
from core.osu_protocol.cho.server import osuCountryCode


class SubmissionSettingsV1(MigratableModel):
    """What score submissions are allowed"""

    relax_submission: bool = Field(default=True)
    auto_pilot_submission: bool = Field(default=True)
    score_v2_submission: bool = Field(default=True)
    force_score_v2: bool = Field(default=False)
    force_nf: bool = Field(default=False)


class ScoringSettingsV1(MigratableModel):
    """How to calculate and display scores"""

    algorithm: ScoringAlgorithm = Field(default=ScoringAlgorithm.LAZER)
    score_v2_shows_lazer_only_leaderboard: bool = Field(default=False)


class LeaderboardSettingsV1(MigratableModel):
    """Leaderboard display rules"""

    score_limit: int = Field(default=50)
    show_lazer_scores_on_leaderboard: bool = Field(default=True)


SubmissionSettings = SubmissionSettingsV1
ScoringSettings = ScoringSettingsV1
LeaderboardSettings = LeaderboardSettingsV1


class ProfileSettingsV1(MigratableModel):
    """Master settings container"""

    submission: SubmissionSettingsV1 = Field(default_factory=SubmissionSettings)
    scoring: ScoringSettingsV1 = Field(default_factory=ScoringSettings)
    leaderboard: LeaderboardSettingsV1 = Field(default_factory=LeaderboardSettings)


ProfileSettings = ProfileSettingsV1


class PerformanceV1(MigratableModel):
    rank: int = Field(default=0)
    accuracy: UnitAccuracy = Field(default=0.0)
    playcount: int = Field(default=0)
    total_score: int = Field(default=0)
    ranked_score: int = Field(default=0)
    performance_points: int = Field(default=0)
    max_combo: int = Field(default=0)

    @field_validator("accuracy", mode="before")
    @classmethod
    def normalize_accuracy(cls, value: float | int) -> float:
        return to_unit_accuracy(value)


Performance = PerformanceV1


def performace_factory() -> dict[osuGameMode, Performance]:
    return {
        osuGameMode.STANDARD: Performance(),
        osuGameMode.TAIKO: Performance(),
        osuGameMode.CATCH_THE_BEAT: Performance(),
        osuGameMode.MANIA: Performance(),
    }


def seasonal_backgrounds_factory() -> list[str]:
    return [
        "https://raw.githubusercontent.com/jeevanjohnson/local-osu-server/refs/heads/2026/resources/seasonal_bg.png"
    ]


URL = str


class ProfileV1(MigratableModel):
    profile_picture: Path | URL | None = Field(default=None)
    friend_ids: list[int] = Field(default=[])
    country_code: osuCountryCode = Field(default=osuCountryCode.XX)
    performance: dict[osuGameMode, Performance] = Field(
        default_factory=performace_factory
    )
    notes: str | None = Field(default=None)
    settings: ProfileSettings = Field(default_factory=ProfileSettings)
    seasonal_backgrounds: list[str] = Field(
        default_factory=seasonal_backgrounds_factory
    )

Profile = ProfileV1