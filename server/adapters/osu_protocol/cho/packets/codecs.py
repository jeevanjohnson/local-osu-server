from server.adapters.osu_protocol.cho.packets.enums import ClientStatus
from server.adapters.osu_protocol.enums import ClientGameMode, ClientMods
import struct
from typing import TypeVar
from abc import ABC, abstractmethod
from collections import namedtuple
from enum import IntEnum

T = TypeVar("T")

type Offset = int


class ByteSize(IntEnum):
    FLOAT32 = 4
    FLOAT64 = 8
    U64_INT = 8
    U32_INT = 4
    S32_INT = 4
    U16_INT = 2
    U8_INT = 1

# sign + bit size
# 8 bits per byte


class osuCodec[T](ABC):

    @classmethod
    @abstractmethod
    def deserialize(cls, buffer: bytes) -> tuple[T, Offset]:
        """Deserialize bytes from osu! protocol into an instance of this type."""
        pass

    @staticmethod
    @abstractmethod
    def serialize(value: T) -> bytes:
        """Serialize this type into bytes for osu! protocol."""
        pass


class osuU8(osuCodec[int]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[int, Offset]:
        return buffer[0], ByteSize.U8_INT

    @staticmethod
    def serialize(value: int) -> bytes:
        return value.to_bytes(ByteSize.U8_INT, "little", signed=False)


class osuU32List(osuCodec[list[int]]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[list[int], Offset]:
        length = int.from_bytes(buffer[:ByteSize.U16_INT], "little")
        values = struct.unpack_from(
            f"<{length}I",
            buffer,
            offset=ByteSize.U16_INT
        )
        return list(values), ByteSize.U16_INT + length * ByteSize.U32_INT

    @staticmethod
    def serialize(value: list[int]) -> bytes:
        result = bytearray()
        result += len(value).to_bytes(ByteSize.U16_INT,
                                      "little", signed=False)

        for val in value:
            result += val.to_bytes(ByteSize.U32_INT, "little", signed=False)

        return bytes(result)


class osuU16(osuCodec[int]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[int, Offset]:
        return int.from_bytes(
            buffer[:ByteSize.U16_INT],
            "little",
            signed=False
        ), ByteSize.U16_INT

    @staticmethod
    def serialize(value: int) -> bytes:
        return value.to_bytes(ByteSize.U16_INT, "little", signed=False)


class osuS32(osuCodec[int]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[int, Offset]:
        return int.from_bytes(
            buffer[:ByteSize.S32_INT],
            "little",
            signed=True
        ), ByteSize.S32_INT

    @staticmethod
    def serialize(value: int) -> bytes:
        return value.to_bytes(ByteSize.S32_INT, "little", signed=True)


class osuU32(osuCodec[int]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[int, Offset]:
        return int.from_bytes(
            buffer[:ByteSize.U32_INT],
            "little",
            signed=False
        ), ByteSize.U32_INT

    @staticmethod
    def serialize(value: int) -> bytes:
        return value.to_bytes(ByteSize.U32_INT, "little", signed=False)


class osuU64(osuCodec[int]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[int, Offset]:
        return int.from_bytes(
            buffer[:ByteSize.U64_INT],
            "little",
            signed=False
        ), ByteSize.U64_INT

    @staticmethod
    def serialize(value: int) -> bytes:
        return value.to_bytes(ByteSize.U64_INT, "little", signed=False)


class osuFloat32(osuCodec[float]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[float, Offset]:
        return struct.unpack_from("<f", buffer)[0], ByteSize.FLOAT32

    @staticmethod
    def serialize(value: float) -> bytes:
        return struct.pack("<f", value)


class osuFloat64(osuCodec[float]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[float, Offset]:
        return struct.unpack_from("<d", buffer)[0], ByteSize.FLOAT64

    @staticmethod
    def serialize(value: float) -> bytes:
        return struct.pack("<d", value)


class osuS32List(osuCodec[list[int]]):

    @staticmethod
    def serialize(value: list[int]) -> bytes:
        result = bytearray()

        result += osuU16.serialize(len(value))

        for val in value:
            result += osuS32.serialize(val)

        return bytes(result)

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[list[int], Offset]:
        length, offset = osuU16.deserialize(buffer)
        values = struct.unpack_from(f"<{length}i", buffer, offset=offset)
        return list(values), offset + length * ByteSize.S32_INT


class osuString(osuCodec[str]):

    @staticmethod
    def serialize_string_length(value: str) -> bytes:
        string_length = len(value.encode())

        if string_length == 0:
            return b"\x00"

        # ULEB128 encoding for string length
        length_bytes = bytearray()

        while string_length > 0:
            # 127 is 0x7F in hex, which is equivalent to 0111 1111 in binary.
            # 7 least signifcant bits = 0111 1111
            length_bytes.append(string_length & 0b0111_1111)

            # shift string_length right by 7 bits to process the next 7 bits in the next iteration
            string_length = string_length >> 7

            if string_length != 0:
                # This means there are more bytes to encode, so we set the
                # most significant bit (the top bit) to 1
                length_bytes[-1] |= 0b1000_0000

        return bytes(length_bytes)

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[str, Offset]:
        # 0x00 means empty string; 0x0b means string is present and length-prefixed.
        if buffer[0] == 0x00:
            return "", 1

        if buffer[0] != 0x0B:
            raise ValueError(f"Invalid osuString marker byte: {buffer[0]:#x}")

        # Skip the 0x0B prefix
        current_offset = 1

        # Decode ULEB128 length
        length = shift = 0
        while True:
            byte = buffer[current_offset]
            current_offset += 1

            length |= (byte & 0x7F) << shift

            if (byte & 0x80) == 0:
                break

            shift += 7

        string_bytes = buffer[current_offset: current_offset + length]
        string_value = string_bytes.decode("utf-8")

        return string_value, current_offset + length

    @staticmethod
    def serialize(value: str) -> bytes:
        if value == "":
            return b"\x00"

        length_of_string = osuString.serialize_string_length(value)

        return b"\x0b" + length_of_string + value.encode()


# Special osu! protocol types with custom serialization logic
osuFriendList = osuS32List

MainMenuIcon = namedtuple("MainMenuIcon", ["icon_url", "on_click_url"])


class osuMainMenuIcon(osuCodec[MainMenuIcon]):
    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[MainMenuIcon, Offset]:
        combined_string, offset = osuString.deserialize(buffer)
        icon_url, on_click_url = combined_string.split("|", 1)
        return MainMenuIcon(icon_url=icon_url, on_click_url=on_click_url), offset

    @staticmethod
    def serialize(icon_url: str, on_click_url: str) -> bytes:
        combined_string = f"{icon_url}|{on_click_url}"
        return osuString.serialize(combined_string)


class osuUTCOffset(osuCodec[int]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[int, Offset]:
        value, offset = osuU8.deserialize(buffer)
        return value + 24, offset

    @staticmethod
    def serialize(value: int) -> bytes:
        if not (0 <= value <= 48):
            raise ValueError("UTC offset must be between 0 and 48 inclusive")

        return osuU8.serialize(value - 24)


class osuAccuracy(osuCodec[float]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[float, Offset]:
        accuracy, offset = osuFloat32.deserialize(buffer)
        if accuracy > 1:
            accuracy /= 100.0

        return accuracy, offset

    @staticmethod
    def serialize(value: float) -> bytes:
        if value > 1:
            value /= 100.0

        return osuFloat32.serialize(value)


class osuStatus(osuCodec[ClientStatus]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[ClientStatus, Offset]:
        status_value, offset = osuU8.deserialize(buffer)
        return ClientStatus(status_value), offset

    @staticmethod
    def serialize(value: ClientStatus) -> bytes:
        return osuU8.serialize(value.value)


class osuGameMode(osuCodec[ClientGameMode]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[ClientGameMode, Offset]:
        mode_value, offset = osuU8.deserialize(buffer)
        return ClientGameMode(mode_value), offset

    @staticmethod
    def serialize(value: ClientGameMode) -> bytes:
        return osuU8.serialize(value.value)


class osuMods(osuCodec[ClientMods]):

    @classmethod
    def deserialize(cls, buffer: bytes) -> tuple[ClientMods, Offset]:
        mods_value, offset = osuU32.deserialize(buffer)
        return ClientMods(mods_value), offset

    @staticmethod
    def serialize(value: ClientMods) -> bytes:
        return osuU32.serialize(value.value)
