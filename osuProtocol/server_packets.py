"""
Purpose/Domain/Concept:
- This module defines the packet IDs for packets sent BY the server TO the osu! client.
- It also provides convenient packet builder functions.
"""

import base64
from enum import IntEnum, IntFlag, unique

import ossapi

from osuProtocol.osuTypes import (
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


def bytes_to_string(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def string_to_bytes(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


@unique
class ServerPackets(IntEnum):
    """
    Packet IDs that the server sends to the osu! client.

    These are organized by functionality:
    - 5-12: User and login
    - 13-15: Spectating
    - 19-24: Notifications and updates
    - 26-28: Match updates
    - 34-37: Match join
    - 42-43: Spectator updates
    - 45-50: Match gameplay
    - 53-61: Match state
    - 64-67: Channels
    - 69-72: Beatmaps and friends
    - 75-81: Protocol and menu
    - 83-92: Presence and user
    - 94-107: Advanced features
    """

    # ===================
    # Login & User
    # ===================

    USER_ID = 5  # Login response (user ID or negative for error)
    USER_LOGOUT = 12  # Player logout notification

    # ===================
    # Messaging
    # ===================

    SEND_MESSAGE = 7  # Send a message (chat)
    PONG = 8  # Pong response to ping

    # ===================
    # Spectating
    # ===================

    SPECTATOR_JOINED = 13  # Spectator joined
    SPECTATOR_LEFT = 14  # Spectator left
    SPECTATE_FRAMES = 15  # Spectator frame data
    SPECTATOR_CANT_SPECTATE = 22  # Cannot spectate

    # ===================
    # Notifications
    # ===================

    VERSION_UPDATE = 19  # Client version update required
    GET_ATTENTION = 23  # Get user's attention
    NOTIFICATION = 24  # Show notification

    # ===================
    # Match Updates
    # ===================

    UPDATE_MATCH = 26  # Update match state
    NEW_MATCH = 27  # New match created
    DISPOSE_MATCH = 28  # Match disposed/removed

    # ===================
    # Match Join
    # ===================

    MATCH_JOIN_SUCCESS = 36  # Successfully joined match
    MATCH_JOIN_FAIL = 37  # Failed to join match

    # ===================
    # Spectator Updates
    # ===================

    FELLOW_SPECTATOR_JOINED = 42  # Fellow spectator joined
    FELLOW_SPECTATOR_LEFT = 43  # Fellow spectator left

    # ===================
    # Match Gameplay
    # ===================

    ALL_PLAYERS_LOADED = 45  # All players loaded
    MATCH_START = 46  # Match started
    MATCH_SCORE_UPDATE = 48  # Score update
    MATCH_TRANSFER_HOST = 50  # Host transferred

    # ===================
    # Match State
    # ===================

    MATCH_ALL_PLAYERS_LOADED = 53  # All players loaded
    MATCH_PLAYER_FAILED = 57  # Player failed
    MATCH_COMPLETE = 58  # Match complete
    MATCH_SKIP = 61  # Skip to next section
    MATCH_PLAYER_SKIPPED = 81  # Player skipped

    # ===================
    # Channels
    # ===================

    CHANNEL_JOIN_SUCCESS = 64  # Successfully joined channel
    CHANNEL_INFO = 65  # Channel info
    CHANNEL_KICK = 66  # Kicked from channel
    CHANNEL_AUTO_JOIN = 67  # Auto-join channel
    CHANNEL_INFO_END = 89  # End of channel list

    # ===================
    # Beatmaps & Stats
    # ===================

    BEATMAP_INFO_REPLY = 69  # Beatmap info response
    USER_STATS = 11  # User statistics

    # ===================
    # Friends
    # ===================

    FRIENDS_LIST = 72  # Friends list

    # ===================
    # Protocol & Menu
    # ===================

    PROTOCOL_VERSION = 75  # Protocol version
    MAIN_MENU_ICON = 76  # Main menu icon
    MONITOR = 80  # (unused)

    # ===================
    # Presence
    # ===================

    USER_PRESENCE = 83  # User presence data
    USER_PRESENCE_SINGLE = 95  # Single user presence
    USER_PRESENCE_BUNDLE = 96  # Bundle of user presences

    # ===================
    # User Status
    # ===================

    USER_SILENCED = 94  # User was silenced

    # ===================
    # Server Commands
    # ===================

    RESTART = 86  # Restart the game
    HANDLE_IRC_CHANGE_USERNAME = 9  # (deprecated)
    HANDLE_IRC_QUIT = 10  # IRC quit

    # ===================
    # Match Features
    # ===================

    MATCH_CHANGE_PASSWORD = 91  # Match password changed
    MATCH_ABORT = 106  # Match aborted

    # ===================
    # Friends & DM
    # ===================

    TOGGLE_BLOCK_NON_FRIEND_DMS = 34  # Toggle blocking DMs
    PRIVILEGES = 71  # User privileges
    USER_DM_BLOCKED = 100  # DM blocked
    TARGET_IS_SILENCED = 101  # Target is silenced

    # ===================
    # Version
    # ===================

    VERSION_UPDATE_FORCED = 102  # Forced version update

    # ===================
    # Server Switch
    # ===================

    SWITCH_SERVER = 103  # Switch to another server
    ACCOUNT_RESTRICTED = 104  # Account restricted
    RTX = 105  # (unused)
    SWITCH_TOURNAMENT_SERVER = 107  # Switch tournament server

    # ===================
    # Silence
    # ===================

    SILENCE_END = 92  # Silence period ended

    # ===================
    # Tournament
    # ===================

    UNAUTHORIZED = 62  # (unused)

    def to_osu_protocol(self) -> bytes:
        return self.value.to_bytes(2, "little", signed=False)


class PlayerPrivileges(IntFlag):
    # << shift bits to the left
    # PLAYER = 1 << 0
    NORMAL = 1 << 0

    MODERATOR = 1 << 1
    """
    0000 0001  (1)
    0000 0010  (2)
    """

    SUPPORTER = 1 << 2
    OWNER = 1 << 3
    DEVELOPER = 1 << 4
    TOURNAMENT = 1 << 5


ALL_PRIVILEGES = (
    PlayerPrivileges.NORMAL
    | PlayerPrivileges.MODERATOR
    | PlayerPrivileges.SUPPORTER
    | PlayerPrivileges.OWNER
    | PlayerPrivileges.DEVELOPER
    | PlayerPrivileges.TOURNAMENT
)


@unique
class LoginFailureReason(IntEnum):
    """Reasons for login failure (negative user IDs)."""

    AUTHENTICATION_FAILED = -1
    OLD_CLIENT = -2
    BANNED = -3
    ERROR_OCCURRED = -5
    NEEDS_SUPPORTER = -6
    PASSWORD_RESET = -7
    REQUIRES_VERIFICATION = -8


@unique
class osuGameMode(IntEnum):
    STANDARD = 0
    TAIKO = 1
    CATCH_THE_BEAT = 2
    MANIA = 3

    def to_api_v2(self) -> ossapi.GameMode:
        return {
            self.STANDARD: ossapi.GameMode.OSU,
            self.TAIKO: ossapi.GameMode.TAIKO,
            self.CATCH_THE_BEAT: ossapi.GameMode.CATCH,
            self.MANIA: ossapi.GameMode.MANIA,
        }[self]

    @classmethod
    def from_osu_file(cls, mode: int) -> "osuGameMode":
        return {0: cls.STANDARD, 1: cls.TAIKO, 2: cls.CATCH_THE_BEAT, 3: cls.MANIA}[
            mode
        ]

    @classmethod
    def from_api_v2(cls, mode: ossapi.GameMode) -> "osuGameMode":
        return {
            ossapi.GameMode.OSU: cls.STANDARD,
            ossapi.GameMode.TAIKO: cls.TAIKO,
            ossapi.GameMode.CATCH: cls.CATCH_THE_BEAT,
            ossapi.GameMode.MANIA: cls.MANIA,
        }[mode]


@unique
class osuAction(IntEnum):
    """The client's current status"""

    Idle = 0
    Afk = 1
    Playing = 2
    Editing = 3
    Modding = 4
    Multiplayer = 5
    Watching = 6
    Unknown = 7
    Testing = 8
    Submitting = 9
    Paused = 10
    Lobby = 11
    Multiplaying = 12
    OsuDirect = 13


class LazerSpecificMod(Exception):
    pass


@unique
class osuMods(IntFlag):
    NOMOD = 0
    NOFAIL = 1 << 0
    EASY = 1 << 1
    TOUCHSCREEN = 1 << 2  # old: 'NOVIDEO'
    HIDDEN = 1 << 3
    HARDROCK = 1 << 4
    SUDDENDEATH = 1 << 5
    DOUBLETIME = 1 << 6
    RELAX = 1 << 7
    HALFTIME = 1 << 8
    NIGHTCORE = 1 << 9
    FLASHLIGHT = 1 << 10
    AUTOPLAY = 1 << 11
    SPUNOUT = 1 << 12
    AUTOPILOT = 1 << 13
    PERFECT = 1 << 14
    KEY4 = 1 << 15
    KEY5 = 1 << 16
    KEY6 = 1 << 17
    KEY7 = 1 << 18
    KEY8 = 1 << 19
    FADEIN = 1 << 20
    RANDOM = 1 << 21
    CINEMA = 1 << 22
    TARGET = 1 << 23
    KEY9 = 1 << 24
    KEYCOOP = 1 << 25
    KEY1 = 1 << 26
    KEY3 = 1 << 27
    KEY2 = 1 << 28
    SCOREV2 = 1 << 29
    MIRROR = 1 << 30

    def to_acronym_list(self) -> list[str]:
        acronym_mapping = {
            self.DOUBLETIME: "DT",
            self.NIGHTCORE: "NC",
            self.HARDROCK: "HR",
            self.HIDDEN: "HD",
            self.FLASHLIGHT: "FL",
            self.EASY: "EZ",
            self.NOFAIL: "NF",
            self.SUDDENDEATH: "SD",
            self.TOUCHSCREEN: "TD",
            self.RELAX: "RX",
            self.HALFTIME: "HT",
            self.AUTOPLAY: "AU",
            self.SPUNOUT: "SO",
            self.AUTOPILOT: "AP",
            self.PERFECT: "PF",
            self.KEY4: "4K",
            self.KEY5: "5K",
            self.KEY6: "6K",
            self.KEY7: "7K",
            self.KEY8: "8K",
            self.FADEIN: "FI",
            self.RANDOM: "RN",
            self.CINEMA: "CM",
            self.TARGET: "TP",
            self.KEY9: "9K",
            self.KEYCOOP: "COOP",
            self.KEY1: "1K",
            self.KEY3: "3K",
            self.KEY2: "2K",
            self.SCOREV2: "SV2",
            self.MIRROR: "MR",
        }

        acronyms = []
        for mod in osuMods:
            if mod != osuMods.NOMOD and (self & mod) == mod:
                acronyms.append(acronym_mapping[mod])

        return acronyms

    @classmethod
    def from_acronym(cls, acronym: str) -> "osuMods":
        try:
            return {
                "DT": cls.DOUBLETIME,
                "NC": cls.NIGHTCORE,
                "HR": cls.HARDROCK,
                "HD": cls.HIDDEN,
                "FL": cls.FLASHLIGHT,
                "EZ": cls.EASY,
                "NF": cls.NOFAIL,
                "SD": cls.SUDDENDEATH,
                "TD": cls.TOUCHSCREEN,
                "RX": cls.RELAX,
                "HT": cls.HALFTIME,
                "AU": cls.AUTOPLAY,
                "SO": cls.SPUNOUT,
                "AP": cls.AUTOPILOT,
                "PF": cls.PERFECT,
                "4K": cls.KEY4,
                "5K": cls.KEY5,
                "6K": cls.KEY6,
                "7K": cls.KEY7,
                "8K": cls.KEY8,
                "FI": cls.FADEIN,
                "RN": cls.RANDOM,
                "CM": cls.CINEMA,
                "TP": cls.TARGET,
                "9K": cls.KEY9,
                "COOP": cls.KEYCOOP,
                "1K": cls.KEY1,
                "3K": cls.KEY3,
                "2K": cls.KEY2,
                "SV2": cls.SCOREV2,
                "MR": cls.MIRROR,
            }[acronym.strip().upper()]
        except KeyError:
            raise ValueError(f"Invalid mod acronym: {acronym}")


@unique
class osuCountryCode(IntEnum):
    OC = 1
    EU = 2
    AD = 3
    AE = 4
    AF = 5
    AG = 6
    AI = 7
    AL = 8
    AM = 9
    AN = 10
    AO = 11
    AQ = 12
    AR = 13
    AS = 14
    AT = 15
    AU = 16
    AW = 17
    AZ = 18
    BA = 19
    BB = 20
    BD = 21
    BE = 22
    BF = 23
    BG = 24
    BH = 25
    BI = 26
    BJ = 27
    BM = 28
    BN = 29
    BO = 30
    BR = 31
    BS = 32
    BT = 33
    BV = 34
    BW = 35
    BY = 36
    BZ = 37
    CA = 38
    CC = 39
    CD = 40
    CF = 41
    CG = 42
    CH = 43
    CI = 44
    CK = 45
    CL = 46
    CM = 47
    CN = 48
    CO = 49
    CR = 50
    CU = 51
    CV = 52
    CX = 53
    CY = 54
    CZ = 55
    DE = 56
    DJ = 57
    DK = 58
    DM = 59
    DO = 60
    DZ = 61
    EC = 62
    EE = 63
    EG = 64
    EH = 65
    ER = 66
    ES = 67
    ET = 68
    FI = 69
    FJ = 70
    FK = 71
    FM = 72
    FO = 73
    FR = 74
    FX = 75
    GA = 76
    GB = 77
    GD = 78
    GE = 79
    GF = 80
    GH = 81
    GI = 82
    GL = 83
    GM = 84
    GN = 85
    GP = 86
    GQ = 87
    GR = 88
    GS = 89
    GT = 90
    GU = 91
    GW = 92
    GY = 93
    HK = 94
    HM = 95
    HN = 96
    HR = 97
    HT = 98
    HU = 99
    ID = 100
    IE = 101
    IL = 102
    IN = 103
    IO = 104
    IQ = 105
    IR = 106
    IS = 107
    IT = 108
    JM = 109
    JO = 110
    JP = 111
    KE = 112
    KG = 113
    KH = 114
    KI = 115
    KM = 116
    KN = 117
    KP = 118
    KR = 119
    KW = 120
    KY = 121
    KZ = 122
    LA = 123
    LB = 124
    LC = 125
    LI = 126
    LK = 127
    LR = 128
    LS = 129
    LT = 130
    LU = 131
    LV = 132
    LY = 133
    MA = 134
    MC = 135
    MD = 136
    MG = 137
    MH = 138
    MK = 139
    ML = 140
    MM = 141
    MN = 142
    MO = 143
    MP = 144
    MQ = 145
    MR = 146
    MS = 147
    MT = 148
    MU = 149
    MV = 150
    MW = 151
    MX = 152
    MY = 153
    MZ = 154
    NA = 155
    NC = 156
    NE = 157
    NF = 158
    NG = 159
    NI = 160
    NL = 161
    NO = 162
    NP = 163
    NR = 164
    NU = 165
    NZ = 166
    OM = 167
    PA = 168
    PE = 169
    PF = 170
    PG = 171
    PH = 172
    PK = 173
    PL = 174
    PM = 175
    PN = 176
    PR = 177
    PS = 178
    PT = 179
    PW = 180
    PY = 181
    QA = 182
    RE = 183
    RO = 184
    RU = 185
    RW = 186
    SA = 187
    SB = 188
    SC = 189
    SD = 190
    SE = 191
    SG = 192
    SH = 193
    SI = 194
    SJ = 195
    SK = 196
    SL = 197
    SM = 198
    SN = 199
    SO = 200
    SR = 201
    ST = 202
    SV = 203
    SY = 204
    SZ = 205
    TC = 206
    TD = 207
    TF = 208
    TG = 209
    TH = 210
    TJ = 211
    TK = 212
    TM = 213
    TN = 214
    TO = 215
    TL = 216
    TR = 217
    TT = 218
    TV = 219
    TW = 220
    TZ = 221
    UA = 222
    UG = 223
    UM = 224
    US = 225
    UY = 226
    UZ = 227
    VA = 228
    VC = 229
    VE = 230
    VG = 231
    VI = 232
    VN = 233
    VU = 234
    WF = 235
    WS = 236
    YE = 237
    YT = 238
    RS = 239
    ZA = 240
    ZM = 241
    ME = 242
    ZW = 243
    XX = 244
    A2 = 245
    O1 = 246
    AX = 247
    GG = 248
    IM = 249
    JE = 250
    BL = 251
    MF = 252

    # now allow a method to convert from str to osuCountryCode
    @classmethod
    def from_str(cls, country_code_str: str) -> "osuCountryCode":
        try:
            return cls[country_code_str]
        except KeyError:
            raise ValueError(f"Invalid country code: {country_code_str}")


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

    def __iadd__(self, other: "Packet | Packets") -> "Packets":
        if isinstance(other, Packets):
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
        game_mode: osuGameMode,
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
        mods: osuMods,
        game_mode: osuGameMode,
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


class ClientRelog(Packet):
    def __init__(self, millisecond_delay: int) -> None:
        super().__init__(
            _id=ServerPackets.RESTART,
            data={"millisecond_delay": osuIntSigned32Bit(millisecond_delay)},
        )


def LoginFailed(reason: LoginFailureReason, message: str | None = None) -> Packets:
    packets = Packets()

    packets += UserID(LoginFailureReason.AUTHENTICATION_FAILED)
    if message is not None:
        packets += Notification(message)

    return packets


def LoginAuthFailed(message: str | None = None) -> Packets:
    return LoginFailed(LoginFailureReason.AUTHENTICATION_FAILED, message)


def LoginError(message: str | None = None) -> Packets:
    return LoginFailed(LoginFailureReason.ERROR_OCCURRED, message)


def BanchoBot(latency: float | None = None) -> Packets:
    if latency is not None:
        info_text = f"API V2 latency: {latency:.2f}ms ʕ•̫͡•ʔ"
    else:
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
        mods=osuMods.NOMOD,
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


def Login(
    username: str,
    friend_ids: list[int],
    utc_offset: int,
    country_code: osuCountryCode,
    game_mode: osuGameMode,
    longitude: float,
    latitude: float,
    rank: int,
    ranked_score: int,
    accuracy: float,
    play_count: int,
    total_score: int,
    performance_points: int,
    login_message: str | None = None,
    latency: float | None = None,
) -> Packets:
    packets = Packets()

    packets += UserID(2)
    packets += ProtocolVersion(19)

    packets += UserPrivileges(ALL_PRIVILEGES)

    if login_message is not None:
        packets += Notification(login_message)

    for channel in ["#osu", "#nothing"]:
        packets += ChannelInfo(
            name=channel, topic=f"Welcome to {channel}!", player_count=1
        )

    packets += ReOrderChannels()

    packets += MainMenuIcon(
        icon_url="https://a.ppy.sh/13028687",
        on_click_url="https://github.com/jeevanjohnson/local-osu-server",
    )

    packets += UserFriendList(friend_ids)

    packets += PlayerPresence(
        user_id=2,
        username=username,
        utc_offset=utc_offset,
        country_code=country_code,
        user_privileges=ALL_PRIVILEGES,
        game_mode=game_mode,
        longitude=longitude,
        latitude=latitude,
        rank=rank,
    )

    packets += PlayerStats(
        user_id=2,
        action=osuAction.Idle,
        info_text="",
        beatmap_md5="",
        mods=osuMods.NOMOD,
        game_mode=game_mode,
        beatmap_id=0,
        ranked_score=ranked_score,
        accuracy=accuracy,
        play_count=play_count,
        total_score=total_score,
        rank=rank,
        performance_points=performance_points,
    )

    packets += BanchoBot(latency=latency)

    return packets


def Relog(message: str | None = None) -> Packets:
    packets = Packets()

    if message is not None:
        packets += Notification(message)

    packets += ClientRelog(0)

    return packets


SilentRelog = Relog()
