"""
Purpose/Domain/Concept:
- This module defines the packet IDs for packets sent BY the server TO the osu! client.
- It also provides convenient packet builder functions.
"""

import base64

from core.adapters.osu_protocol.domain.enums import (
    osuCountryCode,
    osuGameMode,
    osuMods,
)
from core.adapters.osu_protocol.cho.enums import (
    ALL_PRIVILEGES,
    LoginFailureReason,
    osuAction,
    ServerPackets,
)
from core.adapters.osu_protocol.cho.types import (
    osuAccuracy,
    osuBaseType,
    osuByteArray,
    osuFloat32Bit,
    osuFriendList,
    osuIntSigned32Bit,
    osuIntUnsigned32Bit,
    osuIntUnsigned64Bit,
    osuMainMenuIcon,
    osuShort,
    osuString,
    osuUnsignedChar,
    osuUTCOffset,
)
from typing import Iterable


def bytes_to_string(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def string_to_bytes(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))

class Packet:
    def __init__(self, _id: ServerPackets, data: dict[str, osuBaseType]) -> None:

        self._id: ServerPackets = _id
        self.data: dict[str, osuBaseType] = data

    def raw_data(self) -> bytes:
        raw_data = osuByteArray()

        for parameter in self.data.values():
            raw_data += parameter

        return bytes(raw_data)

    def osu_protocol_packet_data_length(self) -> bytes:
        length_of_raw_data = len(self.raw_data())
        return length_of_raw_data.to_bytes(4, "little", signed=False)

    def osu_protocol_padding(self) -> bytes:
        return b"\x00"

    def build(self) -> bytes:
        raw_packet = bytearray()

        raw_packet += self._id.to_osu_protocol()
        raw_packet += self.osu_protocol_padding()
        raw_packet += self.osu_protocol_packet_data_length()
        raw_packet += self.raw_data()

        return bytes(raw_packet)

    def build_str(self) -> str:
        return bytes_to_string(self.build())


class Packets(list[Packet]):
    def build_str(self) -> str:
        return bytes_to_string(self.build())

    def build(self) -> bytes:
        raw_data = bytearray()

        for packet in self:
            raw_data += packet.build()

        return bytes(raw_data)

    def __iadd__(self, other: "Packet | Iterable[Packet]") -> "Packets":
        if isinstance(other, Iterable):
            self.extend(other)
        else:
            self.append(other)

        return self


class UserID(Packet):
    def __init__(self, user_id: int) -> None:
        super().__init__(
            _id=ServerPackets.USER_ID, data={"user_id": osuIntSigned32Bit(user_id)}
        )


LOGIN_FAILED = UserID(LoginFailureReason.AUTHENTICATION_FAILED)


class Notification(Packet):
    def __init__(self, message: str) -> None:
        super().__init__(
            _id=ServerPackets.NOTIFICATION, data={"message": osuString(message)}
        )


class ProtocolVersion(Packet):
    def __init__(self, version: int) -> None:
        super().__init__(
            _id=ServerPackets.PROTOCOL_VERSION,
            data={"version": osuIntUnsigned32Bit(version)},
        )


class UserPrivileges(Packet):
    def __init__(self, privileges: int) -> None:
        super().__init__(
            _id=ServerPackets.PRIVILEGES,
            data={"privileges": osuIntUnsigned32Bit(privileges)},
        )


class ChannelInfo(Packet):
    def __init__(self, name: str, topic: str, player_count: int) -> None:
        super().__init__(
            _id=ServerPackets.CHANNEL_INFO,
            data={
                "name": osuString(name),
                "topic": osuString(topic),
                "player_count": osuShort(player_count),
            },
        )


class ReOrderChannels(Packet):
    def __init__(self) -> None:
        super().__init__(_id=ServerPackets.CHANNEL_INFO_END, data={})


class MainMenuIcon(Packet):
    def __init__(self, icon_url: str, on_click_url: str) -> None:
        super().__init__(
            _id=ServerPackets.MAIN_MENU_ICON,
            data={
                "icon": osuMainMenuIcon(icon_url=icon_url, on_click_url=on_click_url)
            },
        )


class UserFriendList(Packet):
    def __init__(self, friend_ids: list[int]) -> None:
        super().__init__(
            _id=ServerPackets.FRIENDS_LIST,
            data={"friend_ids": osuFriendList(friend_ids)},
        )


class PlayerPresence(Packet):
    def __init__(
        self,
        user_id: int,
        username: str,
        utc_offset: int,
        country_code: osuCountryCode,
        user_privileges: int,
        game_mode: int,
        longitude: float,
        latitude: float,
        rank: int,
    ) -> None:
        super().__init__(
            _id=ServerPackets.USER_PRESENCE,
            data={
                "user_id": osuIntUnsigned32Bit(user_id),
                "username": osuString(username),
                "utc_offset": osuUTCOffset(utc_offset),
                "country_code": osuUnsignedChar(country_code),
                "user_privileges_and_gamemode": osuUnsignedChar(
                    user_privileges | game_mode << 5
                ),
                "longitude": osuFloat32Bit(longitude),
                "latitude": osuFloat32Bit(latitude),
                "rank": osuIntUnsigned32Bit(rank),
            },
        )


