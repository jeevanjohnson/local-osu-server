import hashlib
from datetime import datetime

from usecases.adapters.ossapiasync import OssapiAsync
from models.database.beatmaps import CurrentBeatmap as Beatmap
from osu_protocol.osu.types import osuMapStatus
from osu_protocol.cho.server import osuGameMode
from repositories.beatmaps import BeatmapsRepository
from repositories.osufiles.songs_folder import OsuFileRepository
import usecases.domain.cache_control

@usecases.domain.cache_control.cache_beatmaps
async def from_db(
    beatmap_md5: str | None = None, beatmap_id: int | None = None
) -> Beatmap | None:
    beatmaps_repo = BeatmapsRepository()

    if beatmap_md5 is not None:
        bmap = await beatmaps_repo.from_md5(beatmap_md5)
        if bmap:
            return bmap

    if beatmap_id is not None:
        bmap = await beatmaps_repo.from_id(beatmap_id)
        if bmap:
            return bmap

    return None

@usecases.domain.cache_control.cache_beatmaps
async def from_api_md5(
    api_client: OssapiAsync,
    beatmap_md5: str,
    profile_name: str,
    filename: str | None = None,
) -> Beatmap | None:
    beatmaps_repo = BeatmapsRepository()
    osu_files_repo = OsuFileRepository()

    print(
        f"[DEBUG] from_api_md5 called for beatmap_md5: {beatmap_md5}, filename: {filename}"
    )

    try:
        api_beatmap = await api_client.beatmap(checksum=beatmap_md5)
    except ValueError:
        print(
            f"[DEBUG] ValueError fetching beatmap from API for checksum: {beatmap_md5}"
        )
        return None

    if api_beatmap is None:
        print(f"[DEBUG] API returned None for beatmap checksum: {beatmap_md5}", )
        return None

    # get .osu file from songs folder
    if filename is None and api_beatmap.checksum is not None:
        osu_file = await osu_files_repo.from_md5(api_beatmap.checksum)
    elif filename is not None:
        osu_file = await osu_files_repo.from_filename(filename)
    else:
        osu_file = None

    if osu_file is None:
        osu_file = await osu_files_repo.from_md5(beatmap_md5)

    if osu_file is None:
        return None

    beatmap_set = api_beatmap.beatmapset()

    now = datetime.now()
    bmap = Beatmap(
        time_inserted=now,
        id=api_beatmap.id,
        set_id=api_beatmap.beatmapset_id,
        md5=api_beatmap.checksum or beatmap_md5,
        artist=beatmap_set.artist,
        title=beatmap_set.title,
        difficulty_name=api_beatmap.version,
        max_combo=api_beatmap.max_combo or 0,
        status={profile_name: osuMapStatus.from_api_v2(api_beatmap.ranked)},
        mode=osuGameMode.from_api_v2(api_beatmap.mode),
        difficulty_adjusted=False,
        play_count=api_beatmap.playcount,
        play_count_timestamp=now,
        pass_count=api_beatmap.passcount,
        pass_count_timestamp=now,
        last_updated=api_beatmap.last_updated,
        average_rating=beatmap_set.rating,
    )

    # Always save beatmap to database so it can be found later by rank/love/graveyard commands
    await beatmaps_repo.insert_beatmap(bmap)

    return bmap

@usecases.domain.cache_control.cache_beatmaps
async def from_api_id(
    api_client: OssapiAsync,
    profile_name: str,
    beatmap_id: int,
    filename: str | None = None,
) -> Beatmap | None:
    beatmaps_repo = BeatmapsRepository()
    osu_files_repo = OsuFileRepository()

    api_beatmap = await api_client.beatmap(beatmap_id=beatmap_id)

    if api_beatmap is None:
        return None

    assert api_beatmap.checksum is not None, (
        "Checksum not found for Beatmap with id {}".format(api_beatmap.id)
    )

    if filename is None:
        osu_file = await osu_files_repo.from_md5(api_beatmap.checksum)
    else:
        osu_file = await osu_files_repo.from_filename(filename)

    if osu_file is None:
        return None

    beatmap_set = api_beatmap.beatmapset()

    now = datetime.now()
    bmap = Beatmap(
        time_inserted=now,
        id=api_beatmap.id,
        set_id=api_beatmap.beatmapset_id,
        md5=api_beatmap.checksum,
        artist=beatmap_set.artist,
        title=beatmap_set.title,
        difficulty_name=api_beatmap.version,
        max_combo=api_beatmap.max_combo or 0,
        play_count=api_beatmap.playcount,
        play_count_timestamp=now,
        pass_count=api_beatmap.passcount,
        pass_count_timestamp=now,
        last_updated=api_beatmap.last_updated,
        status={profile_name: osuMapStatus.from_api_v2(api_beatmap.ranked)},
        mode=osuGameMode.from_api_v2(api_beatmap.mode),
        difficulty_adjusted=False,
        average_rating=beatmap_set.rating,
    )

    # Always save beatmap to database so it can be found later by rank/love/graveyard commands
    await beatmaps_repo.insert_beatmap(bmap)

    return bmap

