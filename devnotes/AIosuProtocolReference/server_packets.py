"""
Purpose/Domain/Concept:
- This module defines the packet IDs for packets sent BY the server TO the osu! client.
- It also provides convenient packet builder functions.
"""

from __future__ import annotations

from enum import IntEnum
from enum import unique
from functools import lru_cache

from AIosuProtocolReference.writer import BanchoPacketWriter
from AIosuProtocolReference.types import Message


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
    
    USER_ID = 5                # Login response (user ID or negative for error)
    USER_LOGOUT = 12           # Player logout notification

    # ===================
    # Messaging
    # ===================
    
    SEND_MESSAGE = 7           # Send a message (chat)
    PONG = 8                   # Pong response to ping

    # ===================
    # Spectating
    # ===================
    
    SPECTATOR_JOINED = 13       # Spectator joined
    SPECTATOR_LEFT = 14         # Spectator left
    SPECTATE_FRAMES = 15        # Spectator frame data
    SPECTATOR_CANT_SPECTATE = 22 # Cannot spectate

    # ===================
    # Notifications
    # ===================
    
    VERSION_UPDATE = 19         # Client version update required
    GET_ATTENTION = 23          # Get user's attention
    NOTIFICATION = 24           # Show notification

    # ===================
    # Match Updates
    # ===================
    
    UPDATE_MATCH = 26           # Update match state
    NEW_MATCH = 27              # New match created
    DISPOSE_MATCH = 28          # Match disposed/removed

    # ===================
    # Match Join
    # ===================
    
    MATCH_JOIN_SUCCESS = 36     # Successfully joined match
    MATCH_JOIN_FAIL = 37         # Failed to join match

    # ===================
    # Spectator Updates
    # ===================
    
    FELLOW_SPECTATOR_JOINED = 42 # Fellow spectator joined
    FELLOW_SPECTATOR_LEFT = 43   # Fellow spectator left

    # ===================
    # Match Gameplay
    # ===================
    
    ALL_PLAYERS_LOADED = 45     # All players loaded
    MATCH_START = 46            # Match started
    MATCH_SCORE_UPDATE = 48     # Score update
    MATCH_TRANSFER_HOST = 50    # Host transferred

    # ===================
    # Match State
    # ===================
    
    MATCH_ALL_PLAYERS_LOADED = 53   # All players loaded
    MATCH_PLAYER_FAILED = 57       # Player failed
    MATCH_COMPLETE = 58            # Match complete
    MATCH_SKIP = 61                # Skip to next section
    MATCH_PLAYER_SKIPPED = 81      # Player skipped

    # ===================
    # Channels
    # ===================
    
    CHANNEL_JOIN_SUCCESS = 64   # Successfully joined channel
    CHANNEL_INFO = 65           # Channel info
    CHANNEL_KICK = 66          # Kicked from channel
    CHANNEL_AUTO_JOIN = 67     # Auto-join channel
    CHANNEL_INFO_END = 89      # End of channel list

    # ===================
    # Beatmaps & Stats
    # ===================
    
    BEATMAP_INFO_REPLY = 69     # Beatmap info response
    USER_STATS = 11             # User statistics

    # ===================
    # Friends
    # ===================
    
    FRIENDS_LIST = 72           # Friends list

    # ===================
    # Protocol & Menu
    # ===================
    
    PROTOCOL_VERSION = 75       # Protocol version
    MAIN_MENU_ICON = 76         # Main menu icon
    MONITOR = 80                # (unused)

    # ===================
    # Presence
    # ===================
    
    USER_PRESENCE = 83          # User presence data
    USER_PRESENCE_SINGLE = 95  # Single user presence
    USER_PRESENCE_BUNDLE = 96   # Bundle of user presences

    # ===================
    # User Status
    # ===================
    
    USER_SILENCED = 94          # User was silenced

    # ===================
    # Server Commands
    # ===================
    
    RESTART = 86                # Restart the game
    HANDLE_IRC_CHANGE_USERNAME = 9   # (deprecated)
    HANDLE_IRC_QUIT = 10         # IRC quit

    # ===================
    # Match Features
    # ===================
    
    MATCH_CHANGE_PASSWORD = 91  # Match password changed
    MATCH_ABORT = 106           # Match aborted

    # ===================
    # Friends & DM
    # ===================
    
    TOGGLE_BLOCK_NON_FRIEND_DMS = 34  # Toggle blocking DMs
    PRIVILEGES = 71             # User privileges
    USER_DM_BLOCKED = 100      # DM blocked
    TARGET_IS_SILENCED = 101    # Target is silenced

    # ===================
    # Version
    # ===================
    
    VERSION_UPDATE_FORCED = 102 # Forced version update

    # ===================
    # Server Switch
    # ===================
    
    SWITCH_SERVER = 103         # Switch to another server
    ACCOUNT_RESTRICTED = 104   # Account restricted
    RTX = 105                  # (unused)
    SWITCH_TOURNAMENT_SERVER = 107 # Switch tournament server

    # ===================
    # Silence
    # ===================
    
    SILENCE_END = 92           # Silence period ended

    # ===================
    # Tournament
    # ===================
    
    UNAUTHORIZED = 62           # (unused)

    def __repr__(self) -> str:
        return f"<{self.name} ({self.value})>"


