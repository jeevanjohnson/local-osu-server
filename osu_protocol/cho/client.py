"""
Purpose/Domain/Concept:
- This module defines the packet IDs for packets sent BY the osu! client TO the server.
- These are the packets the server needs to READ and handle.
"""

import struct
from dataclasses import dataclass, field, fields
from enum import IntEnum, unique
from pprint import pformat
from typing import Callable, Type, TypedDict, TypeVar, get_type_hints

# from adapters import log
from osu_protocol.cho.types import (
    osuBaseType,
    osuIntSigned32Bit,
    osuIntUnsigned32Bit,
    osuIntUnSigned32List,
    osuString,
    osuUnsignedChar,
)


class LoginData(TypedDict):
    username: str
    password_md5: bytes
    osu_version: str
    utc_offset: int
    display_city: bool
    pm_private: bool
    osu_path_md5: str
    adapters_str: str
    adapters_md5: str
    uninstall_md5: str
    disk_signature_md5: str


def parse_login_data(raw_login_data: bytes) -> LoginData:
    (
        username,
        password_md5,
        remainder,
    ) = raw_login_data.decode().split("\n", maxsplit=2)

    (
        osu_version,
        utc_offset,
        display_city,
        client_hashes,
        pm_private,
    ) = remainder.split("|", maxsplit=4)

    (
        osu_path_md5,
        adapters_str,
        adapters_md5,
        uninstall_md5,
        disk_signature_md5,
    ) = client_hashes[:-1].split(":", maxsplit=4)

    return {
        "username": username,
        "password_md5": password_md5.encode(),
        "osu_version": osu_version,
        "utc_offset": int(utc_offset),
        "display_city": display_city == "1",
        "pm_private": pm_private == "1",
        "osu_path_md5": osu_path_md5,
        "adapters_str": adapters_str,
        "adapters_md5": adapters_md5,
        "uninstall_md5": uninstall_md5,
        "disk_signature_md5": disk_signature_md5,
    }


@unique
class ClientPackets(IntEnum):
    """
    Packet IDs that the osu! client sends to the server.

    These are organized by functionality:
    - 0-9: User status and messaging
    - 10-15: Spectating
    - 16-27: Channel and chat
    - 28-35: Match/lobby
    - 36-50: Multiplayer match
    - 51-61: Match gameplay
    - 62-70: Beatmaps and friends
    - 71-82: User features
    - 83-95: Presence and settings
    - 96-109: Tournament and advanced features
    """

    # ===================
    # User & Messaging
    # ===================

    UNKNOWN_PACKET = -1  # Unmapped packet

    CHANGE_ACTION = 0  # User status change (playing, idle, etc.)
    SEND_PUBLIC_MESSAGE = 1  # Send message to a channel
    LOGOUT = 2  # Player logout
    REQUEST_STATUS_UPDATE = 3  # Request user status update
    PING = 4  # Keepalive ping

    # ===================
    # Spectating
    # ===================

    START_SPECTATING = 16  # Start spectating a player
    STOP_SPECTATING = 17  # Stop spectating
    SPECTATE_FRAMES = 18  # Spectator frame data
    ERROR_REPORT = 20  # Client error report
    CANT_SPECTATE = 21  # Cannot spectate (in game)

    # ===================
    # Private Messaging
    # ===================

    SEND_PRIVATE_MESSAGE = 25  # Send DM to a player

    # ===================
    # Lobby
    # ===================

    PART_LOBBY = 29  # Leave the lobby
    JOIN_LOBBY = 30  # Join the lobby

    # ===================
    # Match
    # ===================

    CREATE_MATCH = 31  # Create multiplayer match
    JOIN_MATCH = 32  # Join a match
    PART_MATCH = 33  # Leave a match

    MATCH_CHANGE_SLOT = 38  # Change slot in match
    MATCH_READY = 39  # Ready up in match
    MATCH_LOCK = 40  # Lock/unlock slot
    MATCH_CHANGE_SETTINGS = 41  # Change match settings
    MATCH_START = 44  # Start match
    MATCH_SCORE_UPDATE = 47  # Update score during play
    MATCH_COMPLETE = 49  # Match finished

    # ===================
    # Match Mods & Gameplay
    # ===================

    MATCH_CHANGE_MODS = 51  # Change mods in match
    MATCH_LOAD_COMPLETE = 52  # Finished loading beatmap
    MATCH_NO_BEATMAP = 54  # No beatmap selected
    MATCH_NOT_READY = 55  # Not ready in match
    MATCH_FAILED = 56  # Player failed
    MATCH_HAS_BEATMAP = 59  # Has beatmap selected
    MATCH_SKIP_REQUEST = 60  # Request to skip

    # ===================
    # Channels
    # ===================

    CHANNEL_JOIN = 63  # Join a channel
    CHANNEL_PART = 78  # Leave a channel
    RECEIVE_UPDATES = 79  # Toggle receiving updates

    # ===================
    # Beatmaps & Info
    # ===================

    BEATMAP_INFO_REQUEST = 68  # Request beatmap info
    MATCH_TRANSFER_HOST = 70  # Transfer host in match

    # ===================
    # Friends
    # ===================

    FRIEND_ADD = 73  # Add friend
    FRIEND_REMOVE = 74  # Remove friend

    # ===================
    # Match Teams
    # ===================

    MATCH_CHANGE_TEAM = 77  # Change team in match

    # ===================
    # User Status
    # ===================

    SET_AWAY_MESSAGE = 82  # Set away message
    IRC_ONLY = 84  # IRC only mode
    USER_STATS_REQUEST = 85  # Request user stats

    # ===================
    # Match Invites
    # ===================

    MATCH_INVITE = 87  # Invite to match
    MATCH_CHANGE_PASSWORD = 90  # Change match password

    # ===================
    # Tournament
    # ===================

    TOURNAMENT_MATCH_INFO_REQUEST = 93  # Tournament match info
    TOURNAMENT_JOIN_MATCH_CHANNEL = 108  # Join tournament match channel
    TOURNAMENT_LEAVE_MATCH_CHANNEL = 109  # Leave tournament match channel

    # ===================
    # Presence
    # ===================

    USER_PRESENCE_REQUEST = 97  # Request user presence
    USER_PRESENCE_REQUEST_ALL = 98  # Request all users' presence

    # ===================
    # Settings
    # ===================

    TOGGLE_BLOCK_NON_FRIEND_DMS = 99  # Block DMs from non-friends


