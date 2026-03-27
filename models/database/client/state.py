from datetime import datetime

import ossapi.enums
from jays_tools import MigratableModel
from pydantic import Field, field_serializer, field_validator

from models.domain.gameplay import Mods
from osu_protocol.cho.server import osuAction, osuGameMode


class DirectReferenceV1(MigratableModel):
    cursor_string: str | None = Field(default=None)
    last_query: list[
        tuple[
            str,
            ossapi.enums.BeatmapsetSearchMode,
            ossapi.enums.BeatmapsetSearchCategory,
        ]
    ] = Field(default_factory=list)


class BeatmapReferenceV1(MigratableModel):
    md5: str = Field(default="")
    id: int = Field(default=0)
    set_id: int = Field(default=0)
    is_difficulty_adjusted: bool = Field(default=False)
    watchable_replays: list[int] = Field(default_factory=list)


BeatmapReference = BeatmapReferenceV1


class ClientStateV1(MigratableModel):
    # Auth
    in_game: bool = Field(default=False)
    in_game_at: datetime = Field(default_factory=datetime.now)
    logged_in: bool = Field(default=False)
    profile_name: str = Field(default="")

    # Activity
    game_mode: osuGameMode = Field(default=osuGameMode.STANDARD)
    mods: Mods = Field(default=Mods())
    beatmap: BeatmapReference = Field(default_factory=BeatmapReference)
    loaded_score_id: int = Field(default=0)

    status: osuAction = Field(default=osuAction.Idle)
    status_message: str = Field(default="")

    direct_reference: DirectReferenceV1 = Field(default_factory=DirectReferenceV1)

    class Config:
        arbitrary_types_allowed = True

    @field_serializer("mods")
    def serialize_mods(self, value: Mods) -> list[str]:
        return list(value)

    @field_validator("mods", mode="before")
    @classmethod
    def deserialize_packet_queue(cls, value: list[str]) -> Mods:
        return Mods(value)


ClientState = ClientStateV1
