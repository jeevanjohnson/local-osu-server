import base64

from jays_tools import MigratableModel
import ossapi.enums
from pydantic import Field, field_serializer, field_validator
from datetime import datetime
from core.models.domain.gameplay.mods import Mods
from core.models.domain.gameplay.game_mode import GameMode
from core.osu_protocol.cho.enums import osuAction
import core.osu_protocol.cho.server as cho_server

class DirectReferenceV1(MigratableModel):
    cursor_string: str | None = Field(default=None)
    last_query: list[
        tuple[
            str,
            ossapi.enums.BeatmapsetSearchMode,
            ossapi.enums.BeatmapsetSearchCategory,
        ]
    ] = Field(default_factory=list)

DirectReference = DirectReferenceV1

class BeatmapReferenceV1(MigratableModel):
    md5: str = Field(default="")
    id: int = Field(default=0)
    set_id: int = Field(default=0)
    is_difficulty_adjusted: bool = Field(default=False)

BeatmapReference = BeatmapReferenceV1

class Packets(bytearray):

    def __iadd__(self, other: bytes | cho_server.Packet | cho_server.Packets) -> "Packets":
        if isinstance(other, (cho_server.Packet, cho_server.Packets)):
            self += other.build()
        elif isinstance(other, bytes):
            super().__iadd__(other)

        return self

class ClientStateV1(MigratableModel):
    # Auth
    in_game: bool = Field(default=False)
    in_game_at: datetime = Field(default_factory=datetime.now)
    user_name: str = Field(default="")

    # Activity
    game_mode: GameMode = Field(default=GameMode.STANDARD)
    mods: Mods = Field(default=Mods())
    beatmap: BeatmapReference = Field(default_factory=BeatmapReference)
    loaded_score_id: int = Field(default=0)

    status: osuAction = Field(default=osuAction.Idle)
    status_message: str = Field(default="")

    direct_reference: DirectReference = Field(default_factory=DirectReference)

    outgoing_packets: Packets = Field(default_factory=Packets)

    class Config:
        arbitrary_types_allowed = True

    @field_serializer("outgoing_packets")
    def serialize_packet_queue(self, value: Packets) -> str:
        return base64.b64encode(bytes(value)).decode("ascii")

    @field_validator("outgoing_packets", mode="before")
    @classmethod
    def deserialize_packet_queue(cls, value: str) -> Packets:
        return Packets(base64.b64decode(value.encode("ascii")))

    @field_serializer("mods")
    def serialize_mods(self, value: Mods) -> list[str]:
        return list(value)

    @field_validator("mods", mode="before")
    @classmethod
    def deserialize_mods(cls, value: list[str]) -> Mods:
        return Mods(value)

ClientState = ClientStateV1