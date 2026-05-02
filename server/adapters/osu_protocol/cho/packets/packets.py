from dataclasses import field

from core.models.domain.normalizers.country_codes import CountryCode
from server.adapters.osu_protocol.cho.packets.codecs import (
    osuAccuracy,
    osuCodec,
    osuFloat32,
    osuGameMode,
    osuMods,
    osuStatus,
    osuU8,
    osuU16,
    osuU32,
    osuS32,
    osuU64,
    osuU32List,
    osuS32List,
    osuString,
    osuMainMenuIcon,
    osuUTCOffset,
)
from server.adapters.osu_protocol.cho.packets.enums import (
    ClientAuthFailure,
    ClientPrivileges,
    ClientStatus,
    ClientToServer,
    ServerToClient,
)
from server.adapters.osu_protocol.enums import (
    ClientGameMode,
    ClientMods
)
from dataclasses import dataclass
from typing import Self, Type, TypeVar

type PacketBodyLength = int

T = TypeVar("T")

READABLE_PACKETS: dict[ClientToServer, Type["ClientPacketBase"]] = {}


class ClientPacketReader:
    def __init__(self, buffer: memoryview):
        self._buffer = buffer
        self.offset = 0

    def buffer_remaining(self) -> memoryview:
        return self._buffer[self.offset:]

    def skip_padding(self) -> None:
        self.offset += 1

    def skip_packet(self, packet_length: PacketBodyLength) -> None:
        self.offset += packet_length

    def read_parameter(self, data_type: Type[osuCodec[T]]) -> T:
        data, bytes_read = data_type.deserialize(self.buffer_remaining())
        self.offset += bytes_read
        return data

    def read_header(self) -> tuple[ClientToServer, PacketBodyLength]:
        packet_id = self.read_parameter(osuU16)
        self.skip_padding()
        packet_length = self.read_parameter(osuU32)
        return ClientToServer(packet_id), packet_length


class ClientPacketBase:
    def __init_subclass__(cls, packet_id: ClientToServer | tuple[ClientToServer, ...], *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)

        if isinstance(packet_id, tuple):
            for id in packet_id:
                READABLE_PACKETS[id] = cls
        else:
            READABLE_PACKETS[packet_id] = cls

    @classmethod
    def deserialize(cls, packet_body: ClientPacketReader) -> "Self":
        return cls()


@dataclass
class StatusChanged(
    ClientPacketBase,
    packet_id=ClientToServer.CHANGE_ACTION
):
    status: ClientStatus
    status_message: str
    beatmap_md5: str
    current_mods: ClientMods
    current_game_mode: ClientGameMode
    beatmap_id: int

    @classmethod
    def deserialize(cls, packet_body: ClientPacketReader) -> "StatusChanged":
        return cls(
            status=packet_body.read_parameter(osuStatus),
            status_message=packet_body.read_parameter(osuString),
            beatmap_md5=packet_body.read_parameter(osuString),
            current_mods=packet_body.read_parameter(osuMods),
            current_game_mode=packet_body.read_parameter(osuGameMode),
            beatmap_id=packet_body.read_parameter(osuS32)
        )


@dataclass
class LogOut(
    ClientPacketBase,
    packet_id=ClientToServer.LOGOUT
):
    pass


@dataclass
class Ping(
    ClientPacketBase,
    packet_id=ClientToServer.PING
):
    pass


@dataclass
class UserStatsRequest(
    ClientPacketBase,
    packet_id=ClientToServer.USER_STATS_REQUEST
):
    user_ids: list[int]

    @classmethod
    def deserialize(cls, packet_body: ClientPacketReader) -> "UserStatsRequest":
        return cls(
            user_ids=packet_body.read_parameter(osuU32List)
        )


@dataclass
class FriendRemove(
    ClientPacketBase,
    packet_id=ClientToServer.FRIEND_REMOVE,
):
    id: int

    @classmethod
    def deserialize(cls, packet_body: ClientPacketReader) -> "FriendRemove":
        return cls(
            id=packet_body.read_parameter(osuU32)
        )


