from jays_tools import JsonDatabase

from adapters import OsuFile
from constants.paths import OSU_FILES
from models.database.osufiles.backup import OsuFileBackup, OsuFileEntry


class OsuFileBackupRepository:
    def __init__(self) -> None:
        self.db = JsonDatabase(path=OSU_FILES, models=OsuFileBackup)

    async def get_backup(self, md5: str) -> OsuFileEntry | None:
        async with self.db as db:
            if md5 in db.all:
                return db.all[md5]

    async def save_backup(self, backup: OsuFile) -> None:
        async with self.db as db:
            db.all[backup.md5] = OsuFileEntry(
                md5=backup.md5,
                file=backup,
            )

            self.db.set(db)
