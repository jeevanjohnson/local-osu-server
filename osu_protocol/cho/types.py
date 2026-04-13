import struct
from dataclasses import dataclass, field
from typing import Literal

OffSet = int


class osuBaseType:
    def osu_protocol_serialize(self) -> bytes:
        """Serialize this type into bytes for osu! protocol."""
        raise NotImplementedError(
            "osu_protocol_serialize must be implemented by subclasses."
        )

    @classmethod
    def osu_protocol_deserialize(cls, buffer: bytes) -> tuple["osuBaseType", OffSet]:
        """Deserialize bytes from osu! protocol into an instance of this type."""
        raise NotImplementedError(
            "osu_protocol_deserialize must be implemented by subclasses."
        )


class osuByteArray(bytearray):
    def __iadd__(self, other: bytes | bytearray | osuBaseType) -> "osuByteArray":
        if isinstance(other, osuBaseType):
            self.extend(other.osu_protocol_serialize())
        else:
            self.extend(other)

        return self


@dataclass
class osuUnsignedChar(osuBaseType):
    value: int

    def osu_protocol_serialize(self) -> bytes:
        return self.value.to_bytes(1, "little", signed=False)

    @classmethod
    def osu_protocol_deserialize(cls, buffer: bytes) -> tuple["osuUnsignedChar", int]:
        value = int.from_bytes(buffer[:1], "little", signed=False)
        return cls(value=value), 1


@dataclass
class osuIntUnSigned32List(osuBaseType):
    value: list[int]

    @classmethod
    def osu_protocol_deserialize(
        cls, buffer: bytes
    ) -> tuple["osuIntUnSigned32List", OffSet]:
        length = int.from_bytes(buffer[:2], "little")
        buffer = buffer[2:]

        values = struct.unpack(f"<{'I' * length}", buffer[: length * 4])

        return cls(value=list(values)), 2 + length * 4


@dataclass
class osuUTCOffset(osuUnsignedChar):
    offset_hours: int
    value: int = field(init=False)

    def __post_init__(self):
        # if self.offset_hours < -12 or self.offset_hours > 14:
        #     raise ValueError("UTC offset must be between -12 and +14 hours.")

        self.value = self.offset_hours + 24


@dataclass
class osuShort(osuBaseType):
    value: int

    def osu_protocol_serialize(self) -> bytes:
        return self.value.to_bytes(2, "little", signed=False)


@dataclass
class osuInteger(osuBaseType):
    value: int
    signed: bool
    bit_width: Literal[32, 64]

    def osu_protocol_serialize(self) -> bytes:
        if self.bit_width == 32:
            length_of_int = 4
        else:  # self.bit_width == 64
            length_of_int = 8

        try:
            return self.value.to_bytes(length_of_int, "little", signed=self.signed)
        except OverflowError as e:
            raise ValueError(
                f"Value {self.value} cannot be represented in {length_of_int * 8} bits"
            ) from e


@dataclass
class osuIntSigned32Bit(osuInteger):
    value: int
    signed: bool = True
    bit_width: Literal[32, 64] = 32

    @classmethod
    def osu_protocol_deserialize(
        cls, buffer: bytes
    ) -> tuple["osuIntSigned32Bit", OffSet]:
        value = int.from_bytes(buffer[:4], "little", signed=True)
        return cls(value=value), 4


@dataclass
class osuIntUnsigned32Bit(osuInteger):
    value: int
    signed: bool = False
    bit_width: Literal[32, 64] = 32

    @classmethod
    def osu_protocol_deserialize(
        cls, buffer: bytes
    ) -> tuple["osuIntUnsigned32Bit", OffSet]:
        value = int.from_bytes(buffer[:4], "little", signed=False)
        return cls(value=value), 4


@dataclass
class osuIntUnsigned64Bit(osuInteger):
    value: int
    signed: bool = False
    bit_width: Literal[32, 64] = 64

    @classmethod
    def osu_protocol_deserialize(
        cls, buffer: bytes
    ) -> tuple["osuIntUnsigned64Bit", OffSet]:
        value = int.from_bytes(buffer[:8], "little", signed=False)
        return cls(value=value), 8


@dataclass
class osuFloat32Bit(osuBaseType):
    value: float

    def osu_protocol_serialize(self) -> bytes:
        return struct.pack("<f", self.value)


@dataclass
class osuAccuracy(osuFloat32Bit):
    acc: float
    value: float = field(init=False)

    def __post_init__(self):
        if self.acc > 1:
            self.value = self.acc / 100.0
        else:
            self.value = self.acc


@dataclass
class osuFloat64Bit(osuBaseType):
    value: float

    def osu_protocol_serialize(self) -> bytes:
        return struct.pack("<d", self.value)


@dataclass
class osuString(osuBaseType):
    value: str

    def osu_protocol_length(self) -> bytes:
        string_length = len(self.value.encode())

        if string_length == 0:
            return b"\x00"

        # ULEB128 encoding for string length
        length_bytes = osuByteArray()

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
    def osu_protocol_deserialize(cls, buffer: bytes) -> tuple["osuString", OffSet]:
        # 0x00 means empty string; 0x0b means string is present and length-prefixed.
        if buffer[0] == 0x00:
            return cls(value=""), 1

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

        string_bytes = buffer[current_offset : current_offset + length]
        string_value = string_bytes.decode("utf-8")

        return cls(value=string_value), current_offset + length

    def osu_protocol_serialize(self) -> bytes:
        if self.value == "":
            return b"\x00"

        length_of_string = self.osu_protocol_length()

        return b"\x0b" + length_of_string + self.value.encode()


@dataclass
class osuMainMenuIcon(osuString):
    icon_url: str
    on_click_url: str
    value: str = field(init=False)

    def __post_init__(self):
        self.value = f"{self.icon_url}|{self.on_click_url}"


@dataclass
class osuInt32List(osuBaseType):
    values: list[int]

    def osu_protocol_serialize(self) -> bytes:
        result = osuByteArray()

        result += osuShort(len(self.values))

        for val in self.values:
            result += osuIntSigned32Bit(val)

        return bytes(result)


osuFriendList = osuInt32List
