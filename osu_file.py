from osupyparser import OsuFile as BaseOsuFile
from osupyparser.osu.constants import OSU_FILE_HEADER
import hashlib
from pathlib import Path

class OsuFile(BaseOsuFile):
    def __init__(self, file_path: str):
        self.raw_audio_file: bytes | None = None
        super().__init__(file_path)
    
    def parse_file(self) -> 'OsuFile':
        """Parses sections and set them to class variables."""

        with open(self.__file_path, "rb") as stream:
            buffer = stream.read()
        lines = list(map(lambda x: x.strip(), buffer.decode("utf-8-sig").split("\n"))) # Strip lines.
        self.md5 = hashlib.md5(buffer).digest().hex()

        header_line = lines[0]
        print(f"Parsing osu file with header: {header_line}")
        if not header_line.startswith(OSU_FILE_HEADER):
            # First line should have osu special header.
            raise ValueError(f"Unknown file error! Excepted: {OSU_FILE_HEADER}, got {header_line}")
        self.file_version = int(header_line[len(OSU_FILE_HEADER):])

        section_name = ""
        for line in lines[1:]:
            if not line: continue # Just continue looping.

            if line[0] == "[" and line[-1] == "]":
                section_name = line[1:-1].lower()
                continue
            
            # Call parser to take care of it.
            section_parser = getattr(self, f"{section_name}_parser", None)
            if not section_parser: continue
            section_parser(line)

        self.calculate_minor_things()
        self.calculate_max_combo()
        self.get_audio_file()
        return self # Return self as some people would want to make one line parsing.

    def get_audio_file(self) -> bytes | None:
        set_path = Path(self.__file_path).parent
        audio_path = set_path / self.audio_filename

        if audio_path.exists():
            self.raw_audio_file = audio_path.read_bytes()
            return self.raw_audio_file
        
        return None