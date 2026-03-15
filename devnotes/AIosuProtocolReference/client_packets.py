"""
Purpose/Domain/Concept:
- This module defines the packet IDs for packets sent BY the osu! client TO the server.
- These are the packets the server needs to READ and handle.
"""

from __future__ import annotations

from enum import IntEnum
from enum import unique


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
    
    CHANGE_ACTION = 0           # User status change (playing, idle, etc.)
    SEND_PUBLIC_MESSAGE = 1    # Send message to a channel
    LOGOUT = 2                 # Player logout
    REQUEST_STATUS_UPDATE = 3 # Request user status update
    PING = 4                   # Keepalive ping

    # ===================
    # Spectating
    # ===================
    
    START_SPECTATING = 16      # Start spectating a player
    STOP_SPECTATING = 17      # Stop spectating
    SPECTATE_FRAMES = 18       # Spectator frame data
    ERROR_REPORT = 20          # Client error report
    CANT_SPECTATE = 21         # Cannot spectate (in game)

    # ===================
    # Private Messaging
    # ===================
    
    SEND_PRIVATE_MESSAGE = 25  # Send DM to a player

    # ===================
    # Lobby
    # ===================
    
    PART_LOBBY = 29            # Leave the lobby
    JOIN_LOBBY = 30            # Join the lobby

    # ===================
    # Match
    # ===================
    
    CREATE_MATCH = 31          # Create multiplayer match
    JOIN_MATCH = 32           # Join a match
    PART_MATCH = 33            # Leave a match

    MATCH_CHANGE_SLOT = 38    # Change slot in match
    MATCH_READY = 39          # Ready up in match
    MATCH_LOCK = 40            # Lock/unlock slot
    MATCH_CHANGE_SETTINGS = 41 # Change match settings
    MATCH_START = 44           # Start match
    MATCH_SCORE_UPDATE = 47    # Update score during play
    MATCH_COMPLETE = 49        # Match finished

    # ===================
    # Match Mods & Gameplay
    # ===================
    
    MATCH_CHANGE_MODS = 51    # Change mods in match
    MATCH_LOAD_COMPLETE = 52  # Finished loading beatmap
    MATCH_NO_BEATMAP = 54      # No beatmap selected
    MATCH_NOT_READY = 55       # Not ready in match
    MATCH_FAILED = 56          # Player failed
    MATCH_HAS_BEATMAP = 59     # Has beatmap selected
    MATCH_SKIP_REQUEST = 60   # Request to skip

    # ===================
    # Channels
    # ===================
    
    CHANNEL_JOIN = 63          # Join a channel
    CHANNEL_PART = 78          # Leave a channel
    RECEIVE_UPDATES = 79       # Toggle receiving updates

    # ===================
    # Beatmaps & Info
    # ===================
    
    BEATMAP_INFO_REQUEST = 68  # Request beatmap info
    MATCH_TRANSFER_HOST = 70   # Transfer host in match

    # ===================
    # Friends
    # ===================
    
    FRIEND_ADD = 73            # Add friend
    FRIEND_REMOVE = 74        # Remove friend

    # ===================
    # Match Teams
    # ===================
    
    MATCH_CHANGE_TEAM = 77     # Change team in match

    # ===================
    # User Status
    # ===================
    
    SET_AWAY_MESSAGE = 82      # Set away message
    IRC_ONLY = 84              # IRC only mode
    USER_STATS_REQUEST = 85    # Request user stats

    # ===================
    # Match Invites
    # ===================
    
    MATCH_INVITE = 87          # Invite to match
    MATCH_CHANGE_PASSWORD = 90 # Change match password

    # ===================
    # Tournament
    # ===================
    
    TOURNAMENT_MATCH_INFO_REQUEST = 93 # Tournament match info
    TOURNAMENT_JOIN_MATCH_CHANNEL = 108 # Join tournament match channel
    TOURNAMENT_LEAVE_MATCH_CHANNEL = 109 # Leave tournament match channel

    # ===================
    # Presence
    # ===================
    
    USER_PRESENCE_REQUEST = 97        # Request user presence
    USER_PRESENCE_REQUEST_ALL = 98    # Request all users' presence

    # ===================
    # Settings
    # ===================
    
    TOGGLE_BLOCK_NON_FRIEND_DMS = 99  # Block DMs from non-friends

    def __repr__(self) -> str:
        return f"<{self.name} ({self.value})>"


# ===================
# Packet Data Structures
# ===================

# Map packet IDs to their expected data format
# Format: [(field_name, type_string), ...]
CLIENT_PACKET_FORMATS: dict[ClientPackets, list[tuple[str, str]]] = {
    # CHANGE_ACTION (0): action, info_text, map_md5, mods, mode, map_id
    ClientPackets.CHANGE_ACTION: [
        ("action", "u8"),
        ("info_text", "string"),
        ("map_md5", "string"),
        ("mods", "i32"),
        ("mode", "u8"),
        ("map_id", "i32"),
    ],
    
    # SEND_PUBLIC_MESSAGE (1): message
    ClientPackets.SEND_PUBLIC_MESSAGE: [
        ("message", "message"),
    ],
    
    # SEND_PRIVATE_MESSAGE (25): message
    ClientPackets.SEND_PRIVATE_MESSAGE: [
        ("message", "message"),
    ],
    
    # CREATE_MATCH (31): match
    ClientPackets.CREATE_MATCH: [
        ("match", "match"),
    ],
    
    # JOIN_MATCH (32): match_id, password
    ClientPackets.JOIN_MATCH: [
        ("match_id", "i32"),
        ("password", "string"),
    ],
    
    # CHANNEL_JOIN (63): channel_name
    ClientPackets.CHANNEL_JOIN: [
        ("channel_name", "string"),
    ],
    
    # FRIEND_ADD (73): user_id
    ClientPackets.FRIEND_ADD: [
        ("user_id", "i32"),
    ],
    
    # FRIEND_REMOVE (74): user_id
    ClientPackets.FRIEND_REMOVE: [
        ("user_id", "i32"),
    ],
}
