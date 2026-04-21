from pathlib import Path

from watchdog.events import FileSystemEventHandler

from jays_tools.json_database import JsonDatabase as _JsonDatabase

from core.models.database.osu_file_location import OsuFileLocation
from core.repositories.osu_file_location import OsuFileLocationRepository
from osu_watcher.parser import parse_osu_file


class SongFolderHandler(FileSystemEventHandler):
    def __init__(self) -> None:
        super().__init__()
        self.osu_file_location_repo = OsuFileLocationRepository()
    
    def delete_from_path(self, path: Path) -> None:
        database = self.osu_file_location_repo.get()

        md5 = database.path_to_md5.get(path)
        if md5 is not None:
            del database.path_to_md5[path]

        beatmap_id = database.path_to_id.get(path)
        if beatmap_id is not None:
            del database.path_to_id[path]

        set_id = database.path_to_set_id.get(path)
        if set_id is not None:
            del database.path_to_set_id[path]

        filename = database.path_to_filename.get(path)
        if filename is not None:
            del database.path_to_filename[path]

    def update_from_path(self, path: Path) -> None:
        if not path.is_file():
            return

        if not path.suffix == ".osu":
            return

        response = parse_osu_file(path)
        md5 = response["md5"]
        beatmap_id = response["beatmap_id"]
        file_name = response["filename"]
        path_str = response["path"]

        database = self.osu_file_location_repo.get()

        database.by_md5[md5] = path_str
        if beatmap_id is not None:
            database.by_id[beatmap_id] = path_str
        database.by_filename[file_name] = path_str
        if beatmap_id is not None:
            if beatmap_id not in database.by_set_id:
                database.by_set_id[beatmap_id] = []
            database.by_set_id[beatmap_id].append(path_str)
        
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
