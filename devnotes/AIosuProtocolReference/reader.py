"""
Purpose/Domain/Concept:
- This module handles reading packets FROM the osu! client.
- It provides a BanchoPacketReader class that can iterate over incoming packets.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import NamedTuple


# Packet header format: u16 (packet id) + u32 (packet length)
PACKET_HEADER_FORMAT = struct.Struct("<HxI")
PACKET_HEADER_SIZE = 7  # 2 + 4 bytes


class Message(NamedTuple):
    """osu! chat message structure."""
    sender: str
    text: str
    recipient: str
    sender_id: int


class Channel(NamedTuple):
    """osu! channel structure."""
    name: str
    topic: str
    players: int


@dataclass
class BanchoPacketReader:
    """
    A class for reading bancho packets from the osu! client's request body.

    Attributes
    ----------
    buffer : memoryview
        A readonly view of the request's body.

    packet_id : ClientPackets
        The packet ID of the current packet being read.

    packet_length : int
        The length of the current packet's data.

    Example Usage:
    --------------
    ```python
    with memoryview(await request.body()) as buffer:
        for packet in BanchoPacketReader(buffer):
            await packet.handle()
    ```
    """

    buffer: memoryview
    packet_id: int = 0
    packet_length: int = 0

    def __post_init__(self) -> None:
        self._current_offset = 0

    def __iter__(self) -> "BanchoPacketReader":
        return self

    def __next__(self) -> "BanchoPacketReader":
        if not self._has_more_data():
            raise StopIteration

        # Read packet header
        self.packet_id, self.packet_length = self._read_header()

        return self

    def _has_more_data(self) -> bool:
        """Check if there's more data to read."""
        return self._current_offset < len(self.buffer)

    def _read_header(self) -> tuple[int, int]:
        """Read the header of an osu! packet (id & length)."""
        if self._current_offset + PACKET_HEADER_SIZE > len(self.buffer):
            raise StopIteration

        data = struct.unpack_from(
            "<HxI", 
            self.buffer, 
            self._current_offset
        )
        self._current_offset += PACKET_HEADER_SIZE
        return data[0], data[1]

    # ===================
    # Read Methods
    # ===================

    def read_int8(self) -> int:
        """Read a signed 8-bit integer."""
        val = self.buffer[self._current_offset]
        self._current_offset += 1
        return val - 256 if val > 127 else val

    def read_uint8(self) -> int:
        """Read an unsigned 8-bit integer."""
        val = self.buffer[self._current_offset]
        self._current_offset += 1
        return val

    def read_int16(self) -> int:
        """Read a signed 16-bit integer."""
        val = int.from_bytes(
            self.buffer[self._current_offset:self._current_offset + 2],
            "little",
            signed=True
        )
        self._current_offset += 2
        return val

    def read_uint16(self) -> int:
        """Read an unsigned 16-bit integer."""
        val = int.from_bytes(
            self.buffer[self._current_offset:self._current_offset + 2],
            "little",
            signed=False
        )
        self._current_offset += 2
        return val

    def read_int32(self) -> int:
        """Read a signed 32-bit integer."""
        val = int.from_bytes(
            self.buffer[self._current_offset:self._current_offset + 4],
            "little",
            signed=True
        )
        self._current_offset += 4
        return val

    def read_uint32(self) -> int:
        """Read an unsigned 32-bit integer."""
        val = int.from_bytes(
            self.buffer[self._current_offset:self._current_offset + 4],
            "little",
            signed=False
        )
        self._current_offset += 4
        return val

    def read_int64(self) -> int:
        """Read a signed 64-bit integer."""
        val = int.from_bytes(
            self.buffer[self._current_offset:self._current_offset + 8],
            "little",
            signed=True
        )
        self._current_offset += 8
        return val

    def read_uint64(self) -> int:
        """Read an unsigned 64-bit integer."""
        val = int.from_bytes(
            self.buffer[self._current_offset:self._current_offset + 8],
            "little",
            signed=False
        )
        self._current_offset += 8
        return val

    def read_float32(self) -> float:
        """Read a 32-bit float."""
        (val,) = struct.unpack_from(
            "<f",
            self.buffer,
            self._current_offset
        )
        self._current_offset += 4
        return val

    def read_float64(self) -> float:
        """Read a 64-bit float (double)."""
        (val,) = struct.unpack_from(
            "<d",
            self.buffer,
            self._current_offset
        )
        self._current_offset += 8
        return val

    def read_string(self) -> str:
        """Read an osu! formatted string."""
        if self.buffer[self._current_offset] == 0x00:
            self._current_offset += 1
            return ""

        # Skip the 0x0B prefix
        self._current_offset += 1

        # Decode ULEB128 length
        length = shift = 0
        while True:
            byte = self.buffer[self._current_offset]
            self._current_offset += 1

            length |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 1

        # Read the string
        val = self.buffer[
            self._current_offset:self._current_offset + length
        ].tobytes().decode()
        self._current_offset += length
        return val

    def read_message(self) -> Message:
        """Read an osu! message."""
        return Message(
            sender=self.read_string(),
            text=self.read_string(),
            recipient=self.read_string(),
            sender_id=self.read_int32(),
        )

    def read_channel(self) -> Channel:
        """Read an osu! channel."""
        return Channel(
            name=self.read_string(),
            topic=self.read_string(),
            players=self.read_int32(),
        )

    def read_raw(self, length: int) -> bytes:
        """Read raw bytes."""
        val = self.buffer[self._current_offset:self._current_offset + length].tobytes()
        self._current_offset += length
        return val

    def skip(self, length: int) -> None:
        """Skip bytes in the buffer."""
        self._current_offset += length
