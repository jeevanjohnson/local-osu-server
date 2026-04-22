from pathlib import Path

from watchdog.events import FileSystemEventHandler

from core.models.database.osu_file_location import OsuFileLocation
from core.repositories.osu_file_location import OsuFileLocationRepository
from datetime import datetime, timedelta
from typing import TypedDict
from osu_watcher.parser import parse_osu_file
from osu_watcher.repo import insert_beatmap_in_cache, delete_beatmap_from_cache_via_path
from threading import RLock

class OsuFileInsert(TypedDict):
    inserted_at: datetime
    osu_file_location: OsuFileLocation

class SongFolderHandler(FileSystemEventHandler):
    def __init__(self) -> None:
        super().__init__()
        self.osu_file_location_repo = OsuFileLocationRepository()
        self.osu_file_queue: list[OsuFileInsert] = []
        self.lock = RLock()  # To ensure thread safety when accessing the queue
    
    def _update_database(self) -> None:
        now = datetime.now()
        
        # Process if queue is full (5+) OR if oldest item has been waiting 5+ minutes
        should_process = (
            len(self.osu_file_queue) >= 5 or 
            (self.osu_file_queue and now - self.osu_file_queue[0]["inserted_at"] > timedelta(minutes=5))
        )
        
        if should_process:
            with self.lock:
                for osu_file_insert in self.osu_file_queue[:]:  # iterate over copy
                    self.osu_file_location_repo.update(osu_file_insert["osu_file_location"])
            
            self.osu_file_queue.clear()
    
    def update_database(self, location: OsuFileLocation) -> None:
        self.osu_file_queue.append({
            "inserted_at": datetime.now(),
            "osu_file_location": location
        })
        self._update_database()

    def delete_from_path(self, path: Path, update_database: bool = True) -> None:
        database = self.osu_file_location_repo.get()

        database = delete_beatmap_from_cache_via_path(database, path)

        if update_database:
            self.update_database(database)

    def update_from_path(self, path: Path) -> None:
        if not path.is_file():
            return

        if not path.suffix == ".osu":
            return

        database = self.osu_file_location_repo.get()

        database = insert_beatmap_in_cache(
            database, parse_osu_file(path)
        )
        
        self.update_database(database)

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
