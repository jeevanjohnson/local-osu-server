import hashlib
import os
import struct
import tempfile
import zlib
from pathlib import Path

from osupyparser import OsuFile as BaseOsuFile
from osupyparser.osu.constants import OSU_FILE_HEADER

from cache import cached_forever

PACKED_MAGIC = b"LOS2"
PACKED_HEADER = struct.Struct("<4sBII")
PACKED_FLAG_AUDIO_COMPRESSED = 0b00000001
PACKED_ZLIB_LEVEL = 6


# TODO: Clean this up?
class OsuFile(BaseOsuFile):
    def __init__(
        self,
        file_path: str | Path,
        raw_audio_file: bytes | None = None,
    ):
        self.raw_audio_file: bytes | None = raw_audio_file
        self.raw_file: bytes | None = None

        if isinstance(file_path, str):
            self.file_name = file_path
            super().__init__(file_path)
        else:
            self.file_name = file_path.name
            super().__init__(str(file_path.absolute()))

    def colours_parser(self, line: str) -> None:
        # Weird bug with https://osu.ppy.sh/beatmapsets/1682024#osu/3436489
        # color line has 4 instead of just 3
        try:
            super().colours_parser(line)
        except ValueError:
            pass
    
    @property
    def unsubmitted(self) -> bool:
        return self.beatmap_id == 0

    @classmethod
    @cached_forever
    def from_path(
        cls,
        file_path: str | Path,
        raw_audio_file: bytes | None = None,
        load_audio_file: bool = True,
    ) -> "OsuFile":
        parsed_file = cls(file_path).parse_file(load_audio_file=load_audio_file)

        if raw_audio_file is not None:
            parsed_file.raw_audio_file = raw_audio_file

        return parsed_file

    @classmethod
    @cached_forever
    def from_raw(
        cls,
        raw_file: bytes,
        raw_audio_file: bytes | None = None,
        load_audio_file: bool = True,
    ) -> "OsuFile":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".osu") as tmp_file:
            tmp_file.write(raw_file)
            tmp_file_path = tmp_file.name

        parsed_file = cls(tmp_file_path).parse_file(load_audio_file=load_audio_file)

        if raw_audio_file is not None:
            parsed_file.raw_audio_file = raw_audio_file

        os.remove(tmp_file_path)

        return parsed_file

    def parse_file(self, load_audio_file: bool = True) -> "OsuFile":
        """Parses sections and set them to class variables."""

        with open(self.__file_path, "rb") as stream:
            buffer = stream.read()
        lines = list(
            map(lambda x: x.strip(), buffer.decode("utf-8-sig").split("\n"))
        )  # Strip lines.
        self.md5 = hashlib.md5(buffer).digest().hex()

        header_line = lines[0]
        if not header_line.startswith(OSU_FILE_HEADER):
            # First line should have osu special header.
            raise ValueError(
                f"Unknown file error! Excepted: {OSU_FILE_HEADER}, got {header_line}"
            )
        self.file_version = int(header_line[len(OSU_FILE_HEADER) :])

        section_name = ""
        for line in lines[1:]:
            if not line:
                continue  # Just continue looping.

            if line[0] == "[" and line[-1] == "]":
                section_name = line[1:-1].lower()
                continue

            # Call parser to take care of it.
            section_parser = getattr(self, f"{section_name}_parser", None)
            if not section_parser:
                continue
            section_parser(line)

        self.calculate_minor_things()
        self.calculate_max_combo()
        if load_audio_file:
            self.get_audio_file()
        self.get_raw_file()
        return self  # Return self as some people would want to make one line parsing.

    def get_raw_file(self) -> bytes:
        if self.raw_file is not None:
            return self.raw_file

        with open(self.__file_path, "rb") as stream:
            self.raw_file = stream.read()

        return self.raw_file

    def get_audio_file(self) -> bytes | None:
        set_path = Path(self.__file_path).parent
        audio_path = set_path / self.audio_filename

        if audio_path.exists():
            self.raw_audio_file = audio_path.read_bytes()
            return self.raw_audio_file

        return None

    def compress(self, include_audio: bool = True) -> bytes:
        """Compress osu payloads into a versioned compact binary format."""
        raw_file = self.get_raw_file() or b""
        raw_audio_file = (self.raw_audio_file or b"") if include_audio else b""

        raw_blob = zlib.compress(raw_file, level=PACKED_ZLIB_LEVEL)

        # Most audio is already compressed (mp3/ogg). Only keep compressed bytes when useful.
        audio_blob = raw_audio_file
        flags = 0
        if raw_audio_file:
            compressed_audio = zlib.compress(raw_audio_file, level=1)
            if len(compressed_audio) < len(raw_audio_file):
                audio_blob = compressed_audio
                flags |= PACKED_FLAG_AUDIO_COMPRESSED

        header = PACKED_HEADER.pack(PACKED_MAGIC, flags, len(raw_blob), len(audio_blob))
        return header + raw_blob + audio_blob

    @classmethod
    def decompress(cls, data: bytes) -> "OsuFile":
        """Decompress persisted data into an OsuFile object."""
        if len(data) < PACKED_HEADER.size or data[:4] != PACKED_MAGIC:
            raise ValueError("Invalid OsuFile packed payload format.")

        magic, flags, raw_blob_len, audio_blob_len = PACKED_HEADER.unpack_from(data)
        if magic != PACKED_MAGIC:
            raise ValueError("Invalid OsuFile packed magic.")

        payload = data[PACKED_HEADER.size :]
        expected_size = raw_blob_len + audio_blob_len
        if len(payload) != expected_size:
            raise ValueError("Invalid OsuFile packed payload size.")

        raw_blob = payload[:raw_blob_len]
        audio_blob = payload[raw_blob_len:]

        try:
            raw_file = zlib.decompress(raw_blob)
            raw_audio_file = (
                zlib.decompress(audio_blob)
                if flags & PACKED_FLAG_AUDIO_COMPRESSED
                else audio_blob
            )
        except zlib.error as exc:
            raise ValueError("Invalid compressed OsuFile payload.") from exc

        return cls.from_raw(raw_file, raw_audio_file)
