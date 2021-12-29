import lzma
import struct
from enum import IntFlag
from pathlib import Path
from typing import Optional
from objects.mods import Mods

class Key(IntFlag):
    M1    = 1 << 0
    M2    = 1 << 1
    K1    = 1 << 2
    K2    = 1 << 3
    Smoke = 1 << 4

class LifeBar:
    def __init__(self, delta_time: int, current_hp: float) -> None:
        self.delta_time = delta_time
        self.current_hp = current_hp

    @classmethod
    def from_raw_bar(cls, raw_bar: str) -> 'LifeBar':
        hp = 1.0
        if ',' not in raw_bar:
            return cls(int(raw_bar), hp)

        hp, vtime = raw_bar.split(',')
        return cls(int(vtime or 0), float(hp))

class Frame:
    def __init__(
        self, delta_time: float,
        x: float, y: float,
        key: Key
    ) -> None:
        self.delta_time = delta_time
        self.x = x
        self.y = y
        self.pressed = key

    @classmethod
    def from_raw_frame(cls, raw_frame: bytes) -> 'Frame':
        w, x, y, z, = raw_frame.decode().split('|')
        return cls(
            float(w), float(x),
            float(y), Key(int(z))
        )

class Replay:
    def __init__(self, raw_replay: bytes) -> None:
        """https://osu.ppy.sh/wiki/en/osu%21_File_Formats/Osr_%28file_format%29"""
        self._data = raw_replay
        self.offset = 0

        self.mode: int
        self.version: int
        self.beatmap_md5: str
        self.replay_md5: str
        self.player_name: str
        self.n300: int
        self.n100: int
        self.n50: int
        self.ngeki: int
        self.nkatu: int
        self.nmiss: int
        self.total_score: int
        self.combo: int
        self.perfect: bool
        self.mods: Mods
        self.bar_graph: list[LifeBar]
        self.timestamp: int
        self.score_id: int
        self.additional_mods: Optional[int] = None
        self.frames: list[Frame]
        self.raw_frames: bytes

    @property
    def data(self) -> bytes:
        return self._data[self.offset:]

    @classmethod
    def from_file(cls, path: Path) -> 'Replay':
        replay = cls(path.read_bytes())
        replay.parse()
        return replay

    @classmethod
    def from_content(cls, content: bytes) -> 'Replay':
        replay = cls(content)
        replay.parse()
        return replay

    def parse(self) -> None:
        self.mode = self.read_byte()
        self.version = self.read_int()
        self.beatmap_md5 = self.read_string()
        self.player_name = self.read_string()
        self.replay_md5 = self.read_string()
        self.n300 = self.read_short()
        self.n100 = self.read_short()
        self.n50 = self.read_short()
        self.ngeki = self.read_short()
        self.nkatu = self.read_short()
        self.nmiss = self.read_short()
        self.total_score = self.read_int()
        self.combo = self.read_short()
        self.perfect = bool(self.read_byte())
        self.mods = Mods(self.read_int())
        self.bar_graph = [LifeBar.from_raw_bar(x) for x in self.read_string().split('|')]
        self.timestamp = self.read_long_long()

        self.raw_frames = self.read_raw(self.read_int())
        decoded_frames = lzma.decompress(self.raw_frames).split(b',')
        self.frames = [Frame.from_raw_frame(x) for x in decoded_frames if x]

        self.scoreid = self.read_long_long()

        if self.mods & Mods.TARGET:
            self.additional_mods = self.read_double()

    def read_byte(self) -> int:
        val, = struct.unpack('<b', self.data[:1])
        self.offset += 1
        return val

    def read_short(self) -> int:
        val, = struct.unpack('<h', self.data[:2])
        self.offset += 2
        return val

    def read_int(self) -> int:
        val, = struct.unpack('<i', self.data[:4])
        self.offset += 4
        return val

    def read_long_long(self) -> int:
        val, = struct.unpack('<q', self.data[:8])
        self.offset += 8
        return val

    def read_double(self) -> int:
        val, = struct.unpack('<d', self.data[:8])
        self.offset += 8
        return val

    def read_uleb128(self) -> int:
        val = shift = 0

        while True:
            b = self.data[0]
            self.offset += 1

            val |= ((b & 0b01111111) << shift)
            if (b & 0b10000000) == 0:
                break


            shift += 7

        return val

    def read_string(self) -> str:
        if self.read_byte() == 0x0b:
            return self.read_raw(self.read_uleb128()).decode()

        return ''

    def read_raw(self, length: int) -> bytes:
        val = self.data[:length]
        self.offset += length
        return val