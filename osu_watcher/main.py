
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import psutil
from core.repositories.osu_file_location import OsuFileLocationRepository
from watchdog.observers import Observer

from core.constants import OSU_FILE_LOCATION
from core.models.database.osu_file_location import OsuFileLocation
from osu_watcher.parser import parse_osu_file
from osu_watcher.watchdog import SongFolderHandler


def retrive_songs_folder_from_osu_client() -> Path | None:
    try:
        processes = [
            process for process in psutil.process_iter() if process.name() == "osu!.exe"
        ]
    except psutil.NoSuchProcess:
        return

    if not processes:
        return None

    osu = processes[0]

    osu_path = Path(osu.exe())

    cfg_path: Path | None = None
    for cfg_file in osu_path.parent.glob("osu!.*.cfg"):
        if cfg_file.is_file():
            cfg_path = cfg_file
            break

    if cfg_path is None:
        print("osu! cfg don't exists")
        return None

    raw_cfg = cfg_path.read_text(errors="ignore")
    songs_folder: str | None = None
    for line in raw_cfg.splitlines():
        line = line.strip()

        if line.startswith("BeatmapDirectory"):
            songs_folder = line.split("=")[1].strip()
            break

    if songs_folder is None:
        return None

    if os.path.isabs(songs_folder):
        return Path(songs_folder)
    else:
        return osu_path.parent / songs_folder

def initialize_osu_file_cache(songs_folder: Path) -> None:
    osu_file_location_repo = OsuFileLocationRepository()

    osu_files = (osu_file for osu_file in songs_folder.glob("**/*.osu"))

    database = osu_file_location_repo.get()

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(parse_osu_file, f): f for f in osu_files}
        for future in as_completed(futures):
            response = future.result()
            md5 = response["md5"]
            filename = response["filename"]
            set_id = response["beatmap_set_id"]
            id = response["beatmap_id"]
            path = response["path"]

            if id is not None:
                database.by_id[id] = path
            
            database.by_md5[md5] = path
            database.by_filename[filename] = path
            if set_id is not None:
                if set_id not in database.by_set_id:
                    database.by_set_id[set_id] = []
                database.by_set_id[set_id].append(path)

            database.path_to_md5[path] = md5
            if id is not None:
                database.path_to_id[path] = id
            if set_id is not None:
                database.path_to_set_id[path] = set_id
            database.path_to_filename[path] = filename

            print(f"Added osu! file to cache: {path}")

    osu_file_location_repo.update(database)

def validate_osu_file_cache(songs_folder: Path) -> None:
    # check if songs folder was updated since last cache update, if not, skip validation

    osu_file_location_repo = OsuFileLocationRepository()
    database = osu_file_location_repo.get()

    cached_files = set(database.path_to_filename.keys())
    current_files = set(f for f in songs_folder.glob("**/*.osu"))
    new_files = current_files - cached_files

    if not new_files:
        return
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(parse_osu_file, f): f for f in new_files}
        for future in as_completed(futures):
            response = future.result()
            md5 = response["md5"]
            filename = response["filename"]
            set_id = response["beatmap_set_id"]
            id = response["beatmap_id"]
            path = response["path"]

            if id is not None:
                database.by_id[id] = path
            database.by_md5[md5] = path
            database.by_filename[filename] = path
            if set_id is not None:
                if set_id not in database.by_set_id:
                    database.by_set_id[set_id] = []
                database.by_set_id[set_id].append(path)
    
            database.path_to_md5[path] = md5
            if id is not None:
                database.path_to_id[path] = id
            if set_id is not None:
                database.path_to_set_id[path] = set_id
            database.path_to_filename[path] = filename

            print(f"Added new osu! file to cache: {path}")

    osu_file_location_repo.update(database)

def stop(dev_mode: bool):
    observer = Observer()
    observer.stop()
    print("Osu! Watcher stopped")

def start(dev_mode: bool):
    SONGS_FOLDER: Path | None = None

    while SONGS_FOLDER is None:
        SONGS_FOLDER = retrive_songs_folder_from_osu_client()
        if SONGS_FOLDER:
            break

        print("Waiting for osu! client to start...")
        time.sleep(1)
    
    if not OSU_FILE_LOCATION.exists():
        print("Initializing osu! file cache...")
        initialize_osu_file_cache(SONGS_FOLDER)
    else:
        print("Validating osu! file cache...")
        validate_osu_file_cache(SONGS_FOLDER)
    
    event_handler = SongFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, str(SONGS_FOLDER), recursive=True)

    print("Successfully started osu! watcher")

    try:
        observer.start()
        observer.join()
    finally:
        observer.stop()
        observer.join()
        print("Osu! Watcher stopped")