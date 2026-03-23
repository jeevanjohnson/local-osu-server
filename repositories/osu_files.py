from pathlib import Path

from jays_tools import JsonDatabase

from adapters import log_time
from adapters.osu_file import OsuFile
from models.database.osu_files import (
    CurrentOsuFileEntry as OsuFileEntry,
)
from models.database.osu_files import (
    CurrentOsuFiles as OsuFiles,
)


class OsuFilesRepository:
    def __init__(self, path: Path) -> None:
        self.osu_files = JsonDatabase(path=path, models=OsuFiles)

    @log_time
    async def get_by_md5(self, md5: str) -> OsuFileEntry | None:
        async with self.osu_files as osu_files:
            return osu_files.all.get(md5)

    @log_time
    async def upsert(self, beatmap_md5: str, file: OsuFile) -> None:
        async with self.osu_files as osu_files:
            osu_files.all[beatmap_md5] = OsuFileEntry(
                md5=beatmap_md5,
                file=file,
            )
            self.osu_files.set(osu_files)

    @log_time
    async def delete_by_md5(self, md5: str) -> None:
        async with self.osu_files as osu_files:
            osu_files.all.pop(md5, None)
            self.osu_files.set(osu_files)
