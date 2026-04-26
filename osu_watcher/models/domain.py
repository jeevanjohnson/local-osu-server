from jays_tools.architecture import DomainModel
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ParsedOsuFile(DomainModel):
    md5: str
    beatmap_id: int | None
    beatmap_set_id: int | None
    filename: str
    path: Path