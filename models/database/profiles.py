"""
Purpose/Domain/Concept:
- This file contains the database models/architecture for the project regarding user profiles. (profiles.json)
"""

from pathlib import Path

from jays_tools.json_database import MigratableModel
from pydantic import Field

from models.domain.gameplay import osuGameMode
from osuProtocol.client_web import ScoringAlgorithm
from osuProtocol.server_packets import osuCountryCode


class difficultyAdjustedBeatmapConfigV1(MigratableModel):
    allow_submission: bool = Field(default=True)
    sync_rank_status_with_bancho: bool = Field(default=True)


CurrentDifficultyAdjustedBeatmapConfig = difficultyAdjustedBeatmapConfigV1


class LeaderboardConfigV1(MigratableModel):
    leaderboard_score_limit: int = Field(default=50)
    show_lazer_scores_on_leaderboard: bool = Field(default=True)
    truncate_user_names_on_leaderboard: bool = Field(default=False)

CurrentLeaderboardConfig = LeaderboardConfigV1

class SettingsV1(MigratableModel):
    relax_submission: bool = Field(default=False)
    auto_pilot_submission: bool = Field(default=False)
    score_v2_submission: bool = Field(default=False)
    force_scorev2: bool = Field(default=False)
    force_nf: bool = Field(default=False)
    difficulty_adjusted_beatmaps: CurrentDifficultyAdjustedBeatmapConfig = Field(
        default_factory=CurrentDifficultyAdjustedBeatmapConfig
    )
    self_rank: bool = Field(default=False)
    leaderboard: CurrentLeaderboardConfig = Field(
        default_factory=CurrentLeaderboardConfig
    )
    scoring_algorithm: ScoringAlgorithm = Field(default=ScoringAlgorithm.LAZER)
    score_v2_shows_lazer_only_leaderboard: bool = Field(default=False)
    ignore_beatmap_updates: bool = Field(default=False)

CurrentSettings = SettingsV1


class PerformanceV1(MigratableModel):
    rank: int = Field(default=0)
    accuracy: float = Field(default=0.0)
    playcount: int = Field(default=0)
    total_score: int = Field(default=0)
    ranked_score: int = Field(default=0)
    performance_points: int = Field(default=0)


CurrentPerformance = PerformanceV1


def performace_factory() -> dict[osuGameMode, CurrentPerformance]:
    return {
        osuGameMode.STANDARD: CurrentPerformance(),
        osuGameMode.TAIKO: CurrentPerformance(),
        osuGameMode.CATCH_THE_BEAT: CurrentPerformance(),
        osuGameMode.MANIA: CurrentPerformance(),
    }


URL = str


class ProfileV1(MigratableModel):
    profile_picture: Path | URL | None = Field(default=None)
    friend_ids: list[int] = Field(default=[])
    country_code: osuCountryCode = Field(default=osuCountryCode.XX)
    performance: dict[osuGameMode, CurrentPerformance] = Field(
        default_factory=performace_factory
    )
    notes: str | None = Field(default=None)
    settings: CurrentSettings = Field(default_factory=CurrentSettings)


CurrentProfile = ProfileV1

ProfileName = str


def profiles_factory() -> dict[ProfileName, CurrentProfile]:
    return {}


class ProfilesV1(MigratableModel):
    all: dict[ProfileName, CurrentProfile] = Field(
        default_factory=profiles_factory
    )  # Use factory to avoid default instanece from being shared and changed/mutated across profiles


CurrentProfiles = ProfilesV1
