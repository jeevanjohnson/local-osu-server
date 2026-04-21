from pathlib import Path

from watchdog.events import FileSystemEventHandler

from core.repositories.osu_file_location import OsuFileLocationRepository
from osu_watcher.parser import parse_osu_file
from osu_watcher.repo import insert_beatmap_in_cache, delete_beatmap_from_cache_via_path


class SongFolderHandler(FileSystemEventHandler):
    def __init__(self) -> None:
        super().__init__()
        self.osu_file_location_repo = OsuFileLocationRepository()
    
    def delete_from_path(self, path: Path, update_database: bool = True) -> None:
        database = self.osu_file_location_repo.get()

        database = delete_beatmap_from_cache_via_path(database, path)

        if update_database:
            self.osu_file_location_repo.update(database)

    def update_from_path(self, path: Path) -> None:
        if not path.is_file():
            return

        if not path.suffix == ".osu":
            return

        database = self.osu_file_location_repo.get()

        database = insert_beatmap_in_cache(
            database, parse_osu_file(path)
        )
        
        self.osu_file_location_repo.update(database)

    def on_created(self, event) -> None:
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return

        event_src_path = Path(event.src_path)  # type: ignore

        print(f"File created: {event_src_path}")

        self.update_from_path(event_src_path)

    def on_modified(self, event) -> None:
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return

        event_src_path = Path(event.src_path)  # type: ignore

        print(f"File modified: {event_src_path}")

        self.update_from_path(event_src_path)

    def on_deleted(self, event) -> None:
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return

        event_src_path = Path(event.src_path)  # type: ignore
        
        print(f"File deleted: {event_src_path}")

        self.delete_from_path(event_src_path)
    
    def on_moved(self, event) -> None:
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return

        if not event.dest_path.endswith(".osu"):  # type: ignore
            return

        # remove old cache
        old_path = Path(event.src_path)  # type: ignore
       
        self.delete_from_path(old_path)

        # add new cache
        new_path = Path(event.dest_path)  # type: ignore
        
        self.update_from_path(new_path)

        print(f"File moved: {old_path} -> {new_path}")
