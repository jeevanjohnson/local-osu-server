from core.models.database.osu_file_location import OsuFileLocation
from osu_watcher.parser import ParseOsuFileResponse
from pathlib import Path

def insert_beatmap_in_cache(
    database: OsuFileLocation, 
    response: ParseOsuFileResponse
) -> OsuFileLocation:

    md5 = response["md5"]
    filename = response["filename"]
    set_id = response["beatmap_set_id"]
    id = response["beatmap_id"]
    path = response["path"]

    if id is not None:
        if id not in database.by_id:
            database.by_id[id] = []

        if path not in database.by_id[id]:
            database.by_id[id].append(path)
    
    database.by_md5[md5] = path
    database.by_filename[filename] = path
    if set_id is not None:
        if set_id not in database.by_set_id:
            database.by_set_id[set_id] = []
        
        if path not in database.by_set_id[set_id]:
            database.by_set_id[set_id].append(path)

    database.path_to_md5[path] = md5
    if id is not None:
        database.path_to_id[path] = id
    if set_id is not None:
        database.path_to_set_id[path] = set_id
    database.path_to_filename[path] = filename

    print(f"Added osu! file to cache: {path}")

    return database

def delete_beatmap_from_cache_via_path(
    database: OsuFileLocation,
    path: Path,
) -> OsuFileLocation:
    md5 = database.path_to_md5.get(path)
    if md5 is not None:
        del database.path_to_md5[path]
    
    if md5 in database.by_md5:
        del database.by_md5[md5]

    beatmap_id = database.path_to_id.get(path)
    if beatmap_id is not None:
        del database.path_to_id[path]
    
    if beatmap_id in database.by_id:
        database.by_id[beatmap_id] = [
            p for p in database.by_id[beatmap_id] if p != path
        ]
        if not database.by_id[beatmap_id]:  # if the list is empty after removal
            del database.by_id[beatmap_id]

    set_id = database.path_to_set_id.get(path)
    if set_id is not None:
        del database.path_to_set_id[path]

    if set_id in database.by_set_id:
        database.by_set_id[set_id] = [
            p for p in database.by_set_id[set_id] if p != path
        ]
        if not database.by_set_id[set_id]:  # if the list is empty after removal
            del database.by_set_id[set_id]

    filename = database.path_to_filename.get(path)
    if filename is not None:
        del database.path_to_filename[path]
    
    if filename in database.by_filename:
        del database.by_filename[filename]

    return database