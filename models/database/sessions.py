"""
Purpose/Domain/Concept:
- This file contains the database models/architecture for the project regarding a user's sessions. (sessions.json)
"""

from typing import TypedDict

class Session(TypedDict):
    profile_name: str | None
    loaded_beatmap_md5: str | None
    loaded_beatmap_id: int | None
    loaded_beatmap_set_id: int | None
    loaded_replay_id: int | None
    current_game_mode: int | None
    loaded_mods: int | None
    packet_queue: str | None # base64 encoding
    client_opened: bool
    status: int | None
    status_message: str | None
