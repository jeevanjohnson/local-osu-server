"""
Purpose/Domain/Concept:
- This module contains osu! primitive type wrapper classes.
- Each class encapsulates reading and writing binary data for that specific type.
- This makes packet construction and parsing more readable and maintainable.
"""

from __future__ import annotations

import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import NamedTuple

# ===================
# Abstract Base Type
# ===================


class OsuType(ABC):
    """Abstract base class for all osu! types."""

    @staticmethod
    @abstractmethod
    def read(buffer: memoryview) -> OsuType:
        """Read the type from a buffer."""
        pass

    @abstractmethod
    def write(self) -> bytes:
        """Write the type to bytes."""
        pass


# ===================
# Integer Types
# ===================


@dataclass
class osuInt8(OsuType):
    """Signed 8-bit integer (-128 to 127)."""

    value: int = 0

    @staticmethod
    def read(buffer: memoryview) -> osuInt8:
        val = buffer[0]
        return osuInt8(val - 256 if val > 127 else val)

    def write(self) -> bytes:
        return struct.pack("<b", self.value)


@dataclass
class osuUInt8(OsuType):
    """Unsigned 8-bit integer (0 to 255)."""

    value: int = 0

    @staticmethod
    def read(buffer: memoryview) -> osuUInt8:
        return osuUInt8(buffer[0])

    def write(self) -> bytes:
        return struct.pack("<B", self.value)


@dataclass
class osuInt16(OsuType):
    """Signed 16-bit integer."""

    value: int = 0

    @staticmethod
    def read(buffer: memoryview) -> osuInt16:
        val = int.from_bytes(buffer[:2], "little", signed=True)
        return osuInt16(val)

    def write(self) -> bytes:
        return self.value.to_bytes(2, "little", signed=True)


@dataclass
class osuUInt16(OsuType):
    """Unsigned 16-bit integer."""

    value: int = 0

    @staticmethod
    def read(buffer: memoryview) -> osuUInt16:
        val = int.from_bytes(buffer[:2], "little", signed=False)
        return osuUInt16(val)

    def write(self) -> bytes:
        return self.value.to_bytes(2, "little", signed=False)


@dataclass
class osuInt32(OsuType):
    """Signed 32-bit integer."""

    value: int = 0

    @staticmethod
    def read(buffer: memoryview) -> osuInt32:
        val = int.from_bytes(buffer[:4], "little", signed=True)
        return osuInt32(val)

    def write(self) -> bytes:
        return self.value.to_bytes(4, "little", signed=True)


@dataclass
class osuUInt32(OsuType):
    """Unsigned 32-bit integer."""

    value: int = 0

    @staticmethod
    def read(buffer: memoryview) -> osuUInt32:
        val = int.from_bytes(buffer[:4], "little", signed=False)
        return osuUInt32(val)

    def write(self) -> bytes:
        return self.value.to_bytes(4, "little", signed=False)


@dataclass
class osuInt64(OsuType):
    """Signed 64-bit integer."""

    value: int = 0

    @staticmethod
    def read(buffer: memoryview) -> osuInt64:
        val = int.from_bytes(buffer[:8], "little", signed=True)
        return osuInt64(val)

    def write(self) -> bytes:
        return self.value.to_bytes(8, "little", signed=True)


@dataclass
class osuUInt64(OsuType):
    """Unsigned 64-bit integer."""

    value: int = 0

    @staticmethod
    def read(buffer: memoryview) -> osuUInt64:
        val = int.from_bytes(buffer[:8], "little", signed=False)
        return osuUInt64(val)

    def write(self) -> bytes:
        return self.value.to_bytes(8, "little", signed=False)


# ===================
# Float Types
# ===================


@dataclass
class osuFloat32(OsuType):
    """32-bit floating point number."""

    value: float = 0.0

    @staticmethod
    def read(buffer: memoryview) -> osuFloat32:
        (val,) = struct.unpack_from("<f", buffer[:4])
        return osuFloat32(val)

    def write(self) -> bytes:
        return struct.pack("<f", self.value)


@dataclass
class osuFloat64(OsuType):
    """64-bit floating point number (double)."""

    value: float = 0.0

    @staticmethod
    def read(buffer: memoryview) -> osuFloat64:
        (val,) = struct.unpack_from("<d", buffer[:8])
        return osuFloat64(val)

    def write(self) -> bytes:
        return struct.pack("<d", self.value)


# ===================
# String Type
# ===================


@dataclass
class osuString(OsuType):
    """
    osu! string format:
    - 0x0B (1 byte) + ULEB128 length + UTF-8 bytes if non-empty
    - 0x00 if empty string
    """

    value: str = ""

    @staticmethod
    def read(buffer: memoryview) -> tuple[osuString, int]:
        """
        Read a string from buffer.
        Returns (osuString, bytes_consumed).
        """
        if buffer[0] == 0x00:
            return (osuString(""), 1)

        # Skip the 0x0B prefix
        buffer = buffer[1:]

        # Decode ULEB128 length
        length = shift = 0
        while True:
            byte = buffer[0]
            buffer = buffer[1:]

            length |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 1

        # Read the actual string
        val = buffer[:length].tobytes().decode()
        total_consumed = 1 + (shift + 1) + length

        return (osuString(val), total_consumed)

    def write(self) -> bytes:
        if not self.value:
            return b"\x00"

        encoded = self.value.encode()
        return b"\x0b" + self._write_uleb128(len(encoded)) + encoded

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


# ===================
# Higher-Level Types
# ===================


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
class ScoreFrame:
    """osu! score frame for replay data."""

    time: int
    id: int
    num300: int
    num100: int
    num50: int
    num_geki: int
    num_katu: int
    num_miss: int
    total_score: int
    max_combo: int
    current_combo: int
    perfect: bool
    current_hp: int
    tag_byte: int
    score_v2: bool
    combo_portion: float | None = None
    bonus_portion: float | None = None


# ===================
# Type Registry
# ===================


# Map type names to their classes for dynamic lookup
OSU_TYPES: dict[str, type[OsuType]] = {
    "i8": osuInt8,
    "u8": osuUInt8,
    "i16": osuInt16,
    "u16": osuUInt16,
    "i32": osuInt32,
    "u32": osuUInt32,
    "i64": osuInt64,
    "u64": osuUInt64,
    "f32": osuFloat32,
    "f64": osuFloat64,
    "string": osuString,
}
