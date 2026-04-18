import hashlib
from pathlib import Path
from typing import TypedDict


class ParseOsuFileResponse(TypedDict):
    md5: str
    beatmap_id: int | None
    beatmap_set_id: int | None
    filename: str
    path: Path

def parse_osu_file(osu_file: Path) -> ParseOsuFileResponse:
    file_content = osu_file.read_bytes()
    md5 = hashlib.md5(file_content).hexdigest()

    folder_set_name = osu_file.parent.name

    try:
        beatmap_set_id, _ = folder_set_name.split(" ", maxsplit=1)
        beatmap_set_id = int(beatmap_set_id)
    except ValueError:
        beatmap_set_id = None

    beatmap_id: int | None = None
    for line in file_content.decode("utf-8-sig").splitlines()[:50]:
        line = line.strip()

        if line.startswith("BeatmapID"):
            beatmap_id = int(line.split(":")[1].strip())
            break
    
    return {
        "md5": md5,
        "beatmap_id": beatmap_id,
        "beatmap_set_id": beatmap_set_id,
        "filename": osu_file.name,
        "path": osu_file.resolve(),
    }