@usecases.domain.cache_control.cache_beatmaps
async def find_unsubmitted_map(
    profile_name: str, beatmap_md5: str, beatmap_set_id: int, map_filename: str
) -> Beatmap | None:
    beatmaps_repo = BeatmapsRepository()
    osu_files_repo = OsuFileRepository()

    osu_file = await osu_files_repo.from_md5(beatmap_md5)

    if osu_file is None:
        return

    if osu_file.unsubmitted:
        now = datetime.now()
        unsubmitted_beatmap = Beatmap(
            time_inserted=now,
            id=osu_file.beatmap_id,
            set_id=beatmap_set_id,
            md5=beatmap_md5,
            artist=osu_file.artist,
            title=osu_file.title,
            difficulty_name=osu_file.version,
            max_combo=osu_file.max_combo,
            status={profile_name: osuMapStatus.NOT_SUBMITTED},
            mode=osuGameMode.STANDARD,
            difficulty_adjusted=False,
            play_count=0,
            play_count_timestamp=now,
            pass_count=0,
            pass_count_timestamp=now,
            last_updated=now,
            average_rating=0.0,
        )

        await beatmaps_repo.insert_beatmap(unsubmitted_beatmap)
        return unsubmitted_beatmap

    return None

@usecases.domain.cache_control.cache_beatmaps
async def from_difficulty_adjusted_request(
    api_client: OssapiAsync,
    profile_name: str,
    beatmap_md5: str,
    beatmap_set_id: int,
    map_filename: str,
) -> Beatmap | None:
    osu_file_repo = OsuFileRepository()
    beatmap_repo = BeatmapsRepository()

    difficulty_adjusted_osu_file = await osu_file_repo.from_filename(map_filename)

    if difficulty_adjusted_osu_file is None:
        print(f"[DEBUG] Could not find osu file: {map_filename}", )
        return None

    print(
        f"[DEBUG] Found difficulty adjusted osu file: {map_filename}, beatmap_id: {difficulty_adjusted_osu_file.beatmap_id}"
    )

    original_beatmap = await from_db(beatmap_id=difficulty_adjusted_osu_file.beatmap_id)
    if original_beatmap is None:
        print(
            f"[DEBUG] Original beatmap not found in database for beatmap_id: {difficulty_adjusted_osu_file.beatmap_id}, fetching from API"
        )
        original_beatmap = await from_api_id(
            api_client,
            profile_name=profile_name,
            beatmap_id=difficulty_adjusted_osu_file.beatmap_id,
        )
    else:
        print(
            f"[DEBUG] Found original beatmap in database! Status: {original_beatmap.status}, profile_name: {profile_name}"
        )

    if original_beatmap is None:
        print(f"[DEBUG] Could not find or fetch original beatmap", )
        return None

    difficulty_adjusted_beatmap = Beatmap(
        time_inserted=datetime.now(),
        id=original_beatmap.id,
        set_id=original_beatmap.set_id,
        md5=beatmap_md5,
        artist=original_beatmap.artist,
        title=original_beatmap.title,
        difficulty_name=original_beatmap.difficulty_name,
        max_combo=original_beatmap.max_combo,
        status=original_beatmap.status.copy(),  # Copy entire status dict (includes custom statuses)
        mode=original_beatmap.mode,
        difficulty_adjusted=True,
        play_count=original_beatmap.play_count,
        play_count_timestamp=original_beatmap.play_count_timestamp,
        pass_count=original_beatmap.pass_count,
        pass_count_timestamp=original_beatmap.pass_count_timestamp,
        last_updated=original_beatmap.last_updated,
        average_rating=original_beatmap.average_rating,
    )

    print(
        f"[DEBUG] Created difficulty adjusted beatmap with status: {difficulty_adjusted_beatmap.status}"
    )

    # Always save beatmap to database so it can be found later by rank/love/graveyard commands
    await beatmap_repo.insert_beatmap(difficulty_adjusted_beatmap)

    return difficulty_adjusted_beatmap


async def ensure_counts_fresh(
    beatmap: Beatmap,
    api_client: OssapiAsync,
    stale_after_hours: int = 5,
) -> Beatmap:
    """Refresh play_count and pass_count if older than stale_after_hours."""
    now = datetime.now()
    
    # Check if play_count is stale
    play_count_age = (now - beatmap.play_count_timestamp).total_seconds()
    if play_count_age > stale_after_hours * 3600:
        try:
            api_beatmap = await api_client.beatmap(beatmap_id=beatmap.id)
            if api_beatmap:
                beatmap.play_count = api_beatmap.playcount
                beatmap.play_count_timestamp = now
        except Exception as e:
            print(f"[DEBUG] Error refreshing play_count for beatmap {beatmap.id}: {e}")
    
    # Check if pass_count is stale
    pass_count_age = (now - beatmap.pass_count_timestamp).total_seconds()
    if pass_count_age > stale_after_hours * 3600:
        try:
            api_beatmap = await api_client.beatmap(beatmap_id=beatmap.id)
            if api_beatmap:
                beatmap.pass_count = api_beatmap.passcount
                beatmap.pass_count_timestamp = now
        except Exception as e:
            print(f"[DEBUG] Error refreshing pass_count for beatmap {beatmap.id}: {e}")
    
    return beatmap


