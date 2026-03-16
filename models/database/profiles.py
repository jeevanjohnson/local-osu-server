"""
Purpose/Domain/Concept:
- This file contains the database models/architecture for the project regarding user profiles. (profiles.json)
"""

from typing import TypedDict

class osuTrainerBeatmapConfig(TypedDict):
    allow_submission: bool
    sync_rank_status_with_bancho: bool

class Settings(TypedDict):
    relax_submission: bool
    auto_pilot_submission: bool
    score_v2_submission: bool
    force_scorev2: bool
    force_nf: bool
    osu_trainer_beatmaps: osuTrainerBeatmapConfig
    self_rank: bool

class Performance(TypedDict):
    rank: int
    accuracy: float
    playcount: int
    total_score: int
    ranked_score: int
    performance_points: int

class ProfileData(TypedDict):
    profile_picture: str | None
    friend_ids: list[int]
    country_code: int
    performance: dict[str, Performance]
    notes: str | None
    settings: Settings

ProfileName = str
Profile = dict[ProfileName, ProfileData]