@dataclass
class FriendAdd(
    ClientPacketBase,
    packet_id=ClientToServer.FRIEND_ADD
):
    friend_user_id: int

    @classmethod
    def deserialize(cls, packet_body: ClientPacketReader) -> "FriendAdd":
        return cls(
            friend_user_id=packet_body.read_parameter(osuU32)
        )


@dataclass
class SendMessage(
    ClientPacketBase,
    packet_id=(
        ClientToServer.SEND_PUBLIC_MESSAGE,
        ClientToServer.SEND_PRIVATE_MESSAGE
    )
):
    sender: str
    text: str
    receiver: str
    sender_id: int

    @classmethod
    def deserialize(cls, packet_body: ClientPacketReader) -> "SendMessage":
        return cls(
            sender=packet_body.read_parameter(osuString),
            text=packet_body.read_parameter(osuString),
            receiver=packet_body.read_parameter(osuString),
            sender_id=packet_body.read_parameter(osuU32)
        )


@dataclass
class ClientPacketStream:
    packets: list[ClientPacketBase]

    def __iter__(self):
        return iter(self.packets)

    # memoryview prevents any copying happening
    # during processing of var
    @classmethod
    def from_osu_client(cls, stream: bytes) -> "Self":
        packet_reader = ClientPacketReader(
            memoryview(stream)
        )
        packet_stream = cls(
            packets=[]
        )

        while packet_reader.buffer_remaining():
            packet_id, packet_length = packet_reader.read_header()

            if packet_id not in READABLE_PACKETS:
                print(f"Skipped {packet_id.name}")
                packet_reader.skip_packet(packet_length)
                continue

            packet = READABLE_PACKETS[packet_id].deserialize(
                packet_reader
            )

            packet_stream.packets.append(packet)

        return packet_stream


@dataclass
class ServerPacket:
    id: ServerToClient
    body_parameters: list[bytes] = field(default_factory=list)

    def serialize(self) -> bytes:
        body = b"".join(self.body_parameters)
        packet_length = len(body)

        return (
            osuU16.serialize(self.id.value) +
            b"\x00" +  # padding byte
            osuU32.serialize(packet_length) +
            body
        )

    def __add__(self, other: "ServerPacket") -> "ServerPacketStream":
        if isinstance(other, ServerPacket):
            return ServerPacketStream(packets=[self, other])
        else:
            raise NotImplementedError(
                "Can only add ServerPacket to ServerPacketStream")


@dataclass
class ServerPacketStream:
    packets: list[ServerPacket] = field(default_factory=list)

    def serialize(self) -> bytes:
        return b"".join(packet.serialize() for packet in self.packets)

    def __add__(self, other: "ServerPacket | ServerPacketStream") -> "ServerPacketStream":
        if isinstance(other, ServerPacket):
            self.packets.append(other)
            return self
        elif isinstance(other, ServerPacketStream):
            self.packets.extend(other.packets)
            return self
        else:
            raise NotImplementedError(
                "Can only add ServerPacket or ServerPacketStream to ServerPacketStream"
            )


def notify(message: str) -> ServerPacket:
    return ServerPacket(
        id=ServerToClient.NOTIFICATION,
        body_parameters=[
            osuString.serialize(message)
        ]
    )


def login_status(id: int | ClientAuthFailure) -> ServerPacket:
    packet = ServerPacket(
        id=ServerToClient.USER_ID,
        body_parameters=[
            osuU32.serialize(id)
        ]
    )
    return packet


def login_failed(reason: str) -> ServerPacketStream:
    packets = login_status(ClientAuthFailure.AUTHENTICATION_FAILED)
    packets += notify(reason)
    return packets


def login_successful() -> ServerPacket:
    return login_status(2)


def protocol_version(version: int = 19) -> ServerPacket:
    return ServerPacket(
        id=ServerToClient.PROTOCOL_VERSION,
        body_parameters=[
            osuU32.serialize(version)
        ]
    )


