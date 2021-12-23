import lzma
import struct
from enum import unique
from enum import IntEnum
from enum import IntFlag
from typing import Optional

@unique
class GameMode(IntEnum):
    Standard = 0
    Taiko = 1
    CatchTheBeat = 2
    Osumania = 3

@unique
class Mods(IntFlag):
    NOMOD       = 0
    NOFAIL      = 1 << 0
    EASY        = 1 << 1
    TOUCHSCREEN = 1 << 2 # old: 'NOVIDEO'
    HIDDEN      = 1 << 3
    HARDROCK    = 1 << 4
    SUDDENDEATH = 1 << 5
    DOUBLETIME  = 1 << 6
    RELAX       = 1 << 7
    HALFTIME    = 1 << 8
    NIGHTCORE   = 1 << 9
    FLASHLIGHT  = 1 << 10
    AUTOPLAY    = 1 << 11
    SPUNOUT     = 1 << 12
    AUTOPILOT   = 1 << 13
    PERFECT     = 1 << 14
    KEY4        = 1 << 15
    KEY5        = 1 << 16
    KEY6        = 1 << 17
    KEY7        = 1 << 18
    KEY8        = 1 << 19
    FADEIN      = 1 << 20
    RANDOM      = 1 << 21
    CINEMA      = 1 << 22
    TARGET      = 1 << 23
    KEY9        = 1 << 24
    KEYCOOP     = 1 << 25
    KEY1        = 1 << 26
    KEY3        = 1 << 27
    KEY2        = 1 << 28
    SCOREV2     = 1 << 29
    MIRROR      = 1 << 30

    SPEED_CHANGING = DOUBLETIME | NIGHTCORE | HALFTIME

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

        self.mode: Optional[GameMode] = None
        self.version: Optional[int] = None
        self.beatmap_md5: Optional[str] = None
        self.replay_md5: Optional[str] = None
        self.player_name: Optional[str] = None
        self.n300: Optional[int] = None
        self.n100: Optional[int] = None
        self.n50: Optional[int] = None
        self.geki: Optional[int] = None
        self.katu: Optional[int] = None
        self.miss: Optional[int] = None
        self.total_score: Optional[int] = None
        self.combo: Optional[int] = None
        self.perfect: Optional[int] = None
        self.mods: Optional[Mods] = None
        self.bar_graph: Optional[list[LifeBar]] = None
        self.timestamp: Optional[int] = None
        self.score_id: Optional[int] = None
        self.additional_mods: Optional[int] = None
        self.frames: Optional[list[Frame]] = None
        self.raw_frames: Optional[bytes] = None

    @property
    def data(self) -> bytes:
        return self._data[self.offset:]

    @classmethod
    def from_file(cls, path: str) -> 'Replay':
        with open(path, 'rb') as f:
            replay = cls(f.read())
            replay.parse()
            return replay

    @classmethod
    def from_content(cls, content: bytes) -> 'Replay':
        replay = cls(content)
        replay.parse()
        return replay

    def parse(self) -> None:
        self.mode = GameMode(self.read_byte())
        self.version = self.read_int()
        self.beatmap_md5 = self.read_string()
        self.player_name = self.read_string()
        self.replay_md5 = self.read_string()
        self.n300 = self.read_short()
        self.n100 = self.read_short()
        self.n50 = self.read_short()
        self.geki = self.read_short()
        self.katu = self.read_short()
        self.miss = self.read_short()
        self.total_score = self.read_int()
        self.combo = self.read_short()
        self.perfect = self.read_byte()
        self.mods = Mods(self.read_int())
        self.bar_graph = [LifeBar.from_raw_bar(x) for x in self.read_string().split('|')]
        self.timestamp = self.read_long_long()

        self.raw_frames = raw_frames = self.read_raw(self.read_int())
        decoded_frames: list[bytes] = lzma.decompress(raw_frames).split(b',')
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