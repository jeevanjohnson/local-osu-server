"""
Purpose/Domain/Concept:
- This file contains the database models/architecture for the project regarding user profiles. (profiles.json)
"""

from typing import TypedDict

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

ProfileName = str
Profile = dict[ProfileName, ProfileData]