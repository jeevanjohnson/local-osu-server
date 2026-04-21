from enum import IntEnum, unique, IntFlag

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