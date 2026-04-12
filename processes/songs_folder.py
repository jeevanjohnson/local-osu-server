# cache_process.py
import hashlib
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TypedDict

import orjson
import psutil
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

try:
    # from adapters import log
    from constants.paths import CACHE_SONGS_FOLDER  # type: ignore
except ImportError:
    # Ensure we are running from the project root
    sys.path.insert(0, str(Path(__file__).parent.parent))
    # from adapters import log
    from constants.paths import CACHE_SONGS_FOLDER

""" ----- Process Start ----- """

SONGS_FOLDER: Path | None = None

MD5_TO_PATH: dict[str, str] = {}
BEATMAP_ID_TO_PATH: dict[str, list[str]] = {}
FILENAME_TO_PATH: dict[str, str] = {}

PATH_TO_MD5: dict[str, str] = {}
PATH_TO_BEATMAP_ID: dict[str, str] = {}
PATH_TO_FILENAME: dict[str, str] = {}


def find_songs_folder() -> None:
    global SONGS_FOLDER

    try:
        processes = [
            process for process in psutil.process_iter() if process.name() == "osu!.exe"
        ]
    except psutil.NoSuchProcess:
        return

    if not processes:
        return

    osu = processes[0]

    osu_path = Path(osu.exe())

    cfg_path: Path | None = None
    for cfg_file in osu_path.parent.glob("osu!.*.cfg"):
        if cfg_file.is_file():
            cfg_path = cfg_file
            break

    if cfg_path is None:
        print("osu! cfg don't exists")
        return

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
        SONGS_FOLDER = Path(songs_folder)
    else:
        SONGS_FOLDER = osu_path.parent / songs_folder

    print(f"Found songs folder at {SONGS_FOLDER}")


class ParseOsuFileResponse(TypedDict):
    md5: str
    beatmap_id: str | None
    file_name: str
    source: Path


def parse_osu_file(file: Path) -> ParseOsuFileResponse:
    file_content = file.read_bytes()
    md5 = hashlib.md5(file_content).hexdigest()

    beatmap_id: str | None = None
    for line in file_content.decode("utf-8-sig").splitlines()[:50]:
        line = line.strip()

        if line.startswith("BeatmapID"):
            beatmap_id = line.split(":")[1].strip()
            break

    return {
        "md5": md5,
        "beatmap_id": beatmap_id,
        "file_name": file.name,
        "source": file,
    }


def load_cache() -> None:
    CACHE_SONGS_FOLDER.parent.mkdir(parents=True, exist_ok=True)

    if CACHE_SONGS_FOLDER.exists():
        print("Loading songs folder cache...")
        content = orjson.loads(CACHE_SONGS_FOLDER.read_bytes())
        global \
            MD5_TO_PATH, \
            BEATMAP_ID_TO_PATH, \
            PATH_TO_MD5, \
            PATH_TO_BEATMAP_ID, \
            PATH_TO_FILENAME, \
            FILENAME_TO_PATH

        MD5_TO_PATH = content.get("md5_to_path", {})
        BEATMAP_ID_TO_PATH = content.get("beatmap_id_to_path", {})
        FILENAME_TO_PATH = content.get("filename_to_path", {})

        PATH_TO_MD5 = content.get("path_to_md5", {})
        PATH_TO_BEATMAP_ID = content.get("path_to_beatmap_id", {})
        PATH_TO_FILENAME = content.get("path_to_filename", {})

        print("Songs folder cache loaded successfully.")
        return

    # Only build cache if SONGS_FOLDER is available
    if SONGS_FOLDER is None:
        print(
            "No cache file found and songs folder not available, starting with empty cache"
        )
        return

    # build cache
    osu_files = (osu_file for osu_file in SONGS_FOLDER.glob("**/*.osu"))

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(parse_osu_file, f): f for f in osu_files}
        for future in as_completed(futures):
            response = future.result()
            print(f"Processing {response['source']}...")

            md5 = response["md5"]
            beatmap_id = response["beatmap_id"]
            file_name = response["file_name"]
            source = response["source"]
            source_str = str(source.absolute())

            MD5_TO_PATH[md5] = source_str
            PATH_TO_MD5[source_str] = md5
            FILENAME_TO_PATH[file_name] = source_str
            PATH_TO_FILENAME[source_str] = file_name

            if beatmap_id is not None:
                if beatmap_id not in BEATMAP_ID_TO_PATH:
                    BEATMAP_ID_TO_PATH[beatmap_id] = []
                BEATMAP_ID_TO_PATH[beatmap_id].append(source_str)
                PATH_TO_BEATMAP_ID[source_str] = beatmap_id

            print(
                f"Processed {response['source']}, MD5: {md5}, BeatmapID: {beatmap_id}, Filename: {file_name}"
            )

    save_cache()

    print("Songs folder cache built and saved successfully.")

    return None


def save_cache() -> None:
    CACHE_SONGS_FOLDER.write_bytes(
        orjson.dumps(
            {
                "md5_to_path": MD5_TO_PATH,
                "beatmap_id_to_path": BEATMAP_ID_TO_PATH,
                "filename_to_path": FILENAME_TO_PATH,
                "path_to_md5": PATH_TO_MD5,
                "path_to_beatmap_id": PATH_TO_BEATMAP_ID,
                "path_to_filename": PATH_TO_FILENAME,
            }
        )
    )
    # print("Songs folder cache saved successfully.")


