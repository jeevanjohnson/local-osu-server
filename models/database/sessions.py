"""
Purpose/Domain/Concept:
- This file contains the database models/architecture for the project regarding a user's sessions. (sessions.json)
"""

import base64
from datetime import datetime
from pathlib import Path

from jays_tools.json_database import MigratableModel
from pydantic import Field, field_serializer, field_validator

from models.domain.gameplay import osuGameMode, osuMods
from osuProtocol.server_packets import osuAction


class SessionOsuClientActivityV1(MigratableModel):
    opened: bool = Field(default=False)
    logged_in_at: datetime = Field(default_factory=datetime.now)
    status: osuAction = Field(default=osuAction.Idle)
    status_message: str = Field(default="")


CurrentSessionOsuClientActivity = SessionOsuClientActivityV1


# TODO: make this beatmap model?
class SessionBeatmapInfoV1(MigratableModel):
    md5: str = Field(default="")
    id: int = Field(default=0)
    set_id: int = Field(default=0)


CurrentSessionBeatmapInfo = SessionBeatmapInfoV1


class SessionV1(MigratableModel):
    loaded: bool = Field(default=False)
    profile_name: str = Field(default="")
    packet_queue: bytes = Field(default=b"")
    songs_folder: Path | None = Field(default=None)
    replays_folder: Path | None = Field(default=None)

    latest_replay_id: int = Field(default=0)
    current_game_mode: osuGameMode = Field(default=osuGameMode.STANDARD)
    # TODO: List of str mods to be compatible with lazer?
    latest_enabled_mods: osuMods = Field(default=osuMods.NOMOD)
    latest_beatmap: CurrentSessionBeatmapInfo | None = Field(default=None)
    osu_client: CurrentSessionOsuClientActivity = Field(
        default_factory=CurrentSessionOsuClientActivity
    )

    @field_serializer("packet_queue")
    def serialize_packet_queue(self, value: bytes) -> str:
        return base64.b64encode(value).decode("ascii")

    @field_validator("packet_queue", mode="before")
    @classmethod
    def deserialize_packet_queue(cls, value: str) -> bytes:
        return base64.b64decode(value.encode("ascii"))


CurrentSession = SessionV1
