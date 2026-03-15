"""
Purpose/Domain/Concept:
- This is the main module for osu! protocol handling.
- It provides a clean API for reading and writing osu! packets.

Module Structure:
- types.py: Primitive type wrappers (osuInt8, osuInt32, osuString, etc.)
- reader.py: BanchoPacketReader for reading packets from the client
- writer.py: BanchoPacketWriter for writing packets to the client
- client_packets.py: ClientPackets enum for packet IDs from client
- server_packets.py: ServerPackets enum and builder functions for packets to client
"""

# Type classes
from AIosuProtocolReference.types import (
    Channel,
    Message,
    OsuType,
    ScoreFrame,
    osuFloat32,
    osuFloat64,
    osuInt8,
    osuInt16,
    osuInt32,
    osuInt64,
    osuString,
    osuUInt8,
    osuUInt16,
    osuUInt32,
    osuUInt64,
    OSU_TYPES,
)

# Reader
from AIosuProtocolReference.reader import BanchoPacketReader

# Writer
from AIosuProtocolReference.writer import BanchoPacketWriter, write_packet

# Client packets
from AIosuProtocolReference.client_packets import ClientPackets, CLIENT_PACKET_FORMATS

# Server packets
from AIosuProtocolReference.server_packets import (
    LoginFailureReason,
    ServerPackets,
    build_channel_info,
    build_channel_info_end,
    build_channel_join_success,
    build_friends_list,
    build_notification,
    build_pong,
    build_protocol_version,
    build_restart,
    build_send_message,
    build_user_id,
    build_user_logout,
    build_user_stats,
)

__all__ = [
    # Types
    "Channel",
    "Message",
    "OsuType",
    "ScoreFrame",
    "osuFloat32",
    "osuFloat64",
    "osuInt8",
    "osuInt16",
    "osuInt32",
    "osuInt64",
    "osuString",
    "osuUInt8",
    "osuUInt16",
    "osuUInt32",
    "osuUInt64",
    "OSU_TYPES",
    # Reader
    "BanchoPacketReader",
    # Writer
    "BanchoPacketWriter",
    "write_packet",
    # Client packets
    "ClientPackets",
    "CLIENT_PACKET_FORMATS",
    # Server packets
    "LoginFailureReason",
    "ServerPackets",
    "build_channel_info",
    "build_channel_info_end",
    "build_channel_join_success",
    "build_friends_list",
    "build_notification",
    "build_pong",
    "build_protocol_version",
    "build_restart",
    "build_send_message",
    "build_user_id",
    "build_user_logout",
    "build_user_stats",
]
