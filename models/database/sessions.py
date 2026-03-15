"""
Purpose/Domain/Concept:
- This file contains the database models/architecture for the project regarding a user's sessions. (sessions.json)
"""

from typing import TypedDict

# Only one session will be active at a time so we can just

class Session(TypedDict):
    profile_name: str | None
    loaded_beatmap_md5: str | None
    loaded_replay_id: int | None
    current_game_mode: int | None