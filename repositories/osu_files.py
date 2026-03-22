from pathlib import Path

from jays_tools import JsonDatabase

from adapters.app_logger import app_logger
from models.database.osu_files import (
    CurrentOsuFileEntry as OsuFileEntry,
)
from models.database.osu_files import (
    CurrentOsuFiles as OsuFiles,
)


class OsuFilesRepository:
    def __init__(self, path: Path) -> None:
        self.osu_files = JsonDatabase(path=path, models=OsuFiles)

    @app_logger.log(msg="repository get osu file by md5")
    async def get_by_md5(self, md5: str) -> OsuFileEntry | None:
        async with self.osu_files as osu_files:
            return osu_files.all.get(md5)

    @app_logger.log(msg="repository upsert osu file by md5")
    async def upsert(self, entry: OsuFileEntry) -> None:
        async with self.osu_files as osu_files:
            osu_files.all[entry.md5] = entry
            self.osu_files.set(osu_files)

    @app_logger.log(msg="repository delete osu file by md5")
    async def delete_by_md5(self, md5: str) -> None:
        async with self.osu_files as osu_files:
            osu_files.all.pop(md5, None)
            self.osu_files.set(osu_files)
