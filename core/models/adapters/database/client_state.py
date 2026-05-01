import base64

from jays_tools.sql_database import MigratableSQLModel
import ossapi.enums
from pydantic import Field, field_serializer, field_validator
from datetime import datetime
from core.models.domain.normalizers.game_mode import GameMode
from core.models.domain.normalizers.mods import Mods
from core.models.domain.normalizers.scoring_type import ScoringType
from core.models.domain.normalizers.client_status import ClientStatus
from server.adapters.osu_protocol.cho.packets.packets import ServerPacket, ServerPacketStream


class Packets(bytearray):

    def __iadd__(self, other: bytes | ServerPacket | ServerPacketStream) -> "Packets":
        if isinstance(other, (ServerPacket, ServerPacketStream)):
            self += other.serialize()
            return self
        elif isinstance(other, bytes):
            return super().__iadd__(other)
        else:
            raise TypeError(
                f"Unsupported type for Packets addition: {type(other)}"
            )


class ClientStateV1(MigratableSQLModel, table=True):
    profile_name: str = Field(default="")
    logged_in_at: datetime = Field(default_factory=datetime.now)

    # Activity
    game_mode: GameMode = Field(default=GameMode.STANDARD)
    mods: Mods = Field(default=Mods())
    beatmap_md5: str = Field(default="")
    beatmap_id: int = Field(default=0)
    beatmap_set_id: int = Field(default=0)
    beatmap_is_difficulty_adjusted: bool = Field(default=False)
    loaded_score_id: int = Field(default=0)

    status: ClientStatus = Field(default=ClientStatus.IDLE)
    status_message: str = Field(default="")

    direct_cursor_string: str | None = Field(default=None)
    direct_last_query: list[
        tuple[
            str,
            ossapi.enums.BeatmapsetSearchMode,
            ossapi.enums.BeatmapsetSearchCategory,
        ]
    ] = Field(default_factory=list)

    outgoing_packets: Packets = Field(default_factory=Packets)

    current_scoring_mode: ScoringType = Field(default=ScoringType.SCOREV1)

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
