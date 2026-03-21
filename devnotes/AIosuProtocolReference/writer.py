"""
Purpose/Domain/Concept:
- This module handles writing packets TO the osu! client.
- It provides a BanchoPacketWriter class for building outgoing packets.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from AIosuProtocolReference.types import Message


@dataclass
class BanchoPacketWriter:
    """
    A class for writing bancho packets to send to the osu! client.

    Attributes
    ----------
    data : bytearray
        The accumulated packet data.

    Example Usage:
    --------------
    ```python
    writer = BanchoPacketWriter()
    writer.write_packet(ServerPackets.USER_ID, osuInt32(1))
    writer.write_packet(ServerPackets.PONG)
    response = writer.get_response()
    ```
    """

    data: bytearray = field(default_factory=bytearray)

    def __post_init__(self) -> None:
        if self.data is None:
            self.data = bytearray()

    # ===================
    # Write Methods
    # ===================

    def write_int8(self, value: int) -> "BanchoPacketWriter":
        """Write a signed 8-bit integer."""
        self.data.extend(struct.pack("<b", value))
        return self

    def write_uint8(self, value: int) -> "BanchoPacketWriter":
        """Write an unsigned 8-bit integer."""
        self.data.extend(struct.pack("<B", value))
        return self

    def write_int16(self, value: int) -> "BanchoPacketWriter":
        """Write a signed 16-bit integer."""
        self.data.extend(value.to_bytes(2, "little", signed=True))
        return self

    def write_uint16(self, value: int) -> "BanchoPacketWriter":
        """Write an unsigned 16-bit integer."""
        self.data.extend(value.to_bytes(2, "little", signed=False))
        return self

    def write_int32(self, value: int) -> "BanchoPacketWriter":
        """Write a signed 32-bit integer."""
        self.data.extend(value.to_bytes(4, "little", signed=True))
        return self

    def write_uint32(self, value: int) -> "BanchoPacketWriter":
        """Write an unsigned 32-bit integer."""
        self.data.extend(value.to_bytes(4, "little", signed=False))
        return self

    def write_int64(self, value: int) -> "BanchoPacketWriter":
        """Write a signed 64-bit integer."""
        self.data.extend(value.to_bytes(8, "little", signed=True))
        return self

    def write_uint64(self, value: int) -> "BanchoPacketWriter":
        """Write an unsigned 64-bit integer."""
        self.data.extend(value.to_bytes(8, "little", signed=False))
        return self

    def write_float32(self, value: float) -> "BanchoPacketWriter":
        """Write a 32-bit float."""
        self.data.extend(struct.pack("<f", value))
        return self

    def write_float64(self, value: float) -> "BanchoPacketWriter":
        """Write a 64-bit float (double)."""
        self.data.extend(struct.pack("<d", value))
        return self

    def write_string(self, value: str) -> "BanchoPacketWriter":
        """Write an osu! formatted string."""
        if not value:
            self.data.extend(b"\x00")
        else:
            encoded = value.encode()
            self.data.extend(b"\x0b")
            self.data.extend(self._write_uleb128(len(encoded)))
            self.data.extend(encoded)
        return self

    def write_message(self, message: Message) -> "BanchoPacketWriter":
        """Write an osu! message."""
        self.write_string(message.sender)
        self.write_string(message.text)
        self.write_string(message.recipient)
        self.write_int32(message.sender_id)
        return self

    def write_raw(self, value: bytes) -> "BanchoPacketWriter":
        """Write raw bytes."""
        self.data.extend(value)
        return self

    # ===================
    # Packet Building
    # ===================

    def write_packet(
        self, packet_id: int, *args: tuple[Any, ...]
    ) -> "BanchoPacketWriter":
        """
        Write a complete packet with header.

        Parameters
        ----------
        packet_id : int
            The packet ID (e.g., from ServerPackets enum).
        *args : tuple
            Values to write with their types.
            Format: (value, type_string) or just value (defaults to i32)

        Example
        -------
        writer.write_packet(ServerPackets.USER_ID, (1, "i32"))
        writer.write_packet(ServerPackets.SEND_MESSAGE, message)
        """
        # Start writing packet header placeholder
        header_start = len(self.data)
        self.data.extend(
            struct.pack("<Hx", packet_id)
        )  # 6 bytes: 2 (id) + 4 (length placeholder)

        # Write the data
        for arg in args:
            if isinstance(arg, tuple):
                value, type_str = arg
                self._write_typed_value(value, type_str)
            else:
                # Default to int32
                self.write_int32(arg)

        # Calculate and write actual length
        packet_length = len(self.data) - header_start - 6
        length_bytes = struct.pack("<I", packet_length)
        self.data[header_start + 2 : header_start + 6] = length_bytes

        return self

    def _write_typed_value(self, value: Any, type_str: str) -> None:
        """Write a value based on its type string."""
        if type_str == "i8":
            self.write_int8(value)
        elif type_str == "u8":
            self.write_uint8(value)
        elif type_str == "i16":
            self.write_int16(value)
        elif type_str == "u16":
            self.write_uint16(value)
        elif type_str == "i32":
            self.write_int32(value)
        elif type_str == "u32":
            self.write_uint32(value)
        elif type_str == "i64":
            self.write_int64(value)
        elif type_str == "u64":
            self.write_uint64(value)
        elif type_str == "f32":
            self.write_float32(value)
        elif type_str == "f64":
            self.write_float64(value)
        elif type_str == "string":
            self.write_string(value)
        else:
            raise ValueError(f"Unknown type: {type_str}")

    @staticmethod
    def _write_uleb128(num: int) -> bytes:
        """Write number as ULEB128."""
        if num == 0:
            return b"\x00"

        ret = bytearray()
        while num != 0:
            ret.append(num & 0x7F)
            num >>= 7
            if num != 0:
                ret[-1] |= 0x80

        return bytes(ret)

    def get_bytes(self) -> bytes:
        """Get the accumulated data as bytes."""
        return bytes(self.data)

    def clear(self) -> None:
        """Clear the buffer."""
        self.data.clear()


# ===================
# Convenience Functions
# ===================


def write_packet(packet_id: int, *args: tuple[Any, ...]) -> bytes:
    """
    Write a complete packet and return bytes.

    Example
    -------
    data = write_packet(ServerPackets.USER_ID, (1, "i32"))
    """
    writer = BanchoPacketWriter()
    writer.write_packet(packet_id, *args)
    return writer.get_bytes()