class PacketHeader(TypedDict):
    packet_id: int
    packet_length: int


@dataclass
class Packet:
    _id: ClientPackets

    raw_data: bytes
    offset: int  # = 0

    def __repr__(self) -> str:
        return f"<Packet id={self._id} raw_data={self.raw_data} offset={self.offset}>"

    @property
    def remaining_data(self) -> bytes:
        return self.raw_data[self.offset :]

    def read(self) -> int:
        base_fields = {"_id", "raw_data", "offset"}
        type_hints = get_type_hints(type(self))

        for dataclass_field in fields(self):
            if dataclass_field.name in base_fields:
                continue

            data_type: osuBaseType = type_hints[dataclass_field.name]
            data, offset = data_type.osu_protocol_deserialize(self.remaining_data)

            setattr(self, dataclass_field.name, data)
            self.offset += offset

        return self.offset


READABLE_PACKETS: dict[ClientPackets, Type[Packet]] = {}

PacketClass = TypeVar("PacketClass", bound=Type[Packet])


def handles(packet_id: ClientPackets) -> Callable[[PacketClass], PacketClass]:
    def inner(cls: PacketClass) -> PacketClass:
        READABLE_PACKETS[packet_id] = cls
        return cls

    return inner


@handles(ClientPackets.CHANGE_ACTION)
@dataclass
class ChangeAction(Packet):
    action: osuUnsignedChar = field(init=False)
    info_text: osuString = field(init=False)
    beatmap_md5: osuString = field(init=False)
    current_mods: osuIntUnsigned32Bit = field(init=False)
    current_game_mode: osuUnsignedChar = field(init=False)
    beatmap_id: osuIntSigned32Bit = field(init=False)

    def __repr__(self) -> str:
        return pformat(
            {
                "action": self.action,
                "info_text": self.info_text,
                "beatmap_md5": self.beatmap_md5,
                "current_mods": self.current_mods,
                "current_game_mode": self.current_game_mode,
                "beatmap_id": self.beatmap_id,
            }
        )


@handles(ClientPackets.LOGOUT)
@dataclass
class LogOut(Packet):
    padding: osuIntSigned32Bit = field(init=False)


@handles(ClientPackets.PING)
@dataclass
class Ping(Packet):
    pass

    def __repr__(self) -> str:
        return "<Ping Packet>"


@handles(ClientPackets.USER_STATS_REQUEST)
@dataclass
class UserStatsRequest(Packet):
    user_ids: osuIntUnSigned32List = field(init=False)


@handles(ClientPackets.FRIEND_REMOVE)
@dataclass
class FriendRemove(Packet):
    friend_user_id: osuIntSigned32Bit = field(init=False)


@handles(ClientPackets.FRIEND_ADD)
@dataclass
class FriendAdd(Packet):
    friend_user_id: osuIntSigned32Bit = field(init=False)


@handles(ClientPackets.SEND_PUBLIC_MESSAGE)
@dataclass
class SendPublicMessage(Packet):
    sender: osuString = field(init=False)
    text: osuString = field(init=False)
    reciever: osuString = field(init=False)
    sender_id: osuIntSigned32Bit = field(init=False)


@handles(ClientPackets.SEND_PRIVATE_MESSAGE)
@dataclass
class SendPrivateMessage(Packet):
    sender: osuString = field(init=False)
    text: osuString = field(init=False)
    reciever: osuString = field(init=False)
    sender_id: osuIntSigned32Bit = field(init=False)


class Packets(list[Packet]):
    def __init__(self, raw_packet_data: bytes) -> None:
        self.raw_packet_data = raw_packet_data
        self.offset: int = 0
        super().__init__()

    @property
    def remaining_data(self) -> bytes:
        return self.raw_packet_data[self.offset :]

    def read_packet_header(self) -> PacketHeader:
        packet_header = struct.unpack_from("<HxI", self.remaining_data)
        self.offset += 7

        packet_id, packet_length = packet_header
        return {"packet_id": packet_id, "packet_length": packet_length}

    def read(self) -> None:
        while self.remaining_data:
            packet_header = self.read_packet_header()
            packet_id_raw = packet_header["packet_id"]
            packet_length = packet_header["packet_length"]

            try:
                packet_id = ClientPackets(packet_id_raw)
            except ValueError:
                # log.warning(f"Skipping unknown packet ID: {packet_id_raw}")
                self.offset += packet_length
                continue

            if packet_id not in READABLE_PACKETS:
                # log.warning(f"Skipping unimplemented packet with ID: {packet_id.name}")
                self.offset += packet_length
                continue

            packet = READABLE_PACKETS[packet_id](
                _id=packet_id,
                offset=0,
                raw_data=self.remaining_data[: packet_header["packet_length"]],
            )
            packet.read()

            self.offset += packet_length
            self.append(packet)