async def refresh_beatmapset_status_from_api(
    api_client: OssapiAsync, profile_name: str, beatmap: Beatmap
) -> Beatmap | None:
    """Refresh a beatmap's status from the API and update the entire beatmapset."""
    api_beatmap = await api_client.beatmap(beatmap_id=beatmap.id)

    if api_beatmap is None:
        return None

    new_status = osuMapStatus.from_api_v2(api_beatmap.status)

    if new_status == beatmap.status[profile_name]:
        return beatmap

    # Update just the primary beatmap with latest API info
    beatmap.status.update({profile_name: new_status})
    beatmap.play_count = api_beatmap.playcount
    beatmap.pass_count = api_beatmap.passcount
    beatmap.last_updated = api_beatmap.last_updated

    beatmap_repo = BeatmapsRepository()
    await beatmap_repo.insert_beatmap(beatmap)

    # Now update entire beatmapset to have this status
    await change_beatmapset_status(
        beatmap_md5=beatmap.md5,
        profile_name=profile_name,
        new_status=new_status,
        api_client=api_client,
    )

    return beatmap


async def change_beatmap_status(
    beatmap_md5: str,
    profile_name: str,
    new_status: osuMapStatus,
) -> Beatmap | None:
    beatmap_repo = BeatmapsRepository()

    beatmap = await from_db(beatmap_md5=beatmap_md5)
    if beatmap is None:
        return None

    beatmap.status.update({profile_name: new_status})

    await beatmap_repo.insert_beatmap(beatmap)

    return beatmap


async def change_beatmapset_status(
    beatmap_md5: str,
    profile_name: str,
    new_status: osuMapStatus,
    api_client: OssapiAsync,
) -> list[Beatmap]:
    """Change status for all beatmaps in a beatmapset by scanning the folder.

    For each .osu file:
    1. Calculate MD5
    2. Check if already in database
    3. If not in database, read the .osu file to get beatmap_id
    4. Check if beatmap_id exists in database to detect if difficulty-adjusted
    5. If difficulty-adjusted: use from_difficulty_adjusted_request()
    6. If not: fetch from API using from_api_md5()
    7. Update status in database
    """
    beatmap_repo = BeatmapsRepository()
    osu_files_repo = OsuFileRepository()

    # Get the primary beatmap
    primary_beatmap = await from_db(beatmap_md5=beatmap_md5)
    if primary_beatmap is None:
        return []

    # Get the beatmapset folder path
    beatmapset_file_path = await osu_files_repo.path_from_md5(beatmap_md5)
    if beatmapset_file_path is None:
        # Fallback: just update the primary beatmap
        primary_beatmap.status.update({profile_name: new_status})
        await beatmap_repo.insert_beatmap(primary_beatmap)
        return [primary_beatmap]

    beatmapset_folder = beatmapset_file_path.parent

    # Scan the folder for all .osu files and update their statuses
    updated_beatmaps = []

    for osu_file_in_folder in beatmapset_folder.glob("*.osu"):
        # Get the MD5 of this osu file
        file_content = osu_file_in_folder.read_bytes()
        md5 = hashlib.md5(file_content).hexdigest()

        print(f"[DEBUG] Processing osu file: {osu_file_in_folder.name}, MD5: {md5}", )

        # First check if already in database
        beatmap = await from_db(beatmap_md5=md5)

        # If not found in database, check the file itself to see if it's difficulty-adjusted
        if beatmap is None:
            print(f"[DEBUG] Beatmap not in database for MD5: {md5}", )
            # Try to create it as a difficulty-adjusted map first
            beatmap = await from_difficulty_adjusted_request(
                api_client=api_client,
                profile_name=profile_name,
                beatmap_md5=md5,
                beatmap_set_id=0,  # Doesn't matter for difficulty-adjusted lookup
                map_filename=osu_file_in_folder.name,
            )

            # If it's not a difficulty-adjusted map, try fetching from API
            if beatmap is None:
                print(f"[DEBUG] Not difficulty-adjusted, trying from API", )
                beatmap = await from_api_md5(
                    api_client=api_client,
                    beatmap_md5=md5,
                    profile_name=profile_name,
                    filename=osu_file_in_folder.name,
                )
        else:
            print(
                f"[DEBUG] Found beatmap in database MD5: {md5}, status: {beatmap.status}"
            )

        # If still not found, skip this file
        if beatmap is None:
            print(f"[DEBUG] Skipping, beatmap still None", )
            continue

        # Update the status
        print(f"[DEBUG] Updating status for beatmap {beatmap.id} to {new_status}", )
        beatmap.status.update({profile_name: new_status})
        await beatmap_repo.insert_beatmap(beatmap)
        updated_beatmaps.append(beatmap)

    return updated_beatmaps
