import hashlib
import os
import tempfile
from pathlib import Path

from osupyparser import OsuFile as BaseOsuFile
from osupyparser.osu.constants import OSU_FILE_HEADER

BOUNDARY = b"-----LOS2026-----"


class OsuFile(BaseOsuFile):
    def __init__(
        self,
        file_path: str,
        raw_audio_file: bytes | None = None,
    ):
        self.raw_audio_file: bytes | None = raw_audio_file
        self.raw_file: bytes | None = None
        super().__init__(file_path)

    @classmethod
    def from_path(
        cls,
        file_path: str,
        raw_audio_file: bytes | None = None,
        load_audio_file: bool = True,
    ) -> "OsuFile":
        parsed_file = cls(file_path).parse_file(load_audio_file=load_audio_file)

        if raw_audio_file is not None:
            parsed_file.raw_audio_file = raw_audio_file

        return parsed_file

    @classmethod
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

    def compress(self) -> bytes:
        """Compresses the osu file & audio file into bytes for storage."""

        result = [
            self.get_raw_file() or b"",
            BOUNDARY,
            self.raw_audio_file or b"",
        ]

        return b"\n".join(result)

    @classmethod
    def decompress(cls, data: bytes) -> "OsuFile":
        """Decompresses the data into an OsuFile object."""
        try:
            raw_file, raw_audio_file = data.split(BOUNDARY)
        except ValueError:
            raise ValueError("Invalid data format for OsuFile decompression.")

        return cls.from_raw(raw_file, raw_audio_file)
