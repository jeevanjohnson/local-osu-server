from pathlib import Path

from hachiko.hachiko import AIOEventHandler

from core.repositories.osu_file_locations import OsuFileLocationsRepository
from osu_watcher.services import OsuFileLocationService, OsuFileService

class SongFolderHandler(AIOEventHandler):
    def __init__(self) -> None:
        super().__init__()
        self.osu_file_location_repo = OsuFileLocationsRepository()
        self.osu_file_location_service = OsuFileLocationService()
        self.osu_file_service = OsuFileService()

    def get_songs_folder(self, osu_file: Path) -> Path:
        return osu_file.parent.parent

    async def delete_from_path(self, path: Path) -> None:
        songs_folder = self.get_songs_folder(path)

        osu_file_locations = await self.osu_file_location_repo.get(songs_folder)

        if osu_file_locations is None:
            return

        if path not in osu_file_locations.path_to_filename:
            return
        
        osu_file_locations = self.osu_file_location_service.remove(
            path, osu_file_locations
        )

        await self.osu_file_location_repo.update(osu_file_locations)

    async def add_from_path(self, path: Path) -> None:
        songs_folder = self.get_songs_folder(path)

        osu_file_locations = await self.osu_file_location_repo.get(songs_folder)

        if osu_file_locations is None:
            return

        if path in osu_file_locations.path_to_filename:
            return
    
        parsed_osu_file = self.osu_file_service.parse_watcher_data(path)

        osu_file_locations = self.osu_file_location_service.add(
            parsed_osu_file, osu_file_locations
        )
        
        await self.osu_file_location_repo.update(osu_file_locations)

    async def on_created(self, event) -> None:
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return

        event_src_path = Path(event.src_path)  # type: ignore

        if not event_src_path.is_file():
            return

        if not event_src_path.suffix == ".osu":
            return

        print(f"File created: {event_src_path}")

        await self.add_from_path(event_src_path)

    async def on_modified(self, event) -> None:
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return

        event_src_path = Path(event.src_path)  # type: ignore

        if not event_src_path.is_file():
            return

        if not event_src_path.suffix == ".osu":
            return

        print(f"File modified: {event_src_path}")

        # delete old data and add new data
        await self.delete_from_path(event_src_path)
        await self.add_from_path(event_src_path)

    async def on_deleted(self, event) -> None:
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return

        event_src_path = Path(event.src_path)  # type: ignore

        if not event_src_path.is_file():
            return

        if not event_src_path.suffix == ".osu":
            return
        
        print(f"File deleted: {event_src_path}")

        await self.delete_from_path(event_src_path)
    
    async def on_moved(self, event) -> None:
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return


        if not event.dest_path.endswith(".osu"):  # type: ignore
            return

        # remove old cache
        old_path = Path(event.src_path)  # type: ignore

        if not old_path.is_file():
            return

        if not old_path.suffix == ".osu":
            return

        await self.delete_from_path(old_path)

        # add new cache
        new_path = Path(event.dest_path)  # type: ignore

        if not new_path.is_file():
            return

        if not new_path.suffix == ".osu":
            return

        await self.add_from_path(new_path)

        print(f"File moved: {old_path} -> {new_path}")
