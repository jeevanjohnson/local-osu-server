import base64

from jays_tools import MigratableModel
from pydantic import Field, field_serializer, field_validator

from osuProtocol.server_packets import Packet
from osuProtocol.server_packets import Packets as ServerPackets

RAW_PACKET = bytes


class Packets(bytearray):
    # handle += for Packets
    def __iadd__(self, other: bytes | Packet | ServerPackets) -> "Packets":
        print(f"Adding packet(s) to queue: {other}")

        if isinstance(other, Packet):
            self += other.build()
        elif isinstance(other, ServerPackets):
            self += b"".join(packet.build() for packet in other)
        elif isinstance(other, bytes):
            super().__iadd__(other)

        return self


class ClientUpdateV1(MigratableModel):
    packets: Packets = Field(default_factory=Packets)

    class Config:
        arbitrary_types_allowed = True

    @field_serializer("packets")
    def serialize_packet_queue(self, value: Packets) -> str:
        return base64.b64encode(bytes(value)).decode("ascii")

    @field_validator("packets", mode="before")
    @classmethod
    def deserialize_packet_queue(cls, value: str) -> Packets:
        return Packets(base64.b64decode(value.encode("ascii")))


ClientUpdate = ClientUpdateV1