def update_cache(
    source: Path,
    md5: str | None = None,
    beatmap_id: str | None = None,
    file_name: str | None = None,
) -> None:
    source_str = str(source.absolute())

    if md5 is not None:
        MD5_TO_PATH[md5] = source_str
        PATH_TO_MD5[source_str] = md5

    if file_name is not None:
        FILENAME_TO_PATH[file_name] = source_str
        PATH_TO_FILENAME[source_str] = file_name

    if beatmap_id is not None:
        if beatmap_id not in BEATMAP_ID_TO_PATH:
            BEATMAP_ID_TO_PATH[beatmap_id] = []
        BEATMAP_ID_TO_PATH[beatmap_id].append(source_str)
        PATH_TO_BEATMAP_ID[source_str] = beatmap_id


# Watch dog
class SongFolderHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return

        event_src_path = Path(event.src_path)  # type: ignore

        response = parse_osu_file(event_src_path)
        md5 = response["md5"]
        beatmap_id = response["beatmap_id"]
        file_name = response["file_name"]
        source = response["source"]

        update_cache(source, md5, beatmap_id, file_name)

        save_cache()

        print(
            f"File created: {event.src_path}, MD5: {md5}, BeatmapID: {beatmap_id}, Filename: {file_name}"
        )

    def on_modified(self, event) -> None:
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return

        event_src_path = Path(event.src_path)  # type: ignore

        response = parse_osu_file(event_src_path)
        md5 = response["md5"]
        beatmap_id = response["beatmap_id"]
        file_name = response["file_name"]
        source = response["source"]

        update_cache(source, md5, beatmap_id, file_name)

        save_cache()

        print(
            f"File modified: {event.src_path}, MD5: {md5}, BeatmapID: {beatmap_id}, Filename: {file_name}"
        )

    def on_deleted(self, event) -> None:
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return

        event_src_path = Path(event.src_path)  # type: ignore
        event_src_path_str = str(event_src_path.absolute())

        md5 = PATH_TO_MD5.get(event_src_path_str)
        beatmap_id = PATH_TO_BEATMAP_ID.get(event_src_path_str)
        file_name = PATH_TO_FILENAME.get(event_src_path_str)

        if md5 is not None:
            del MD5_TO_PATH[md5]
            del PATH_TO_MD5[event_src_path_str]

        if file_name is not None:
            del FILENAME_TO_PATH[file_name]
            del PATH_TO_FILENAME[event_src_path_str]

        if beatmap_id is not None:
            paths = BEATMAP_ID_TO_PATH.get(beatmap_id, [])
            if event_src_path_str in paths:
                paths.remove(event_src_path_str)
            if not paths:  # clean up empty list
                del BEATMAP_ID_TO_PATH[beatmap_id]

            del PATH_TO_BEATMAP_ID[event_src_path_str]

        save_cache()

        print(
            f"File deleted: {event.src_path}, MD5: {md5}, BeatmapID: {beatmap_id}, Filename: {file_name}"
        )

    def on_moved(self, event) -> None:
        if event.is_directory:
            return

        if not event.src_path.endswith(".osu"):  # type: ignore
            return

        if not event.dest_path.endswith(".osu"):  # type: ignore
            return

        # remove old cache
        old_path = Path(event.src_path)  # type: ignore
        old_path_str = str(old_path.absolute())

        md5 = PATH_TO_MD5.get(old_path_str)
        beatmap_id = PATH_TO_BEATMAP_ID.get(old_path_str)
        file_name = PATH_TO_FILENAME.get(old_path_str)
        if md5 is not None:
            del MD5_TO_PATH[md5]
            del PATH_TO_MD5[old_path_str]

        if file_name is not None:
            del FILENAME_TO_PATH[file_name]
            del PATH_TO_FILENAME[old_path_str]

        if beatmap_id is not None:
            paths = BEATMAP_ID_TO_PATH.get(beatmap_id, [])
            if old_path_str in paths:
                paths.remove(old_path_str)
            if not paths:  # clean up empty list
                del BEATMAP_ID_TO_PATH[beatmap_id]

            del PATH_TO_BEATMAP_ID[old_path_str]

        # add new cache
        new_path = Path(event.dest_path)  # type: ignore
        response = parse_osu_file(new_path)
        md5 = response["md5"]
        beatmap_id = response["beatmap_id"]
        file_name = response["file_name"]
        source = response["source"]

        update_cache(source, md5, beatmap_id, file_name)

        save_cache()

        print(
            f"File moved: from {event.src_path} to {event.dest_path}, MD5: {md5}, BeatmapID: {beatmap_id}, Filename: {file_name}"
        )


def validate_cache_on_startup() -> None:
    """Check for new maps added while server offline and update cache."""
    if SONGS_FOLDER is None:
        return

    current_files = set(str(f.absolute()) for f in SONGS_FOLDER.glob("**/*.osu"))
    cached_files = set(PATH_TO_MD5.keys())
    new_files = current_files - cached_files

    if not new_files:
        return

    print(f"Found {len(new_files)} new maps, updating cache...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(parse_osu_file, Path(f)): f for f in new_files}
        for future in as_completed(futures):
            response = future.result()
            update_cache(
                response["source"],
                response["md5"],
                response["beatmap_id"],
                response["file_name"],
            )

    save_cache()
    print(f"Cache validation complete, {len(new_files)} new maps added")


def songs_folder_process() -> None:
    print("Running songs folder process!")
    global SONGS_FOLDER

    while SONGS_FOLDER is None:
        find_songs_folder()
        if SONGS_FOLDER is None:
            # log.warning("Waiting for osu! client to be launched")
            time.sleep(1)
        else:
            break

    # Load cache BEFORE starting the observer (blocking, not daemon)
    load_cache()

    # Detect and update cache for maps added while offline
    validate_cache_on_startup()

    event_handler = SongFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, str(SONGS_FOLDER), recursive=True)

    try:
        observer.start()
        observer.join()
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()


""" ----- Process End ----- """