class PlayerStats(Packet):
    def __init__(
        self,
        user_id: int,
        action: osuAction,
        info_text: str,
        beatmap_md5: str,
        mods: int,
        game_mode: int,
        beatmap_id: int,
        ranked_score: int,
        accuracy: float,
        play_count: int,
        total_score: int,
        rank: int,
        performance_points: int,
    ) -> None:
        super().__init__(
            _id=ServerPackets.USER_STATS,
            data={
                "user_id": osuIntUnsigned32Bit(user_id),
                "action": osuUnsignedChar(action),
                "info_text": osuString(info_text),
                "beatmap_md5": osuString(beatmap_md5),
                "mods": osuIntSigned32Bit(mods),
                "game_mode": osuUnsignedChar(game_mode),
                "beatmap_id": osuIntSigned32Bit(beatmap_id),
                "ranked_score": osuIntUnsigned64Bit(ranked_score),
                "accuracy": osuAccuracy(accuracy),
                "play_count": osuIntUnsigned32Bit(play_count),
                "total_score": osuIntUnsigned64Bit(total_score),
                "rank": osuIntSigned32Bit(rank),
                "performance_points": osuShort(performance_points),
            },
        )


class ClientReset(Packet):
    def __init__(self, millisecond_delay: int) -> None:
        super().__init__(
            _id=ServerPackets.RESTART,
            data={"millisecond_delay": osuIntSigned32Bit(millisecond_delay)},
        )


class LogOut(Packet):
    def __init__(self, user_id: int) -> None:
        super().__init__(
            _id=ServerPackets.USER_LOGOUT,
            data={
                "user_id": osuIntSigned32Bit(user_id),
                "padding": osuUnsignedChar(0),
            },
        )


class Message(Packet):
    def __init__(
        self, sender: str, message: str, recipient: str, sender_id: int
    ) -> None:
        super().__init__(
            _id=ServerPackets.SEND_MESSAGE,
            data={
                "sender": osuString(sender),
                "message": osuString(message),
                "recipient": osuString(recipient),
                "sender_id": osuIntSigned32Bit(sender_id),
            },
        )


def login_failed(reason: str | None = None) -> Packets:
    packets = Packets()

    packets += UserID(LoginFailureReason.AUTHENTICATION_FAILED)
    if reason is not None:
        packets += Notification(reason)

    return packets

def bancho_user(
    user_id: int,
    username: str,
    country_code: osuCountryCode,
    game_mode: osuGameMode,
    rank: int,
    action: osuAction,
    info_text: str,
    beatmap_md5: str,
    mods: int,
    beatmap_id: int,
    ranked_score: int,
    accuracy: float,
    play_count: int,
    total_score: int,
    performance_points: int,
    presence_aware: bool,
) -> Packets:
    packets = Packets()

    if presence_aware:
        packets += PlayerPresence(
            user_id=user_id,
            username=username,
            utc_offset=0,
            country_code=country_code,
            user_privileges=ALL_PRIVILEGES,
            game_mode=game_mode,
            longitude=0.0,
            latitude=0.0,
            rank=rank,
        )

    packets += PlayerStats(
        user_id=user_id,
        action=action,
        info_text=info_text,
        beatmap_md5=beatmap_md5,
        mods=mods,
        game_mode=game_mode,
        beatmap_id=beatmap_id,
        ranked_score=ranked_score,
        accuracy=accuracy,
        play_count=play_count,
        total_score=total_score,
        rank=rank,
        performance_points=performance_points,
    )

    return packets


def bancho_bot() -> Packets:
    info_text = "over the server... ʕ•̫͡•ʔ"

    packets = Packets()

    packets += PlayerPresence(
        user_id=3,
        username="BanchoBot",
        utc_offset=0,
        country_code=osuCountryCode.NA,
        user_privileges=ALL_PRIVILEGES,
        game_mode=osuGameMode.STANDARD,
        longitude=0.0,
        latitude=0.0,
        rank=0,
    )

    packets += PlayerStats(
        user_id=3,
        action=osuAction.Watching,
        info_text=info_text,
        beatmap_md5="",
        mods=0,
        game_mode=osuGameMode.STANDARD,
        beatmap_id=0,
        ranked_score=0,
        accuracy=0.0,
        play_count=0,
        total_score=0,
        rank=0,
        performance_points=0,
    )

    return packets


def reset(message: str | None = None) -> Packets:
    packets = Packets()

    if message is not None:
        packets += Notification(message)

    packets += ClientReset(0)

    return packets
