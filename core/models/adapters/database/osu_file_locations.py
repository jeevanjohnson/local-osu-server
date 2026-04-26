from jays_tools.architecture import AdapterModel
from jays_tools.sql_database import MigratableSQLModel
from pydantic import Field
from pathlib import Path

class OsuFileLocationsV1(MigratableSQLModel, AdapterModel, table=True):
    songs_folder_directory: Path = Field(default_factory=Path)

    md5_to_path: dict[str, Path] = Field(default_factory=dict)
    id_to_paths: dict[int, list[Path]] = Field(default_factory=dict)
    set_id_to_paths: dict[int, list[Path]] = Field(default_factory=dict)
    filename_to_path: dict[str, Path] = Field(default_factory=dict)

    path_to_md5: dict[Path, str] = Field(default_factory=dict)
    path_to_id: dict[Path, int] = Field(default_factory=dict)
    path_to_set_id: dict[Path, int] = Field(default_factory=dict)
    path_to_filename: dict[Path, str] = Field(default_factory=dict)

OsuFileLocations = OsuFileLocationsV1