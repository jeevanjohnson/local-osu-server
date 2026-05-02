from pathlib import Path
from typing import Coroutine
from asyncio import Task
import asyncio
from hachiko.hachiko import AIOEventHandler
from osu_watcher.usecases import OsuDomainUsecases


class SongFolderHandler(AIOEventHandler):
    def __init__(self) -> None:
        super().__init__()

        self.osu_domain_usecases = OsuDomainUsecases()
        self.pending_refresh_task: Task | None = None

    def get_songs_folder(self, osu_file: Path) -> Path:
        return osu_file.parent.parent

    def osu_event(self, event, event_path_str: str) -> Path | None:
        if event.is_directory:
            return None

        if not event_path_str.endswith(".osu"):
            return None

        event_src_path = Path(event_path_str)

        if not event_src_path.is_file():
            return None

        if not event_src_path.suffix == ".osu":
            return None

        return event_src_path

    async def on_osu_event(self, event, event_path_str: str) -> None:
        event_src_path = self.osu_event(event, event_path_str)
        if event_src_path is None:
            return

        songs_folder = self.get_songs_folder(event_src_path)

        if self.pending_refresh_task:
            self.pending_refresh_task.cancel()
            self.pending_refresh_task = None

        self.pending_refresh_task = asyncio.create_task(
            self.osu_domain_usecases.refresh_osu_file_locations_in_database(
                songs_folder
            )
        )

    async def on_created(self, event) -> None:
        await self.on_osu_event(event, event.src_path)

    async def on_modified(self, event) -> None:
        await self.on_osu_event(event, event.src_path)

    async def on_deleted(self, event) -> None:
        await self.on_osu_event(event, event.src_path)

    async def on_moved(self, event) -> None:
        await self.on_osu_event(event, event.dest_path)
