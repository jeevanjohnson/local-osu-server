from jays_tools.json_database import MigratableModel
from pydantic import Field, field_validator

from core.models.domain.gameplay.accuracy import Accuracy
from core.models.domain.gameplay.scoring import ScoringType
from core.osu_protocol.cho.server import osuCountryCode
from core.models.domain.gameplay.game_mode import GameMode
import random

class SubmissionSettingsV1(MigratableModel):
    """What score submissions are allowed"""

    relax_submission: bool = Field(default=False)
    auto_pilot_submission: bool = Field(default=False)
    score_v2_submission: bool = Field(default=False)
    force_score_v2: bool = Field(default=False)
    force_nf: bool = Field(default=False)

class LeaderboardSettingsV1(MigratableModel):
    """Leaderboard display rules"""

    score_limit: int = Field(default=50)
    show_lazer_scores_on_leaderboard: bool = Field(default=True)
    show_only_lazer_scores_on_leaderboard_with_score_v2_enabled: bool = Field(default=False)
    scores_sorted_by: ScoringType = Field(default=ScoringType.SCOREV1)

SubmissionSettings = SubmissionSettingsV1
LeaderboardSettings = LeaderboardSettingsV1

class ProfileSettingsV1(MigratableModel):
    """Master settings container"""

    submission: SubmissionSettingsV1 = Field(default_factory=SubmissionSettings)
    leaderboard: LeaderboardSettingsV1 = Field(default_factory=LeaderboardSettings)

ProfileSettings = ProfileSettingsV1

class PerformanceV1(MigratableModel):
    rank: int = Field(default=0)
    accuracy: Accuracy = Field(default=Accuracy(0))
    playcount: int = Field(default=0)
    total_score_v1: int = Field(default=0)
    total_score_v2: int = Field(default=0)
    ranked_score_v1: int = Field(default=0)
    ranked_score_v2: int = Field(default=0)
    performance_points: int = Field(default=0)
    max_combo: int = Field(default=0)

    @field_validator("accuracy", mode="before")
    @classmethod
    def normalize_accuracy(cls, value: float | int) -> Accuracy:
        return Accuracy(value)
    
    class Config:
        arbitrary_types_allowed = True

Performance = PerformanceV1

def performace_factory() -> dict[GameMode, Performance]:
    return {
        GameMode.STANDARD: Performance(),
        GameMode.TAIKO: Performance(),
        GameMode.CATCH: Performance(),
        GameMode.MANIA: Performance(),
    }


def seasonal_backgrounds_factory() -> list[str]:
    return [
        "https://raw.githubusercontent.com/jeevanjohnson/local-osu-server/refs/heads/2026/resources/seasonal_bg.png"
    ]


def random_country_code_factory() -> osuCountryCode:
    return random.choice(
        list(osuCountryCode)
    )

URL = str


class ProfileV1(MigratableModel):
    avatar_url: URL = Field(default="https://a.ppy.sh/")
    friend_ids: list[int] = Field(default=[])
    country_code: osuCountryCode = Field(
        default_factory=random_country_code_factory
    )
    performance: dict[GameMode, Performance] = Field(
        default_factory=performace_factory
    )
    notes: str = Field(default="")
    settings: ProfileSettings = Field(default_factory=ProfileSettings)
    seasonal_backgrounds: list[str] = Field(
        default_factory=seasonal_backgrounds_factory
    )

Profile = ProfileV1