def client_privileges(client_privileges: ClientPrivileges) -> ServerPacket:
    return ServerPacket(
        id=ServerToClient.PRIVILEGES,
        body_parameters=[
            osuU32.serialize(client_privileges.value)
        ]
    )


def channel_info(
    channel_name: str,
    channel_topic: str,
    user_count: int,
) -> ServerPacket:
    return ServerPacket(
        id=ServerToClient.CHANNEL_INFO,
        body_parameters=[
            osuString.serialize(channel_name),
            osuString.serialize(channel_topic),
            osuU16.serialize(user_count)
        ]
    )


def reorder_channels() -> ServerPacket:
    return ServerPacket(
        id=ServerToClient.CHANNEL_INFO_END
    )


def main_menu_icon(
    icon_url: str,
    on_click_url: str
) -> ServerPacket:
    return ServerPacket(
        id=ServerToClient.MAIN_MENU_ICON,
        body_parameters=[
            osuMainMenuIcon.serialize(icon_url, on_click_url)
        ]
    )


def friend_list(friend_ids: list[int]) -> ServerPacket:
    return ServerPacket(
        id=ServerToClient.FRIENDS_LIST,
        body_parameters=[
            osuS32List.serialize(friend_ids)
        ]
    )


def player_presence(
    user_id: int,
    username: str,
    utc_offset: int,
    country_code: CountryCode,
    privileges: ClientPrivileges,
    game_mode: ClientGameMode,
    rank: int,
    longitude: float = 0.0,
    latitude: float = 0.0,
) -> ServerPacket:
    return ServerPacket(
        id=ServerToClient.USER_PRESENCE,
        body_parameters=[
            osuU32.serialize(user_id),
            osuString.serialize(username),
            osuUTCOffset.serialize(utc_offset),
            osuU8.serialize(country_code.value),
            osuU8.serialize(
                privileges.value | game_mode.value << 5
            ),
            osuFloat32.serialize(longitude),
            osuFloat32.serialize(latitude),
            osuU32.serialize(rank),
        ]
    )


def player_snapshot(
    user_id: int,
    action: ClientStatus,
    status_text: str,
    beatmap_md5: str,
    mods: ClientMods,
    game_mode: ClientGameMode,
    beatmap_id: int,
    ranked_score: int,
    accuracy: float,
    play_count: int,
    total_score: int,
    rank: int,
    pp: int,
) -> ServerPacket:
    return ServerPacket(
        id=ServerToClient.USER_STATS,
        body_parameters=[
            osuU32.serialize(user_id),
            osuU8.serialize(action.value),
            osuString.serialize(status_text),
            osuString.serialize(beatmap_md5),
            osuMods.serialize(mods),
            osuGameMode.serialize(game_mode),
            osuU64.serialize(beatmap_id),
            osuU32.serialize(ranked_score),
            osuAccuracy.serialize(accuracy),
            osuU32.serialize(play_count),
            osuU64.serialize(total_score),
            osuS32.serialize(rank),
            osuU16.serialize(pp)
        ]
    )


def relog(
    timeout: int,
    notification: str | None = None,
) -> ServerPacket | ServerPacketStream:
    packet = ServerPacket(
        id=ServerToClient.RESTART,
        body_parameters=[
            osuS32.serialize(timeout)
        ]
    )

    if notification:
        packet += notify(notification)

    return packet


def force_relog() -> ServerPacket | ServerPacketStream:
    return relog(timeout=0)


def player_logged_out(user_id: int) -> ServerPacket:
    return ServerPacket(
        id=ServerToClient.USER_LOGOUT,
        body_parameters=[
            osuS32.serialize(user_id),
            osuU8.serialize(0)  # padding byte
        ]
    )


def message(
    message: str,
    /,
    sender: str,
    sender_id: int,
    reciever: str,
) -> ServerPacket:

    return ServerPacket(
        id=ServerToClient.SEND_MESSAGE,
        body_parameters=[
            osuString.serialize(sender),
            osuString.serialize(message),
            osuString.serialize(reciever),
            osuS32.serialize(sender_id)
        ]
    )