# ===================
# Login Failure Reasons
# ===================

class LoginFailureReason(IntEnum):
    """Reasons for login failure (negative user IDs)."""
    AUTHENTICATION_FAILED = -1
    OLD_CLIENT = -2
    BANNED = -3
    ERROR_OCCURRED = -5
    NEEDS_SUPPORTER = -6
    PASSWORD_RESET = -7
    REQUIRES_VERIFICATION = -8


# ===================
# Packet Builder Functions
# ===================

def build_user_id(user_id: int) -> bytes:
    """
    Build a USER_ID packet.
    
    Positive ID = successful login with that user ID
    Negative ID = login failure (see LoginFailureReason)
    """
    writer = BanchoPacketWriter()
    writer.write_packet(ServerPackets.USER_ID, (user_id, "i32"))
    return writer.get_bytes()


def build_pong() -> bytes:
    """Build a PONG packet (response to client ping)."""
    writer = BanchoPacketWriter()
    writer.write_packet(ServerPackets.PONG)
    return writer.get_bytes()


def build_send_message(sender: str, text: str, recipient: str, sender_id: int) -> bytes:
    """Build a SEND_MESSAGE packet (chat message)."""
    from AIosuProtocolReference.types import Message
    writer = BanchoPacketWriter()
    message = Message(sender, text, recipient, sender_id)
    writer.write_packet(ServerPackets.SEND_MESSAGE, message)
    return writer.get_bytes()


def build_user_stats(
    user_id: int,
    action: int,
    info_text: str,
    map_md5: str,
    mods: int,
    mode: int,
    map_id: int,
    ranked_score: int,
    accuracy: float,
    plays: int,
    total_score: int,
    global_rank: int,
    pp: int,
) -> bytes:
    """Build a USER_STATS packet."""
    writer = BanchoPacketWriter()
    writer.write_packet(
        ServerPackets.USER_STATS,
        (user_id, "i32"),
        (action, "u8"),
        (info_text, "string"),
        (map_md5, "string"),
        (mods, "i32"),
        (mode, "u8"),
        (map_id, "i32"),
        (ranked_score, "i64"),
        (accuracy / 100.0, "f32"),
        (plays, "i32"),
        (total_score, "i64"),
        (global_rank, "i32"),
        (pp, "u16"),
    )
    return writer.get_bytes()


def build_user_logout(user_id: int, timeout: int = 0) -> bytes:
    """Build a USER_LOGOUT packet."""
    writer = BanchoPacketWriter()
    writer.write_packet(
        ServerPackets.USER_LOGOUT,
        (user_id, "i32"),
        (timeout, "u8"),
    )
    return writer.get_bytes()


def build_channel_join_success(channel_name: str) -> bytes:
    """Build a CHANNEL_JOIN_SUCCESS packet."""
    writer = BanchoPacketWriter()
    writer.write_packet(ServerPackets.CHANNEL_JOIN_SUCCESS, (channel_name, "string"))
    return writer.get_bytes()


def build_channel_info(name: str, topic: str, player_count: int) -> bytes:
    """Build a CHANNEL_INFO packet."""
    writer = BanchoPacketWriter()
    writer.write_packet(
        ServerPackets.CHANNEL_INFO,
        (name, "string"),
        (topic, "string"),
        (player_count, "i32"),
    )
    return writer.get_bytes()


def build_channel_info_end() -> bytes:
    """Build a CHANNEL_INFO_END packet (marks end of channel list)."""
    writer = BanchoPacketWriter()
    writer.write_packet(ServerPackets.CHANNEL_INFO_END)
    return writer.get_bytes()


def build_protocol_version(version: int) -> bytes:
    """Build a PROTOCOL_VERSION packet."""
    writer = BanchoPacketWriter()
    writer.write_packet(ServerPackets.PROTOCOL_VERSION, (version, "i32"))
    return writer.get_bytes()


def build_main_menu_icon(url: str, filename: str) -> bytes:
    """Build a MAIN_MENU_ICON packet."""
    writer = BanchoPacketWriter()
    writer.write_packet(
        ServerPackets.MAIN_MENU_ICON,
        (url, "string"),
        (filename, "string"),
    )
    return writer.get_bytes()


def build_friends_list(friends: list[int]) -> bytes:
    """Build a FRIENDS_LIST packet."""
    writer = BanchoPacketWriter()
    writer.write_packet(ServerPackets.FRIENDS_LIST, (len(friends), "i32"))
    for friend_id in friends:
        writer.write_int32(friend_id)
    return writer.get_bytes()


def build_restart(delay_ms: int = 1000) -> bytes:
    """Build a RESTART packet."""
    writer = BanchoPacketWriter()
    writer.write_packet(ServerPackets.RESTART, (delay_ms, "i32"))
    return writer.get_bytes()


def build_notification(message: str) -> bytes:
    """Build a NOTIFICATION packet."""
    writer = BanchoPacketWriter()
    writer.write_packet(ServerPackets.NOTIFICATION, (message, "string"))
    return writer.get_bytes()
