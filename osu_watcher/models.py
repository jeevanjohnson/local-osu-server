from pathlib import Path

from jays_tools import MigratableModel
from pydantic import Field


class OsuFileLocationV1(MigratableModel):
    by_md5: dict[str, Path] = Field(default_factory=dict)
    by_id: dict[int, Path] = Field(default_factory=dict)
    by_set_id: dict[int, list[Path]] = Field(default_factory=dict)
    by_filename: dict[str, Path] = Field(default_factory=dict)

    path_to_md5: dict[Path, str] = Field(default_factory=dict)
    path_to_id: dict[Path, int] = Field(default_factory=dict)
    path_to_set_id: dict[Path, int] = Field(default_factory=dict)
    path_to_filename: dict[Path, str] = Field(default_factory=dict)

OsuFileLocation = OsuFileLocationV1